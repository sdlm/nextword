# Mochi Upload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `nextword mochi upload` and `nextword mochi preview` commands that push generated cards from `data/cards.json` to a Mochi deck using the Mochi REST API.

**Architecture:** New module `nextword/mochi/` (client init + upload logic), following the same pattern as `nextword/cards/`. Cards are created with `template-id` + `fields` payload; state is persisted incrementally in `data/mochi_state.json` (word → card_id) to support idempotent re-runs via `update_card`.

**Tech Stack:** `mochi-api-client` (already installed), `python-dotenv`, `requests.exceptions.HTTPError`, `pytest` with `tmp_path` / `monkeypatch` fixtures.

**Spec:** `docs/superpowers/specs/2026-05-27-mochi-upload-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `nextword/mochi/__init__.py` | Create | Empty package marker |
| `nextword/mochi/client.py` | Create | Load env vars, return initialised `Mochi` client |
| `nextword/mochi/upload.py` | Create | All upload logic: field discovery, state I/O, retry, orchestration, preview |
| `nextword/cli.py` | Modify | Add `mochi upload` and `mochi preview <word>` subcommands |
| `tests/test_mochi.py` | Create | All mochi tests |
| `data/mochi_state.json` | Runtime | Generated; not committed |

---

## Task 1: Package skeleton + `client.py`

**Files:**
- Create: `nextword/mochi/__init__.py`
- Create: `nextword/mochi/client.py`
- Test: `tests/test_mochi.py`

### Interfaces

```python
# nextword/mochi/client.py
from mochi.auth import Auth
from mochi.client import Mochi

def make_client() -> tuple[Mochi, str, str]:
    """Load .env, return (mochi_client, deck_id, template_id).

    Reads: MOCHI_API_KEY, MOCHI_DECK_ID, MOCHI_TEMPLATE_ID.
    Raises RuntimeError if any var is missing.
    """
```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mochi.py
import pytest
from nextword.mochi.client import make_client

def test_make_client_raises_if_api_key_missing(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    monkeypatch.delenv("MOCHI_DECK_ID", raising=False)
    monkeypatch.delenv("MOCHI_TEMPLATE_ID", raising=False)
    with pytest.raises(RuntimeError, match="MOCHI_API_KEY"):
        make_client()

def test_make_client_raises_if_deck_id_missing(monkeypatch):
    monkeypatch.setenv("MOCHI_API_KEY", "key")
    monkeypatch.delenv("MOCHI_DECK_ID", raising=False)
    monkeypatch.setenv("MOCHI_TEMPLATE_ID", "tmpl")
    with pytest.raises(RuntimeError, match="MOCHI_DECK_ID"):
        make_client()

def test_make_client_raises_if_template_id_missing(monkeypatch):
    monkeypatch.setenv("MOCHI_API_KEY", "key")
    monkeypatch.setenv("MOCHI_DECK_ID", "deck")
    monkeypatch.delenv("MOCHI_TEMPLATE_ID", raising=False)
    with pytest.raises(RuntimeError, match="MOCHI_TEMPLATE_ID"):
        make_client()
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_mochi.py -v
```

Expected: ImportError or 3 FAILs.

- [ ] **Step 3: Create `nextword/mochi/__init__.py`** (empty)

- [ ] **Step 4: Implement `make_client()`**

Use `load_dotenv()` then `os.environ.get(...)`. Check each var, raise `RuntimeError(f"<VAR> is not set")` if missing. Return `(Mochi(Auth.Token(api_key)), deck_id, template_id)`.

- [ ] **Step 5: Run tests — verify they pass**

```
pytest tests/test_mochi.py -v
```

- [ ] **Step 6: Commit**

```
git add nextword/mochi/ tests/test_mochi.py
git commit -m "feat: add nextword/mochi package with client factory"
```

---

## Task 2: Pure helpers — field mapping, state I/O, payload builder

**Files:**
- Create: `nextword/mochi/upload.py`
- Test: `tests/test_mochi.py`

### Interfaces

