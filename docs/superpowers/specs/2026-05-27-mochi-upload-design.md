# Mochi Upload — Design Spec

**Date:** 2026-05-27

## Overview

Upload generated flashcards from `data/cards.json` to a Mochi deck using the Mochi REST API. Cards are created with `template-id` and `fields` to enable Mochi's 3-side SRS layout as defined in `docs/template.md`. Re-running upload updates existing cards rather than creating duplicates.

---

## Configuration

Three env vars in `.env` (alongside existing `MOCHI_API_KEY`):

```
MOCHI_API_KEY=...       # already present
MOCHI_DECK_ID=...       # user copies from Mochi app
MOCHI_TEMPLATE_ID=...   # user copies from Mochi app
```

Missing vars raise `RuntimeError` with a clear message at startup.

---

## Module Structure

New module `nextword/mochi/` mirrors the existing `nextword/cards/` pattern:

```
nextword/mochi/
  __init__.py
  client.py     # Mochi client init + env var loading
  upload.py     # field discovery, create/update, retry, state
```

New data file:

```
data/mochi_state.json   # { "word": "mochi_card_id", ... }
```

---

## Data Flow

### `nextword mochi upload`

1. Read `MOCHI_API_KEY`, `MOCHI_DECK_ID`, `MOCHI_TEMPLATE_ID` from `.env` — raise on missing.
2. Call `mochi.templates.get_template(template_id)` → extract field name→ID mapping:
   ```python
   # e.g. {"Word": "abc1", "Definition": "abc2", ...}
   ```
   Cached in memory for the duration of the run.
3. Load `data/cards.json` and `data/mochi_state.json` (empty dict if missing).
4. For each card in `cards.json`:
   - `content = card["fields"]["Word"]`
   - Build `fields_payload`:
     ```python
     {fid: {"id": fid, "value": card["fields"][fname]}
      for fname, fid in field_id_map.items()}
     ```
   - If `word` in state → `update_card(card_id, content=..., fields=...)`
   - Else → `create_card(content, deck_id, template_id=..., fields=...)`
   - Both calls wrapped with **exponential backoff retry**: 3 attempts, delays 1s / 2s / 4s on `HTTPError`.
   - On success: write `word → card_id` into state dict.
   - On final failure after retries: log word as failed, continue.
5. Write updated `data/mochi_state.json`.
6. Print summary: `Uploaded N cards (X new, Y updated, Z failed)`.

### `nextword mochi preview <word>`

- Look up `word` in `data/cards.json`; error if not found.
- Print to stdout what would be sent (no API call):
  ```
  content: "undertake"
  deck_id: <MOCHI_DECK_ID>
  template_id: <MOCHI_TEMPLATE_ID>
  fields:
    Word: undertake
    Part of speech: verb
    ...
  ```

---

## Retry Logic

Implemented in `upload.py` without additional dependencies:

```python
def _with_retry(fn, *, attempts=3):
    for i in range(attempts):
        try:
            return fn()
        except HTTPError:
            if i == attempts - 1:
                raise
            time.sleep(2 ** i)
```

---

## Error Handling

- Missing env vars → `RuntimeError` at startup (fail fast, no partial uploads).
- `cards.json` missing or empty → `RuntimeError`.
- Per-card `HTTPError` after all retries → word added to `failed` list; upload continues.
- `get_template` failure → `RuntimeError` (can't proceed without field IDs).
- Field name not found in template → `RuntimeError` with message listing missing fields (catches template mismatch early).

---

## CLI Integration

New subcommand tree added to `nextword/cli.py`:

```
nextword mochi upload           # upload all cards from data/cards.json
nextword mochi preview <word>   # dry-run: print payload for one word
```

---

## Files Changed / Created

| File | Change |
|------|--------|
| `nextword/mochi/__init__.py` | new (empty) |
| `nextword/mochi/client.py` | new |
| `nextword/mochi/upload.py` | new |
| `nextword/cli.py` | add `mochi` subparser |
| `data/mochi_state.json` | generated at runtime |
| `.env` | user adds `MOCHI_DECK_ID`, `MOCHI_TEMPLATE_ID` |

---

## Out of Scope

- Deleting cards from Mochi (not needed for current workflow)
- Automatic template creation (user creates template manually)
- Parallel uploads (sequential is fine; deck sizes are small)
- Jinja templating (not needed; Mochi renders fields via its own template syntax)
