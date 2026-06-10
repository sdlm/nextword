# Подсветка загруженных в Mochi слов — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Внутри TUI окрашивать в зелёный всю строку слова, уже загруженного в Mochi.

**Architecture:** Источник истины — `data/mochi_state.json` (`{word: card_id}`), читается один раз при открытии списка. `WordRow` получает флаг `loaded`; если он `True`, `_text()` оборачивает строку в Rich-разметку `[green]…[/green]`. Все изменения — в `nextword/app.py`, новых модулей нет.

**Tech Stack:** Python, Textual, pytest.

**Спека:** `docs/superpowers/specs/2026-06-10-mochi-loaded-highlight-design.md`

**Принцип:** минимум кода. Не добавлять регистронезависимость, перечитывание файла, настройки цвета — всё это вне scope.

---

## File Structure

- **Modify** `nextword/app.py`:
  - новая константа `_MOCHI_STATE_PATH`;
  - новый хелпер `_load_mochi_words(path=_MOCHI_STATE_PATH) -> set[str]`;
  - `WordRow.__init__` — параметр `loaded: bool = False`;
  - `WordRow._text()` — обёртка `[green]…[/green]` при `self.loaded`;
  - `WordListScreen.__init__` — `self._loaded_words = _load_mochi_words()`;
  - `WordListScreen.compose()` и `_rebuild_list()` — передача `loaded=...`.
- **Create** `tests/test_app.py` — юнит-тесты `_load_mochi_words` и `WordRow._text()`.

---

### Task 1: Хелпер `_load_mochi_words()`

**Files:**
- Modify: `nextword/app.py` (рядом с `_POSITION_PATH` / `_load_position`)
- Test: `tests/test_app.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_app.py`:

```python
import json

from nextword.app import WordRow, _load_mochi_words


def test_load_mochi_words_returns_keys(tmp_path):
    state = tmp_path / "mochi_state.json"
    state.write_text(
        json.dumps({"reluctant": "abc", "genuine": "def"}),
        encoding="utf-8",
    )
    assert _load_mochi_words(state) == {"reluctant", "genuine"}


def test_load_mochi_words_missing_file_returns_empty(tmp_path):
    assert _load_mochi_words(tmp_path / "nope.json") == set()
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `pytest tests/test_app.py -v`
Expected: FAIL — `ImportError: cannot import name '_load_mochi_words'`

- [ ] **Step 3: Минимальная реализация**

В `nextword/app.py` после блока `_POSITION_PATH` / `_load_position` / `_save_position`
(перед `PAGE_SIZE` или сразу за ним — рядом с другими хелперами) добавить:

```python
_MOCHI_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "mochi_state.json"


def _load_mochi_words(path: Path = _MOCHI_STATE_PATH) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.keys())
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return set()
```

(`json` и `Path` уже импортированы в файле.)

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `pytest tests/test_app.py -v`
Expected: PASS (2 passed) — кроме теста на `WordRow`, которого ещё нет (он появится в Task 2).

- [ ] **Step 5: Commit**

```bash
git add nextword/app.py tests/test_app.py
git commit -m "feat: add _load_mochi_words helper"
```

---

### Task 2: Зелёная подсветка в `WordRow`

**Files:**
- Modify: `nextword/app.py` — `WordRow.__init__`, `WordRow._text()`
- Test: `tests/test_app.py`

- [ ] **Step 1: Написать падающий тест**

Добавить в `tests/test_app.py`:

```python
def _make_row(loaded: bool) -> WordRow:
    return WordRow(
        word="reluctant",
        translation="неохотный — 80%",
        global_num=841,
        sublevel_num=14,
        level="B1",
        sublevel="intermediate",
        loaded=loaded,
    )


def test_text_wraps_loaded_word_in_green():
    text = _make_row(loaded=True)._text()
    assert text.startswith("[green]")
    assert text.endswith("[/green]")
    assert "reluctant" in text


