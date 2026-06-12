# Design: Remove Successfully Uploaded Words from export.csv

**Date:** 2026-06-12

## Overview

After a successful Mochi upload, words that were uploaded should be removed from `data/export.csv` so they are not re-processed in future pipeline runs.

## Behaviour

- Removal happens **once, at the end** of `_run_pipeline()` in `cli.py`, after `mochi_upload.upload()` returns.
- Only words that were **successfully uploaded** are removed. Words that failed card generation or Mochi upload remain in the CSV.
- If `upload()` raises an exception, the CSV is **not modified** (existing `try/except` guard handles this).
- If the set of successfully uploaded words is empty, the CSV is **not modified**.
- If `pipeline.DEFAULT_CSV` does not exist, nothing is done.
- After removal, if all words were uploaded, the CSV contains only the header row (`word`).

## Implementation

### Where

`nextword/cli.py` — inside `_run_pipeline()`, after the `mochi_upload.upload()` call.

### Logic

```python
# successful uploads = generated cards minus those that failed upload
uploaded = {card["fields"]["Word"] for card in cards} - set(failed_words)

if uploaded and pipeline.DEFAULT_CSV.exists():
    remaining = [w for w in pipeline.read_words(pipeline.DEFAULT_CSV) if w not in uploaded]
    with pipeline.DEFAULT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word"])
        for word in remaining:
            writer.writerow([word])
```

### Data flow

1. `pipeline.generate()` → `(cards, _failed_gen)` — cards that passed generation
2. `mochi_upload.upload()` → `(new_count, updated_count, failed_words)` — words that failed upload
3. `uploaded = {card["fields"]["Word"] for card in cards} - set(failed_words)`
4. Rewrite `pipeline.DEFAULT_CSV` keeping only words not in `uploaded`

## Files Changed

- `nextword/cli.py` — add CSV rewrite logic to `_run_pipeline()`; add `import csv` at top

## Testing

- Add test in `tests/test_cli.py`: mock `pipeline.generate` and `mochi_upload.upload`, assert CSV is rewritten correctly after a successful pipeline run.
- Cases to cover: all succeed (CSV emptied), partial failure (failed words remain), upload exception (CSV unchanged), empty uploaded set (CSV unchanged).
