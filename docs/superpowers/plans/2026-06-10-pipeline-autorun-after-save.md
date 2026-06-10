# Pipeline Autorun After /save — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** После подтверждённого `/save` в TUI автоматически прогонять цепочку `export.csv → cards.json → Mochi` без ручного запуска CLI-подкоманд.

**Architecture:** TUI при подтверждении пишет `export.csv` и выходит через `app.exit(result="run_pipeline")`. `cli.main()` ловит этот сигнал после `app.run()` и в обычном терминале вызывает `pipeline.generate()`, затем (если есть карточки) `mochi.upload()`. Шаги пайплайна переиспользуются как есть.

**Tech Stack:** Python 3.11+, Textual (TUI + `ModalScreen`), pytest (+ `unittest.mock`), существующие пакеты `nextword.cards.pipeline` и `nextword.mochi.upload`.

**Spec:** `docs/superpowers/specs/2026-06-10-pipeline-autorun-after-save-design.md`

---

## File Structure

- **Modify `nextword/cli.py`** — вынести оркестрацию пайплайна в `_run_pipeline()`, запуск TUI + диспетчеризацию сигнала в `_run_tui_and_pipeline()`; `main()` зовёт последнюю в ветке «нет подкоманды». Это создаёт тестируемый seam без участия Textual.
- **Modify `nextword/app.py`** — добавить `ConfirmScreen(ModalScreen[bool])`; `action_save` теперь показывает модалку, а запись CSV/позиции/выход переезжает в колбэк `_on_save_confirm`.
- **Modify `tests/test_cli.py`** — тесты на `_run_pipeline` (4 случая) и на диспетчеризацию `_run_tui_and_pipeline` (2 случая).

`app.py` не покрывается автотестами: в проекте нет async-инфраструктуры (`pytest-asyncio`) и TUI исторически не тестируется. Изменения `app.py` верифицируются ручным смоук-тестом + прогоном существующего набора (он должен остаться зелёным).

---

## Task 1: Pipeline orchestration in `cli.py`

**Files:**
- Modify: `nextword/cli.py:54-56` (ветка запуска TUI в `main`)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Добавить в конец `tests/test_cli.py`:

```python
from unittest.mock import MagicMock, patch

from nextword import cli


def test_run_pipeline_generates_then_uploads():
    with patch("nextword.cards.pipeline.generate", return_value=([{"word": "x"}], [])) as gen, \
         patch("nextword.mochi.upload.upload") as up:
        cli._run_pipeline()
    gen.assert_called_once()
    up.assert_called_once()


def test_run_pipeline_skips_upload_when_no_cards():
    with patch("nextword.cards.pipeline.generate", return_value=([], ["x"])), \
         patch("nextword.mochi.upload.upload") as up:
        cli._run_pipeline()
    up.assert_not_called()


def test_run_pipeline_handles_generate_error():
    with patch("nextword.cards.pipeline.generate", side_effect=RuntimeError("boom")), \
         patch("nextword.mochi.upload.upload") as up:
        cli._run_pipeline()  # must not raise
    up.assert_not_called()


def test_run_pipeline_handles_upload_error():
    with patch("nextword.cards.pipeline.generate", return_value=([{"word": "x"}], [])), \
         patch("nextword.mochi.upload.upload", side_effect=RuntimeError("boom")):
        cli._run_pipeline()  # must not raise


def test_tui_runs_pipeline_when_signaled():
    fake_app = MagicMock()
    fake_app.run.return_value = "run_pipeline"
    with patch("nextword.app.WordListApp", return_value=fake_app), \
         patch("nextword.cli._run_pipeline") as rp:
        cli._run_tui_and_pipeline()
    rp.assert_called_once()


def test_tui_skips_pipeline_on_plain_exit():
    fake_app = MagicMock()
    fake_app.run.return_value = None
    with patch("nextword.app.WordListApp", return_value=fake_app), \
         patch("nextword.cli._run_pipeline") as rp:
        cli._run_tui_and_pipeline()
    rp.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_cli.py -v`
Expected: FAIL — `AttributeError: module 'nextword.cli' has no attribute '_run_pipeline'` (и `_run_tui_and_pipeline`).

- [ ] **Step 3: Implement orchestration in `cli.py`**

Заменить хвост `main()` (строки 54-56):

```python
    from nextword.app import WordListApp

    WordListApp().run()
```

на вызов хелпера и добавить две функции **перед** `main()` (после `build_parser`):

```python
def _run_pipeline() -> None:
    from nextword.cards import pipeline
    from nextword.mochi import upload as mochi_upload

    try:
        cards, _failed = pipeline.generate()
    except Exception as exc:  # noqa: BLE001 — top-level CLI guard, print instead of traceback
        print(f"Card generation failed: {exc}")
        return
    if not cards:
        print("No cards generated; skipping Mochi upload.")
        return
    try:
        mochi_upload.upload()
    except Exception as exc:  # noqa: BLE001
        print(f"Mochi upload failed: {exc}")


def _run_tui_and_pipeline() -> None:
    from nextword.app import WordListApp

    result = WordListApp().run()
    if result == "run_pipeline":
        _run_pipeline()
```