def test_text_no_green_when_not_loaded():
    text = _make_row(loaded=False)._text()
    assert "[green]" not in text
    assert "reluctant" in text
```

- [ ] **Step 2: Запустить тест — убедиться, что падает**

Run: `pytest tests/test_app.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'loaded'`

- [ ] **Step 3: Минимальная реализация**

В `nextword/app.py`, `WordRow.__init__` — добавить параметр `loaded` (последним,
после `checked`) и сохранить его:

```python
    def __init__(
        self,
        word: str,
        translation: str,
        global_num: int,
        sublevel_num: int,
        level: str,
        sublevel: str,
        checked: bool = False,
        loaded: bool = False,
    ) -> None:
        super().__init__()
        self.word = word
        self.translation = translation
        self.global_num = global_num
        self.sublevel_num = sublevel_num
        self.level = level
        self.sublevel = sublevel
        self.checked = checked
        self.loaded = loaded
```

В `WordRow._text()` — обернуть итоговую строку в зелёный при `self.loaded`.
Текущий `return (...)` заменить на присваивание + обёртку:

```python
    def _text(self) -> str:
        mark = "x" if self.checked else " "
        first_line = self.translation.split("\n")[0]
        sub_short = _SUBLEVEL_SHORT.get(self.sublevel, self.sublevel[:6])
        line = (
            f"\\[{mark}] {self.level:<3} {sub_short:<6}"
            f"  {self.global_num:<5} / {self.sublevel_num:>3} {self.word:<28} {first_line}"
        )
        if self.loaded:
            return f"[green]{line}[/green]"
        return line
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `pytest tests/test_app.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add nextword/app.py tests/test_app.py
git commit -m "feat: render Mochi-loaded words in green in WordRow"
```

---

### Task 3: Прокинуть `loaded` из `WordListScreen`

**Files:**
- Modify: `nextword/app.py` — `WordListScreen.__init__`, `compose()`, `_rebuild_list()`

- [ ] **Step 1: Загрузить состояние один раз в `__init__`**

В `WordListScreen.__init__`, рядом с `self._checked_ids: set[int] = set()`, добавить:

```python
        self._loaded_words = _load_mochi_words()
```

- [ ] **Step 2: Передать `loaded` в `compose()`**

В `WordListScreen.compose()`, в конструкторе `WordRow` внутри списка, после
`checked=w["id"] in self._checked_ids,` добавить строку:

```python
                    loaded=w["word"] in self._loaded_words,
```

- [ ] **Step 3: Передать `loaded` в `_rebuild_list()`**

В `WordListScreen._rebuild_list()`, в конструкторе `WordRow` внутри `lv.append(...)`,
после `checked=w["id"] in self._checked_ids,` добавить строку:

```python
                    loaded=w["word"] in self._loaded_words,
```

- [ ] **Step 4: Запустить весь набор тестов и проверку импорта**

Run: `pytest -q`
Expected: PASS (все тесты, включая `tests/test_app.py`)

Run: `python -c "import nextword.app"`
Expected: без ошибок (синтаксис/импорт в порядке)

- [ ] **Step 5: Commit**

```bash
git add nextword/app.py
git commit -m "feat: pass loaded flag to WordRow in word list screen"
```

---

## Self-Review (выполнено при написании плана)

- **Покрытие спеки:** константа (T1), хелпер (T1), `WordRow.loaded` (T2), зелёная
  обёртка в `_text()` (T2), загрузка в `__init__` (T3), прокидывание в `compose`
  и `_rebuild_list` (T3). Тесты — T1/T2. Все пункты спеки покрыты.
- **Плейсхолдеры:** отсутствуют — каждый шаг содержит готовый код/команду.
- **Согласованность типов:** `_load_mochi_words(path) -> set[str]`, `loaded: bool`,
  `self._loaded_words: set[str]`, матчинг `w["word"] in self._loaded_words` —
  имена и типы совпадают во всех задачах.
