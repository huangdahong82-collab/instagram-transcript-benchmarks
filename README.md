# Instagram transcript benchmarks

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23433884.svg)](https://doi.org/10.5281/zenodo.23433884)

Raw measurements of what a hosted Whisper endpoint actually returns for Instagram-style
audio: 151 uploads across four suites, scored word by word against reference text we
wrote ourselves. Every row in `data/` carries the URL of the write-up it came from.
Archived with a DOI at Zenodo: https://doi.org/10.5281/zenodo.23433884

The endpoint under test is the public one behind
[transcriptreel.com](https://transcriptreel.com); each suite is also written up there in
prose, with the audio conditions spelled out.

## Why this exists

Search for an Instagram transcript tool and you will find accuracy claims of 95% and 99%
with no test set, no audio and no scoring method behind them. A percentage produced
without a labelled corpus is marketing, not measurement. This repository is the opposite
of that: a small, checkable set of runs where the reference text is known word for word,
so anyone can re-derive the score.

There is no single accuracy number here, and that is deliberate. One voice reading one
sentence is not a corpus. What is here is the shape of the failures — which is the part
that decides whether a transcript is usable.

## What is in `data/`

| File | Rows | Uploads behind it | Run on | Suite |
|---|---|---|---|---|
| `degradation-28-uploads.csv` | 16 | 28 | 2026-10-02 | one 29-word clip re-encoded 16 ways: sample rate, bitrate, band limit, level, speed, noise beds |
| `music-beds-37-uploads.csv` | 23 | 37 | 2026-10-07 | the same clip under synthesised music beds at measured levels, plus repair attempts |
| `accented-voices-36-uploads.csv` | 15 | 36 | 2026-10-12 | one 32-word sentence in four voices, then a playback-speed ladder |
| `writing-layer-50-uploads.csv` | 27 | 50 | 2026-10-17 | numbers, negations, grammar, loanwords, silence, and what does not change the output |
| `latency.csv` | 7 | — | both | wall-clock times by file size and warm/cold model |

Columns: `suite, test_id, date, condition, setting, reference_words, words_matched,
response_words, verbatim_output, note, source_url`. Empty `words_matched` means the run
was recorded but not scored word by word; the raw output is in `verbatim_output` instead.

`reference_words` counts words in the reference text, `words_matched` counts reference
words that survived into the output. Both are produced by `tools/wer.py`.

## Three things the data shows

**Sample rate and bitrate barely matter; masking does.** 8 kHz, 16 kHz, 22.05 kHz, 44.1 kHz
stereo at 320 kbps, 32 kbps MP3 and a 300–3400 Hz telephone band all returned 29 of 29
words. What broke the same clip was speech at 5% with noise at 30%: the response was a
single token, `nd`, with `success: true`.

**A steady music bed is not the problem; a dense broadband mix is.** A three-note pad at
four times the voice level still returned 29 of 29. A dense mix at equal level returned 28
of 29, at +6 dB 24 of 29, and at +12 dB 15 of 29 inside a 32-word response that reads like
English and shares almost nothing with what was said.

**Failure arrives as fluent text, never as an error.** None of the degraded runs returned
an error field. A six-second file of digital silence returned 338 words — "Thank you very
much" repeated — with `success: true`, in 19.66 s.

## Scoring it yourself

`tools/wer.py` is the scorer used for every `words_matched` value here. Standard library
only, no dependencies.

```bash
python3 tools/wer.py --self-test
python3 tools/wer.py --ref reference.txt --hyp output.txt
python3 tools/wer.py --ref-text "the quick brown fox jumps over the lazy dog" \
                     --hyp-text "the cookground talk jumped over the lazy job"
```

It prints a summary line (`matched N/M S= D= I= WER=`) followed by a word-level
alignment: `=` matched, `S` substituted, `D` missing from the output, `I` present only in
the output. Normalisation is lowercase plus punctuation stripping, keeping intra-word
apostrophes so `can't` stays one token.

## Limits you should hold on to

- The voices are text-to-speech (flite, US and Scottish English), not recordings of real
  speakers. Accent and learner-speech results describe the model's behaviour on synthetic
  audio, not on a corpus of real people.
- One engine: `@cf/openai/whisper` on Cloudflare Workers AI, as reported in the response's
  `engine` field. Other Whisper hosts may behave differently.
- One sentence per suite, one voice per suite. These are controlled probes, not a benchmark
  you can quote for your own audio.
- The music beds are synthesised, not licensed tracks. We hold no rights to test commercial
  music and did not guess at what it would do.
- Dates are in the `date` column. A model update can invalidate a run; re-run before
  quoting an old number.

## License

Data in `data/` is CC BY 4.0. Code in `tools/` is MIT. See `LICENSE`.