И в `main()` заменить блок запуска TUI на:

```python
    _run_tui_and_pipeline()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_cli.py -v`
Expected: PASS — все 6 новых тестов зелёные, старые (парсинг) тоже.

- [ ] **Step 5: Commit**

```bash
git add nextword/cli.py tests/test_cli.py
git commit -m "feat: run cards+mochi pipeline after TUI save signal"
```

---

## Task 2: Confirmation modal + save handoff in `app.py`

**Files:**
- Modify: `nextword/app.py:7` (импорт `ModalScreen`)
- Modify: `nextword/app.py:260-274` (`action_save`)
- Add: `ConfirmScreen` класс в `nextword/app.py`

Автотестов нет (см. File Structure). Верификация — ручной смоук + зелёный набор.

- [ ] **Step 1: Add `ModalScreen` to the Textual screen import**

Заменить строку 7:

```python
from textual.screen import Screen
```

на:

```python
from textual.screen import ModalScreen, Screen
```

- [ ] **Step 2: Add `ConfirmScreen` class**

Вставить перед `class WordListScreen(Screen):` (строка 136):

```python
class ConfirmScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    ConfirmScreen Static {
        width: auto;
        padding: 1 2;
        border: round $primary;
    }
    """

    BINDINGS = [
        Binding("enter", "confirm", "Yes"),
        Binding("escape", "cancel", "No"),
    ]

    def __init__(self, count: int) -> None:
        super().__init__()
        self._count = count

    def compose(self) -> ComposeResult:
        yield Static(
            f"Generate {self._count} cards and upload to Mochi?\n"
            "Enter — yes,   Esc — cancel"
        )

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
```

- [ ] **Step 3: Split `action_save` into guard + confirm callback**

Заменить текущий `action_save` (строки 260-274):

```python
    def action_save(self) -> None:
        if not self._checked_ids:
            self.notify("No words selected.", severity="warning")
            return
        checked_set = self._checked_ids
        selected = [w["word"] for w in self._all_words if w["id"] in checked_set]
        out = Path(__file__).resolve().parent.parent / "data" / "export.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["word"])
            for word in selected:
                writer.writerow([word])
        _save_position(self._current_word_id())
        self.app.exit(message=f"Saved {len(selected)} words to {out}")
```

на:

```python
    def action_save(self) -> None:
        if not self._checked_ids:
            self.notify("No words selected.", severity="warning")
            return
        self.app.push_screen(ConfirmScreen(len(self._checked_ids)), self._on_save_confirm)

    def _on_save_confirm(self, run_pipeline: bool) -> None:
        if not run_pipeline:
            return
        checked_set = self._checked_ids
        selected = [w["word"] for w in self._all_words if w["id"] in checked_set]
        out = Path(__file__).resolve().parent.parent / "data" / "export.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["word"])
            for word in selected:
                writer.writerow([word])
        _save_position(self._current_word_id())
        self.app.exit(
            result="run_pipeline",
            message=f"Saved {len(selected)} words to {out}",
        )
```

- [ ] **Step 4: Run the full suite to confirm nothing broke**

Run: `poetry run pytest -q`
Expected: PASS — весь набор зелёный (новые cli-тесты + старые).

- [ ] **Step 5: Manual smoke test (Esc path — бесплатно)**

Run: `poetry run nextword`
Действия: выбрать любое слово (`Space`), нажать `s`.
Expected: появляется центрированная модалка «Generate 1 cards and upload to Mochi? Enter — yes, Esc — cancel». Нажать `Esc` → модалка закрывается, возвращаемся к списку, `data/export.csv` **не** изменился (проверить `git status` / mtime). Выйти `q`.

Подтверждённый путь (Enter) запускает платный пайплайн — проверять только при реальном намерении сгенерировать карточки.

- [ ] **Step 6: Commit**

```bash
git add nextword/app.py
git commit -m "feat: confirm modal on save, signal pipeline run on confirm"
```

---

## Self-Review Notes

- **Spec coverage:**
  - «полная цепочка generate + upload» → Task 1 `_run_pipeline`.
  - «диалог подтверждения в TUI, Enter/Esc» → Task 2 `ConfirmScreen`.
  - «убрать чистый CSV-экспорт» → Task 2: `s` всегда ведёт к модалке, отдельного save-only пути нет.
  - «exit→cli.main ловит сигнал» → Task 1 `_run_tui_and_pipeline`.
  - «гейт upload при ≥1 карточке» → Task 1 `if not cards: ... return`.
  - «чистые сообщения вместо трейсбеков» → Task 1 `try/except` вокруг обоих шагов.
  - «parallel, не batch» → `pipeline.generate()` без `use_batch`.
- **Type consistency:** сигнал-строка `"run_pipeline"` одинакова в `_on_save_confirm` (app.py), `_run_tui_and_pipeline` (cli.py) и тестах. `ConfirmScreen.dismiss(bool)` ↔ колбэк `_on_save_confirm(run_pipeline: bool)`. `pipeline.generate()` возвращает `(cards, failed)` — распаковка совпадает с сигнатурой в `nextword/cards/pipeline.py`.
- **Placeholders:** нет — весь код приведён целиком.
