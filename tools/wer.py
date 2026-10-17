#!/usr/bin/env python3
"""wer.py - word error rate and word-level alignment for transcript comparisons.

Why this exists: every number in ../data/ was scored by aligning the model output
against a reference text we wrote ourselves, then counting words that survived.
This is that scorer, so the numbers can be checked instead of trusted.

Usage
-----
    python3 tools/wer.py --ref reference.txt --hyp output.txt
    python3 tools/wer.py --ref-text "the quick brown fox" --hyp-text "the quick round box"
    python3 tools/wer.py --self-test

Output is plain text: one summary line, then an alignment of the two texts where
   =  matched        S  substituted        D  deleted (missing from output)
   I  inserted (present in output only)

Normalisation defaults (turn off with --keep-case / --keep-punct):
  - lowercase everything
  - drop punctuation, keep intra-word apostrophes so "can't" stays one token
  - collapse whitespace
  - optionally fold numbers to words with --spell-numbers (off by default; it is
    a lossy transform and it changes what you are measuring)
"""

import argparse
import re
import sys

PUNCT_RE = re.compile(r"[^\w\s']|_", re.UNICODE)
MULTI_SPACE_RE = re.compile(r"\s+")

ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
        "eighty", "ninety"]


def _two_digits(n):
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + ("-" + ONES[o] if o else "")


def spell_number(n):
    """Integer to English words, up to 999,999,999. Returns None if out of range."""
    if n < 0 or n > 999_999_999:
        return None
    if n < 100:
        return _two_digits(n)
    if n < 1000:
        h, r = divmod(n, 100)
        return ONES[h] + " hundred" + (" " + _two_digits(r) if r else "")
    for size, name in ((1_000_000, "million"), (1_000, "thousand")):
        if n >= size:
            hi, lo = divmod(n, size)
            head = spell_number(hi) + " " + name
            return head + (" " + spell_number(lo) if lo else "")
    return None


def normalise(text, keep_case=False, keep_punct=False, spell_numbers=False):
    if not keep_punct:
        text = PUNCT_RE.sub(" ", text)
    text = MULTI_SPACE_RE.sub(" ", text).strip()
    tokens = text.split(" ") if text else []
    if not keep_case:
        tokens = [t.lower() for t in tokens]
    if spell_numbers:
        out = []
        for tok in tokens:
            core = tok.strip(".,!?;:")
            if core.isdigit():
                words = spell_number(int(core))
                if words:
                    out.extend(words.split(" "))
                    continue
            out.append(tok)
        tokens = out
    return tokens


def align(ref, hyp):
    """Levenshtein alignment. Returns (ops, stats) with ops as (op, ref_word, hyp_word)."""
    n, m = len(ref), len(hyp)
    # dp[i][j] = cost of aligning ref[:i] with hyp[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i
    for j in range(1, m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        ri = ref[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ri == hyp[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,        # deletion
                dp[i][j - 1] + 1,        # insertion
                dp[i - 1][j - 1] + cost,  # match or substitution
            )

    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            if dp[i][j] == dp[i - 1][j - 1] + cost:
                ops.append(("=" if cost == 0 else "S", ref[i - 1], hyp[j - 1]))
                i, j = i - 1, j - 1
                continue
        if i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("D", ref[i - 1], ""))
            i -= 1
            continue
        ops.append(("I", "", hyp[j - 1]))
        j -= 1
    ops.reverse()

    matched = sum(1 for op in ops if op[0] == "=")
    sub = sum(1 for op in ops if op[0] == "S")
    dele = sum(1 for op in ops if op[0] == "D")
    ins = sum(1 for op in ops if op[0] == "I")
    stats = {
        "ref_words": n,
        "hyp_words": m,
        "matched": matched,
        "substitutions": sub,
        "deletions": dele,
        "insertions": ins,
        "wer": (sub + dele + ins) / n if n else float("nan"),
    }
    return ops, stats


def format_report(ops, stats):
    lines = []
    lines.append(
        "matched {matched}/{ref_words}  S={substitutions} D={deletions} I={insertions}  "
        "WER={wer:.3f}".format(**stats)
    )
    lines.append("")
    width = 22
    for op, r, h in ops:
        if op == "=":
            lines.append("  =  {:<{w}}".format(r, w=width))
        elif op == "S":
            lines.append("  S  {:<{w}} -> {}".format(r, h, w=width))
        elif op == "D":
            lines.append("  D  {:<{w}} -> (missing)".format(r, w=width))
        else:
            lines.append("  I  {:<{w}} -> {}".format("(absent)", h, w=width))
    return "\n".join(lines)


def read_file(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


SELF_TEST_CASES = [
    # (reference, hypothesis, expected matched, expected ref_words, note)
    ("the quick brown fox jumps over the lazy dog",
     "the quick round box jumps over the lazy dog", 7, 9, "music bed at +6 dB: brown->round, fox->box"),
    ("the quick brown fox jumps over the lazy dog",
     "this is a test of the instagram transfer tool", 0, 9, "hallucination replaces the sentence"),
    ("i can come on friday but i can't come on saturday",
     "i can't come on friday but i can't come on saturday", 10, 11, "a negation appears where none was spoken"),
    ("she don't like coffee", "she don't like coffee", 4, 4, "grammar error left untouched"),
]


def self_test():
    ok = True
    for ref_text, hyp_text, exp_matched, exp_ref, note in SELF_TEST_CASES:
        ref = normalise(ref_text)
        hyp = normalise(hyp_text)
        _, stats = align(ref, hyp)
        good = stats["matched"] == exp_matched and stats["ref_words"] == exp_ref
        ok = ok and good
        print("{} matched={}/{} expected={}/{}  {}".format(
            "PASS" if good else "FAIL", stats["matched"], stats["ref_words"],
            exp_matched, exp_ref, note))
    print("\nall cases pass" if ok else "\nFAILURES ABOVE")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Word error rate and alignment for transcripts.")
    ap.add_argument("--ref", help="reference transcript file")
    ap.add_argument("--hyp", help="hypothesis (model output) file")
    ap.add_argument("--ref-text", help="reference text inline")
    ap.add_argument("--hyp-text", help="hypothesis text inline")
    ap.add_argument("--keep-case", action="store_true", help="do not lowercase")
    ap.add_argument("--keep-punct", action="store_true", help="keep punctuation as tokens")
    ap.add_argument("--spell-numbers", action="store_true",
                    help="write digits out as words before scoring (lossy, off by default)")
    ap.add_argument("--quiet", action="store_true", help="summary line only")
    ap.add_argument("--self-test", action="store_true", help="run the built-in checks")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.ref_text is not None:
        ref_text = args.ref_text
    elif args.ref:
        ref_text = read_file(args.ref)
    else:
        ap.error("need --ref, --ref-text or --self-test")

    if args.hyp_text is not None:
        hyp_text = args.hyp_text
    elif args.hyp:
        hyp_text = read_file(args.hyp)
    else:
        ap.error("need --hyp or --hyp-text")

    ref = normalise(ref_text, args.keep_case, args.keep_punct, args.spell_numbers)
    hyp = normalise(hyp_text, args.keep_case, args.keep_punct, args.spell_numbers)
    ops, stats = align(ref, hyp)

    if args.quiet:
        print("matched {matched}/{ref_words} S={substitutions} D={deletions} "
              "I={insertions} WER={wer:.3f}".format(**stats))
    else:
        print(format_report(ops, stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
