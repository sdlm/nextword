# TUI Frequency Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the word-number column in the TUI word list with a monochrome frequency bar driven by `wordfreq` Zipf scores.

**Architecture:** `db.py` attaches a numeric `freq` field to each word dict (and drops the now-unused `sublevel_num`). `app.py` gains a pure `_freq_bar()` helper that maps a Zipf score to a `[####------]` bar; `WordRow._text()` renders that bar (escaped, because the bracket style collides with Rich markup) in place of the two numbers, while keeping `global_num` (=`id`) as the selection/position key.

**Tech Stack:** Python 3.11, Textual/Rich (TUI + markup), `wordfreq`, pytest.

**Spec:** `docs/superpowers/specs/2026-06-13-tui-frequency-bar-design.md`

**Run tests with:** `.venv/bin/python -m pytest`

---

## File Structure

- **Modify** `nextword/db.py` — add `freq` to `get_words`/`get_all_words`, remove `sublevel_num` computation.
- **Modify** `nextword/app.py` — add `FREQ_*` constants + `_freq_bar()` helper; change `WordRow` (constructor, `_text()`, two call sites).
- **Modify** `tests/test_db.py` — assert `freq` present, `sublevel_num` absent.
- **Modify** `tests/test_app.py` — update `_make_row` helper signature; add `_freq_bar` unit tests and a render-based `_text()` test.

---

## Task 1: `_freq_bar` pure helper

Additive only — no existing behavior changes, so the suite stays green throughout.

**Files:**
- Modify: `nextword/app.py` (insert constants + helper between `_save_position` and `class WordRow`, around line 53)
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_app.py` (extend the existing `from nextword.app import ...` line to also import `_freq_bar`):

```python
from nextword.app import WordRow, _freq_bar, _load_mochi_words


def test_freq_bar_empty_at_or_below_min():
    assert _freq_bar(0.0) == "[----------]"
    assert _freq_bar(1.0) == "[----------]"
    assert _freq_bar(2.0) == "[----------]"


def test_freq_bar_full_at_or_above_max():
    assert _freq_bar(6.0) == "[##########]"
    assert _freq_bar(7.5) == "[##########]"


def test_freq_bar_partial_at_midpoint():
    assert _freq_bar(4.0) == "[#####-----]"


def test_freq_bar_length_is_width_plus_brackets():
    for f in [0.0, 2.5, 3.7, 5.1, 8.0]:
        assert len(_freq_bar(f)) == 12
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_app.py -q`
Expected: FAIL — `ImportError: cannot import name '_freq_bar'`

- [ ] **Step 3: Implement the helper**

In `nextword/app.py`, insert after the `_save_position` function (currently ends line 52) and before `class WordRow`:

```python
FREQ_MIN = 2.0
FREQ_MAX = 6.0
FREQ_BAR_WIDTH = 10