```python
# nextword/mochi/upload.py
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_CARDS = _DATA_DIR / "cards.json"
DEFAULT_STATE = _DATA_DIR / "mochi_state.json"

def get_field_id_map(template: dict) -> dict[str, str]:
    """Extract {display_name: field_id} from get_template() response.

    e.g. {"Word": "name", "Definition": "C8cx6HFb", "Cloze": "9sbCiG4l", ...}
    """

def load_state(path: Path) -> dict[str, str]:
    """Return word→card_id dict from mochi_state.json. Return {} if file missing."""

def save_state(path: Path, state: dict[str, str]) -> None:
    """Write word→card_id dict to mochi_state.json (creates parent dirs)."""

def build_fields_payload(
    card_fields: dict[str, str],
    field_id_map: dict[str, str],
) -> dict:
    """Convert card fields + name→ID map to Mochi API fields payload.

    Returns: {field_id: {"id": field_id, "value": field_value}, ...}
    """
```

- [ ] **Step 1: Write failing tests**

```python
# Real template response (abridged) — use as fixture input
TEMPLATE_FIXTURE = {
    "fields": {
        "name":     {"id": "name",     "name": "Word"},
        "39H26Wpc": {"id": "39H26Wpc", "name": "Part of speech"},
        "C8cx6HFb": {"id": "C8cx6HFb", "name": "Definition"},
        "9sbCiG4l": {"id": "9sbCiG4l", "name": "Cloze"},
    }
}

def test_get_field_id_map_word_maps_to_name():
    result = get_field_id_map(TEMPLATE_FIXTURE)
    assert result["Word"] == "name"

def test_get_field_id_map_all_fields_present():
    result = get_field_id_map(TEMPLATE_FIXTURE)
    assert result["Part of speech"] == "39H26Wpc"
    assert result["Definition"] == "C8cx6HFb"
    assert result["Cloze"] == "9sbCiG4l"

def test_load_state_returns_empty_dict_if_missing(tmp_path):
    assert load_state(tmp_path / "nope.json") == {}

def test_save_and_load_state_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = {"extra": "card_abc", "fact": "card_xyz"}
    save_state(path, state)
    assert load_state(path) == state

def test_build_fields_payload_structure():
    field_id_map = {"Word": "name", "Definition": "C8cx6HFb"}
    card_fields = {"Word": "undertake", "Definition": "to take on a task"}
    payload = build_fields_payload(card_fields, field_id_map)
    assert payload == {
        "name":     {"id": "name",     "value": "undertake"},
        "C8cx6HFb": {"id": "C8cx6HFb", "value": "to take on a task"},
    }
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_mochi.py -v
```

- [ ] **Step 3: Create `nextword/mochi/upload.py`** with the four functions

- [ ] **Step 4: Run tests — verify they pass**

```
pytest tests/test_mochi.py -v
```

- [ ] **Step 5: Commit**

```
git add nextword/mochi/upload.py tests/test_mochi.py
git commit -m "feat: add field mapping, state I/O, and payload builder"
```

---

## Task 3: Retry helper

**Files:**
- Modify: `nextword/mochi/upload.py`
- Test: `tests/test_mochi.py`

### Interface

```python
import time
from typing import Callable, Any
from requests.exceptions import HTTPError

def _with_retry(fn: Callable, *, attempts: int = 3, sleep=time.sleep) -> Any:
    """Call fn(). On HTTPError retry up to `attempts` times with 1s/2s/4s backoff.

    Raises the last HTTPError if all attempts fail.
    """
```

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import MagicMock, call
from requests.exceptions import HTTPError
from nextword.mochi.upload import _with_retry

def test_retry_succeeds_on_first_try():
    fn = MagicMock(return_value="ok")
    assert _with_retry(fn) == "ok"
    fn.assert_called_once()

def test_retry_succeeds_after_two_failures():
    fn = MagicMock(side_effect=[HTTPError(), HTTPError(), "ok"])
    sleep = MagicMock()
    assert _with_retry(fn, sleep=sleep) == "ok"
    assert fn.call_count == 3
    assert sleep.call_args_list == [call(1), call(2)]

