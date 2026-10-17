# Method

Every number in `data/` was produced the same way: build audio whose text we know word
for word, upload it, align the returned text against the reference, count reference words
that survived. This file records how, and what was not measured.

## Engine

`@cf/openai/whisper` on Cloudflare Workers AI. The engine string is read from the
response's own `engine` field (`Cloudflare Workers AI (@cf/openai/whisper)`), not inferred.

The response body has exactly six fields: `success`, `transcript`, `language`, `engine`,
`fileSize`, `fileName`. There is no per-word confidence, no timestamps, no speaker labels,
no alternative readings. In all 151 uploads the `language` field read `unknown`.

## Audio

Synthesised with `flite` (US English `slt`/`kal`/`rms`, Scottish `awb`) so the reference
text is exact rather than transcribed by hand. Levels were measured, not guessed: in the
music suite the speech averaged -18.1 dB and the dense bed -17.7 dB at its base level, so
"1x" means the music and the voice were roughly equal.

Reference texts: 29 words (degradation and music suites), 32 words (accent suite),
sentence-level sets of 4–11 words plus a 114-word narration (writing suite).

## Scoring

`tools/wer.py`, in this repository. Words are lowercased and stripped of punctuation,
with intra-word apostrophes preserved. Alignment is Levenshtein over word tokens.
`words_matched` = number of reference words aligned as matches. `WER` = (S + D + I) / N
where N is the reference word count.

Where a run was recorded but not scored word by word — for example an output that shares
nothing with the reference, or a response that was two characters long — `words_matched`
is left empty and the raw text is in `verbatim_output`. Filling in a score there would
have meant inventing an alignment.

## What we did not measure

- **No accuracy percentage, anywhere.** That needs a labelled corpus of real Instagram
  audio with verified human reference transcripts. We do not have one, and neither do the
  tools that print 95% and 99% on their homepages without publishing theirs.
- **No real human accents.** The accent suite compares four synthetic voices. It isolates
  acoustics from content (identical words in every render) but says nothing about how the
  model treats a real speaker.
- **No commercial music.** The beds are synthesised pads, drums, bass and a dense
  noise-plus-chord mix. Licensed tracks with sung vocals may behave differently; we hold
  no rights to test them.
- **No speed benchmark.** Timings in `latency.csv` are wall clock including upload, on one
  machine and one network. They show that wait time tracks upload size and whether the
  model is warm, not throughput per minute of audio.

## Reproducing

Any run can be repeated against any endpoint that accepts a file and returns text: upload
the same audio, then score the output with `tools/wer.py` against the reference in the
`setting` and `verbatim_output` columns. The `source_url` on each row points at the
write-up describing that run's audio conditions.

## Dates

Suites were run on 2026-10-02, 2026-10-07, 2026-10-12 and 2026-10-17. Hosted models change
without notice; a number from October is a claim about October.