def _freq_bar(freq: float, width: int = FREQ_BAR_WIDTH) -> str:
    clamped = max(FREQ_MIN, min(FREQ_MAX, freq))
    filled = round((clamped - FREQ_MIN) / (FREQ_MAX - FREQ_MIN) * width)
    filled = max(0, min(width, filled))
    return "[" + "#" * filled + "-" * (width - filled) + "]"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_app.py -q`
Expected: PASS (all existing tests still pass too)

- [ ] **Step 5: Commit**

```bash
git add nextword/app.py tests/test_app.py
git commit -m "feat: add _freq_bar helper mapping zipf score to bar"
```

---

## Task 2: Wire `freq` end-to-end and remove `sublevel_num`

This is one atomic task **on purpose**: `db.py` and its `app.py` consumers must change together. Splitting them would leave a commit where the test suite is green but the app crashes at runtime with `KeyError: 'sublevel_num'` (no test wires db → `WordRow`).

**Critical gotcha (verified empirically):** the `[##########]` bar collides with Rich/Textual markup — the opening `[` is parsed as a tag and the bar **silently disappears at render** (no exception). A substring check on the raw `_text()` string would still pass. So: escape the bar at the embed site, and verify with a **render-based** test, not a raw-string check.

**Files:**
- Modify: `nextword/db.py` (add import, both functions)
- Modify: `nextword/app.py` (add `escape` import; `WordRow.__init__`, `_text()`; call sites in `compose` and `_rebuild_list`)
- Test: `tests/test_db.py`, `tests/test_app.py`

- [ ] **Step 1: Write/update the failing tests**

In `tests/test_db.py`, append:

```python
def test_get_words_includes_freq_and_drops_sublevel_num(db_path):
    result = get_words("A2", "beginner", db_path=db_path)
    assert all(isinstance(r["freq"], float) for r in result)
    allow = next(r for r in result if r["word"] == "allow")
    assert allow["freq"] > 0  # common word -> positive zipf
    assert "sublevel_num" not in result[0]


def test_get_all_words_includes_freq_and_drops_sublevel_num(db_path):
    result = get_all_words(db_path=db_path)
    assert all(isinstance(r["freq"], float) for r in result)
    assert "sublevel_num" not in result[0]
```

In `tests/test_app.py`, replace the `_make_row` helper (currently passes
`sublevel_num=14`) with the new signature, and add a render-based test.
Add these imports near the top of the file:

```python
import io
from rich.console import Console
```

Replace `_make_row`:

```python
def _make_row(loaded: bool) -> WordRow:
    return WordRow(
        word="reluctant",
        translation="неохотный — 80%",
        global_num=841,
        freq=3.5,
        level="B1",
        sublevel="intermediate",
        loaded=loaded,
    )
```

Add a helper + render test:

```python
def _render(text: str) -> str:
    buf = io.StringIO()
    Console(file=buf, width=200, force_terminal=False).print(text)
    return buf.getvalue()


def test_text_renders_freq_bar_and_omits_numbers():
    row = WordRow(
        word="make",
        translation="делать",
        global_num=841,
        freq=6.08,
        level="A2",
        sublevel="beginner",
    )
    rendered = _render(row._text())
    assert "[##########]" in rendered  # full bar survives markup rendering
    assert "841" not in rendered       # word number no longer shown
    assert " / " not in rendered       # old "num / num" separator gone
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_db.py tests/test_app.py -q`
Expected: FAIL — `test_db` raises `KeyError: 'freq'`; `test_app` raises
`TypeError` (WordRow got unexpected `freq` / missing `sublevel_num`).

- [ ] **Step 3: Implement `nextword/db.py`**

Add the import at the top of `nextword/db.py` (after the existing imports):

```python
from wordfreq import zipf_frequency
```

Replace the body of `get_words` (the `return [...]` comprehension) with:

```python
    return [
        {
            "id": row["id"],
            "word": row["word"],
            "translation": row["translation"],
            "level": level,
            "sublevel": sublevel,
            "freq": zipf_frequency(row["word"].strip().lower(), "en"),
        }
        for row in rows
    ]
```

Replace `get_all_words` (everything after the `rows = conn.execute(...)` block) with:

```python
    return [
        {
            "id": row["id"],
            "word": row["word"],
            "translation": row["translation"],
            "level": row["level"],
            "sublevel": row["sublevel"],
            "freq": zipf_frequency(row["word"].strip().lower(), "en"),
        }
        for row in rows
    ]
```

(This removes the `sublevel_counters` dict and the manual `result` loop.)

- [ ] **Step 4: Implement `nextword/app.py`**

Add the import near the top (with the other imports):

```python
from rich.markup import escape
```

Replace `WordRow.__init__` (drop `sublevel_num`, add `freq`; keep `global_num`):

```python
    def __init__(
        self,
        word: str,
        translation: str,
        global_num: int,
        freq: float,
        level: str,
        sublevel: str,
        checked: bool = False,
        loaded: bool = False,
    ) -> None:
        super().__init__()
        self.word = word
        self.translation = translation
        self.global_num = global_num
        self.freq = freq
        self.level = level
        self.sublevel = sublevel
        self.checked = checked
        self.loaded = loaded
```

Replace `_text()`:

```python
    def _text(self) -> str:
        mark = "x" if self.checked else " "
        first_line = self.translation.split("\n")[0]
        sub_short = _SUBLEVEL_SHORT.get(self.sublevel, self.sublevel[:6])
        line = (
            f"\\[{mark}] {self.level:<3} {sub_short:<6}"
            f"  {escape(_freq_bar(self.freq))}  {self.word:<28} {first_line}"
        )
        if self.checked:
            return f"[yellow]{line}[/yellow]"
        if self.loaded:
            return f"[green]{line}[/green]"
        return line
```

In `compose()`, replace the `WordRow(...)` construction (the list
comprehension inside `yield ListView(...)`) with — note `sublevel_num=...`
is gone, `freq=w["freq"]` added, `global_num=w["id"]` kept:

```python
                WordRow(
                    w["word"],
                    w["translation"],
                    global_num=w["id"],
                    freq=w["freq"],
                    level=w["level"],
                    sublevel=w["sublevel"],
                    checked=w["id"] in self._checked_ids,
                    loaded=w["word"] in self._loaded_words,
                )
```

In `_rebuild_list()`, replace the `WordRow(...)` passed to `lv.append(...)`
with the same construction:

```python
            lv.append(
                WordRow(
                    w["word"],
                    w["translation"],
                    global_num=w["id"],
                    freq=w["freq"],
                    level=w["level"],
                    sublevel=w["sublevel"],
                    checked=w["id"] in self._checked_ids,
                    loaded=w["word"] in self._loaded_words,
                )
            )
```

- [ ] **Step 5: Run the full test suite to verify it passes**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (all tests, including the unchanged green/no-green tests)

- [ ] **Step 6: Smoke-test end-to-end against the real DB**

Run:

```bash
.venv/bin/python -c "
from nextword.db import get_all_words
from nextword.app import WordRow
import io
from rich.console import Console
w = get_all_words()[0]
row = WordRow(w['word'], w['translation'], global_num=w['id'], freq=w['freq'], level=w['level'], sublevel=w['sublevel'])
buf = io.StringIO(); Console(file=buf, width=200, force_terminal=False).print(row._text())
print(repr(buf.getvalue()))
"
```

Expected: output contains a `[...]` bar made of `#`/`-` between the
sublevel and the word, and no `NN / NN` number pair.

- [ ] **Step 7: Commit**

```bash
git add nextword/db.py nextword/app.py tests/test_db.py tests/test_app.py
git commit -m "feat: show wordfreq frequency bar instead of word numbers in TUI"
```

---

## Self-Review Notes

- **Spec coverage:** db `freq` field (Task 2 Step 3); `sublevel_num` removal (Task 2 Steps 1, 3); `_freq_bar` with `[2,6]` clamp (Task 1); escaped bar in `_text()` + numbers removed, `global_num` kept (Task 2 Step 4); `freq==0` → empty bar (covered by `_freq_bar(0.0)` test → `[----------]`, Task 1); tests incl. render test (Task 2 Step 1). All spec sections map to a task.
- **`global_num` stays load-bearing:** `_text()` no longer prints it, but the field is kept and `compose`/`_rebuild_list` still pass `global_num=w["id"]`, so `_checked_ids` (app.py:264) and `_current_word_id` (app.py:302) are unaffected.
- **No placeholders:** every code/edit step shows the full code.
- **Type/name consistency:** `freq: float` defined in db dicts (Task 2) and consumed as `WordRow(freq=...)` and `_freq_bar(self.freq)` (Tasks 1–2); `_freq_bar` signature identical everywhere.