def test_retry_raises_after_all_attempts_fail():
    fn = MagicMock(side_effect=HTTPError("boom"))
    sleep = MagicMock()
    with pytest.raises(HTTPError):
        _with_retry(fn, sleep=sleep)
    assert fn.call_count == 3
    assert sleep.call_count == 2
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_mochi.py::test_retry_succeeds_on_first_try \
       tests/test_mochi.py::test_retry_succeeds_after_two_failures \
       tests/test_mochi.py::test_retry_raises_after_all_attempts_fail -v
```

- [ ] **Step 3: Implement `_with_retry`** in `upload.py`

- [ ] **Step 4: Run tests — verify they pass**

```
pytest tests/test_mochi.py -v
```

- [ ] **Step 5: Commit**

```
git add nextword/mochi/upload.py tests/test_mochi.py
git commit -m "feat: add retry helper with exponential backoff"
```

---

## Task 4: `upload()` orchestration

**Files:**
- Modify: `nextword/mochi/upload.py`
- Test: `tests/test_mochi.py`

### Interface

```python
def upload(
    cards_path: Path = DEFAULT_CARDS,
    state_path: Path = DEFAULT_STATE,
    *,
    client=None,          # injectable: Mochi instance (or None → make_client())
    deck_id: str | None = None,
    template_id: str | None = None,
    sleep=time.sleep,
) -> tuple[int, int, list[str]]:
    """Upload all cards from cards_path to Mochi.

    - New word (not in state): create_card(content, deck_id, template_id=..., fields=...)
    - Existing word (in state): update_card(card_id, content=..., fields=...)
      NOTE: update_card receives ONLY content and fields — not template_id or deck_id.
    - State is written to disk after EACH successful card (incremental persistence).
    - Failed words (HTTPError after retries) are collected and returned.

    Returns: (new_count, updated_count, failed_words)
    """
```

**Test setup pattern** — use `SimpleNamespace` (same as `test_cards_pipeline.py`), inject `client` directly:

```python
from types import SimpleNamespace
from unittest.mock import MagicMock

def _make_mock_client(template_fixture, card_id="card_001"):
    client = SimpleNamespace(
        templates=SimpleNamespace(
            get_template=MagicMock(return_value=template_fixture)
        ),
        cards=SimpleNamespace(
            create_card=MagicMock(return_value={"id": card_id}),
            update_card=MagicMock(return_value={"id": card_id}),
        ),
    )
    return client
```

- [ ] **Step 1: Write failing tests**

```python
import json
from nextword.mochi.upload import upload

CARDS_FIXTURE = [
    {"word": "extra", "fields": {
        "Word": "extra", "Part of speech": "adjective",
        "Definition": "More than usual", "Example": "Extra chairs.",
        "Translation": "дополнительный", "Collocations": "extra time",
        "Synonyms & Nuance": "additional", "Cloze": "We ordered [...] chairs.",
    }},
    {"word": "fact", "fields": {
        "Word": "fact", "Part of speech": "noun",
        "Definition": "A known truth", "Example": "That is a fact.",
        "Translation": "факт", "Collocations": "hard fact",
        "Synonyms & Nuance": "truth", "Cloze": "Base it on [...].",
    }},
]

FULL_TEMPLATE_FIXTURE = {
    "fields": {
        "name":     {"id": "name",     "name": "Word"},
        "39H26Wpc": {"id": "39H26Wpc", "name": "Part of speech"},
        "C8cx6HFb": {"id": "C8cx6HFb", "name": "Definition"},
        "fYg9Kx07": {"id": "fYg9Kx07", "name": "Example"},
        "yeAAPAUQ": {"id": "yeAAPAUQ", "name": "Translation"},
        "igIW8zAx": {"id": "igIW8zAx", "name": "Collocations"},
        "THTJKPzM": {"id": "THTJKPzM", "name": "Synonyms & Nuance"},
        "9sbCiG4l": {"id": "9sbCiG4l", "name": "Cloze"},
    }
}

