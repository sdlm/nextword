# Design: Remove Successfully Uploaded Words from export.csv

**Date:** 2026-06-12
**Revised:** 2026-06-13 — cleanup moved into `_do_upload()`; the uploaded-word
set is now derived from `cards.json` (`mochi_upload.DEFAULT_CARDS`) instead of
the in-memory `cards` returned by `generate()`, and cleanup now runs for the
standalone `nextword mochi upload` command as well as the pipeline.

## Overview

After a successful Mochi upload, words that were uploaded should be removed from `data/export.csv` so they are not re-processed in future pipeline runs.

## Behaviour

- Removal happens in `_do_upload()` in `cli.py`, after `mochi_upload.upload()` returns. `_do_upload()` is called both from `_run_pipeline()` (TUI → generate → upload) **and** from the standalone `nextword mochi upload` command — so CSV cleanup runs for both paths.
- The set of uploaded words is derived from the generated cards on disk (`cards.json` / `mochi_upload.DEFAULT_CARDS`) minus the words that failed upload. In the pipeline path `pipeline.generate()` writes `cards.json` before upload; in the standalone path it must already exist.
- Only words that were **successfully uploaded** are removed. Words that failed Mochi upload remain in the CSV.
- If `upload()` raises an exception, the CSV is **not modified** (the `try/except` guard returns before cleanup).
- If `cards.json` (`mochi_upload.DEFAULT_CARDS`) does not exist, nothing is done.
- If the set of successfully uploaded words is empty, the CSV is **not modified**.
- If `pipeline.DEFAULT_CSV` does not exist, nothing is done.
- After removal, if all words were uploaded, the CSV contains only the header row (`word`).

## Implementation

### Where

`nextword/cli.py` — inside `_do_upload()`, after the `mochi_upload.upload()` call. `_do_upload()` is invoked by both `_run_pipeline()` and the standalone `mochi upload` command.

### Logic

```python
if not mochi_upload.DEFAULT_CARDS.exists():
    return
cards = json.loads(mochi_upload.DEFAULT_CARDS.read_text(encoding="utf-8"))
# successful uploads = generated cards on disk minus those that failed upload
uploaded = {card["fields"]["Word"] for card in cards} - set(failed_words)

if uploaded and pipeline.DEFAULT_CSV.exists():
    remaining = [w for w in pipeline.read_words(pipeline.DEFAULT_CSV) if w not in uploaded]
    pipeline.write_words(pipeline.DEFAULT_CSV, remaining)
```

### Data flow

1. (pipeline path only) `pipeline.generate()` writes `cards.json` and returns `(cards, _failed_gen)`
2. `mochi_upload.upload()` → `(new_count, updated_count, failed_words)` — words that failed upload
3. Read `cards.json` (`mochi_upload.DEFAULT_CARDS`); `uploaded = {card["fields"]["Word"] for card in cards} - set(failed_words)`
4. Rewrite `pipeline.DEFAULT_CSV` keeping only words not in `uploaded`

## Files Changed

- `nextword/cli.py` — CSV rewrite logic lives in `_do_upload()` (reads `cards.json`, rewrites `pipeline.DEFAULT_CSV` via `pipeline.write_words`).

## Testing

- Tests in `tests/test_cli.py`: mock `pipeline.generate` and `mochi_upload.upload`, **stand up a tmp `cards.json` and patch `mochi_upload.DEFAULT_CARDS`** (the cleanup reads it), and assert the CSV is rewritten correctly. Without the `cards.json` patch the cleanup is a no-op and tests pass vacuously.
- Cases to cover: all succeed (CSV emptied), partial failure (failed words remain), upload exception (CSV unchanged), empty uploaded set (CSV unchanged), missing CSV (no-op).