def test_upload_creates_new_cards(tmp_path):
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps(CARDS_FIXTURE), encoding="utf-8")
    state_path = tmp_path / "state.json"
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)

    new, updated, failed = upload(
        cards_file, state_path,
        client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None,
    )

    assert new == 2
    assert updated == 0
    assert failed == []
    assert client.cards.create_card.call_count == 2
    assert client.cards.update_card.call_count == 0

def test_upload_content_is_word(tmp_path):
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps([CARDS_FIXTURE[0]]), encoding="utf-8")
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)

    upload(cards_file, tmp_path / "state.json",
           client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None)

    args, kwargs = client.cards.create_card.call_args
    assert args[0] == "extra"   # content = word

def test_upload_update_receives_only_content_and_fields(tmp_path):
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps([CARDS_FIXTURE[0]]), encoding="utf-8")
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"extra": "card_001"}), encoding="utf-8")
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)

    upload(cards_file, state_path,
           client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None)

    assert client.cards.update_card.call_count == 1
    assert client.cards.create_card.call_count == 0
    _, kwargs = client.cards.update_card.call_args
    assert "template_id" not in kwargs
    assert "deck_id" not in kwargs
    assert "content" in kwargs
    assert "fields" in kwargs

def test_upload_writes_state_incrementally(tmp_path):
    """State must be on disk after each card, not just at the end."""
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps(CARDS_FIXTURE), encoding="utf-8")
    state_path = tmp_path / "state.json"

    saved_after_first: list[dict] = []

    original_create = MagicMock(side_effect=lambda *a, **kw: {"id": f"card_{a[0]}"})

    def capturing_create(*args, **kwargs):
        result = original_create(*args, **kwargs)
        # snapshot state from disk immediately after this call
        saved_after_first.append(json.loads(state_path.read_text()))
        return result

    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)
    client.cards.create_card = capturing_create

    upload(cards_file, state_path,
           client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None)

    # After the first card is created, "extra" should already be in state
    assert "extra" in saved_after_first[0]

def test_upload_collects_failures_and_continues(tmp_path):
    from requests.exceptions import HTTPError
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps(CARDS_FIXTURE), encoding="utf-8")
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)
    client.cards.create_card = MagicMock(
        side_effect=[HTTPError(), HTTPError(), HTTPError(),   # extra: 3 failures
                     {"id": "card_fact"}]                     # fact: success
    )

    new, updated, failed = upload(
        cards_file, tmp_path / "state.json",
        client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None,
    )

    assert "extra" in failed
    assert new == 1
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_mochi.py -k "upload" -v
```

- [ ] **Step 3: Implement `upload()`** in `upload.py`

Key points:
- Call `client.templates.get_template(template_id)` once at start to build `field_id_map`
- For each card: build payload, call create or update inside `_with_retry`, write state immediately on success
- Print per-card progress line; print summary at end

- [ ] **Step 4: Run tests — verify they pass**

```
pytest tests/test_mochi.py -v
```

- [ ] **Step 5: Commit**

```
git add nextword/mochi/upload.py tests/test_mochi.py
git commit -m "feat: implement upload() with incremental state and retry"
```

---

## Task 5: `preview()`

**Files:**
- Modify: `nextword/mochi/upload.py`
- Test: `tests/test_mochi.py`

### Interface

```python
def preview(word: str, cards_path: Path = DEFAULT_CARDS) -> None:
    """Print what would be sent to Mochi for the given word. No API calls.

    Reads MOCHI_DECK_ID and MOCHI_TEMPLATE_ID from env (via load_dotenv).
    Prints field names and values — does NOT resolve field IDs (no API needed).
    Raises RuntimeError if word not found in cards_path.
    """
```

Output format (approximate):
```
word:        extra
deck_id:     <MOCHI_DECK_ID>
template_id: <MOCHI_TEMPLATE_ID>

fields:
  Word:              extra
  Part of speech:    adjective
  Definition:        More than what is usual...
  ...
```

- [ ] **Step 1: Write failing tests**

```python
import json
from nextword.mochi.upload import preview

def test_preview_prints_word_and_fields(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("MOCHI_DECK_ID", "deck123")
    monkeypatch.setenv("MOCHI_TEMPLATE_ID", "tmpl456")
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps([CARDS_FIXTURE[0]]), encoding="utf-8")

    preview("extra", cards_path=cards_file)

    out = capsys.readouterr().out
    assert "extra" in out
    assert "deck123" in out
    assert "tmpl456" in out
    assert "adjective" in out

def test_preview_raises_if_word_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCHI_DECK_ID", "d")
    monkeypatch.setenv("MOCHI_TEMPLATE_ID", "t")
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps([CARDS_FIXTURE[0]]), encoding="utf-8")

    with pytest.raises(RuntimeError, match="unknown"):
        preview("unknown", cards_path=cards_file)
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_mochi.py -k "preview" -v
```

- [ ] **Step 3: Implement `preview()`**

Read cards.json, find the word (raise RuntimeError if missing), load MOCHI_DECK_ID and MOCHI_TEMPLATE_ID from env, print structured output.

- [ ] **Step 4: Run tests — verify they pass**

```
pytest tests/test_mochi.py -v
```

- [ ] **Step 5: Commit**

```
git add nextword/mochi/upload.py tests/test_mochi.py
git commit -m "feat: add preview() dry-run for mochi upload"
```

---

## Task 6: CLI integration

**Files:**
- Modify: `nextword/cli.py`
- Test: `tests/test_cli.py`

### New subcommands

```
nextword mochi upload
nextword mochi preview <word>
```

Add to `build_parser()` after the `cards` block:

```python
mochi = sub.add_parser("mochi", help="Mochi card upload")
mochi_sub = mochi.add_subparsers(dest="mochi_command")
mochi_sub.add_parser("upload", help="Upload cards.json to Mochi")
mochi_preview = mochi_sub.add_parser("preview", help="Dry-run: print payload for one word")
mochi_preview.add_argument("word", help="Word to preview")
```

Dispatch in `main()`:

```python
if args.command == "mochi":
    from nextword.mochi import upload as mochi_upload
    if args.mochi_command == "upload":
        mochi_upload.upload()
    elif args.mochi_command == "preview":
        mochi_upload.preview(args.word)
    else:
        build_parser().parse_args(["mochi", "--help"])
    return
```

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py  (append to existing file)

def test_mochi_upload_parses():
    args = build_parser().parse_args(["mochi", "upload"])
    assert args.command == "mochi"
    assert args.mochi_command == "upload"

def test_mochi_preview_parses_word():
    args = build_parser().parse_args(["mochi", "preview", "undertake"])
    assert args.command == "mochi"
    assert args.mochi_command == "preview"
    assert args.word == "undertake"
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_cli.py -v
```

- [ ] **Step 3: Update `build_parser()` and `main()`** in `nextword/cli.py`

- [ ] **Step 4: Run all tests — verify they pass**

```
pytest -v
```

- [ ] **Step 5: Commit**

```
git add nextword/cli.py tests/test_cli.py
git commit -m "feat: add nextword mochi upload/preview CLI commands"
```

---

## Self-Review Checklist

- [x] **Spec coverage:**
  - `MOCHI_DECK_ID` / `MOCHI_TEMPLATE_ID` env vars → Task 1
  - `get_template` field discovery → Task 2
  - `load_state` / `save_state` → Task 2
  - `build_fields_payload` → Task 2
  - Retry with backoff → Task 3
  - `upload()` create/update + incremental state → Task 4
  - `update_card` receives only `content` + `fields` → Task 4 test
  - Failed words collected, upload continues → Task 4 test
  - `preview()` no API call → Task 5
  - CLI routing → Task 6
- [x] **No placeholders** — all test assertions and interfaces are concrete
- [x] **Type consistency** — `get_field_id_map` returns `dict[str, str]` used consistently in `build_fields_payload` and `upload`; `load_state` / `save_state` both use `dict[str, str]`
