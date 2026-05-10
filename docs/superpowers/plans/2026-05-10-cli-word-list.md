# CLI Word List Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TUI-утилита на Python/Textual для просмотра слов из words.db с чекбоксами и экспортом в CSV.

**Architecture:** Три файла с чёткими обязанностями: `db.py` изолирует SQLite-запросы, `app.py` содержит все три Textual-экрана, `cli.py` — точка входа. Данные передаются между экранами через параметры конструктора.

**Tech Stack:** Python 3.11+, Textual, SQLite3 (stdlib), csv (stdlib), pytest.

---

## File Map

| Файл | Действие | Назначение |
|---|---|---|
| `pyproject.toml` | Modify | Добавить зависимость textual |
| `nextword/db.py` | Create | SQLite-запросы к words.db |
| `nextword/app.py` | Create | Textual App + LevelScreen, SublevelScreen, WordListScreen |
| `nextword/cli.py` | Create | Точка входа |
| `tests/test_db.py` | Create | Тесты для db.py |

---

## Task 1: Add textual dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Добавить textual и pytest в зависимости**

```bash
cd /path/to/NextWord
poetry add textual
poetry add --group dev pytest
```

- [ ] **Step 2: Проверить установку**

```bash
poetry run python -c "import textual; print(textual.__version__)"
```

Expected: выводится версия textual (например, `0.x.x`), без ошибок.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "feat: add textual and pytest dependencies"
```

---

## Task 2: Implement db.py with TDD

**Files:**
- Create: `nextword/db.py`
- Create: `tests/__init__.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Создать структуру директорий**

```bash
mkdir -p nextword tests
touch nextword/__init__.py tests/__init__.py
```

- [ ] **Step 2: Написать failing тест**

Создать `tests/test_db.py`:

```python
import sqlite3
import pytest
from nextword.db import get_words


@pytest.fixture
def db_path(tmp_path):
    db = tmp_path / "test_words.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE words (
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL,
            part_of_speech TEXT,
            level TEXT,
            sublevel TEXT,
            definition TEXT,
            example TEXT,
            translation TEXT,
            collocations TEXT,
            synonyms_nuance TEXT,
            cloze TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO words (word, level, sublevel, translation) VALUES (?, ?, ?, ?)",
        [
            ("allow",   "A2", "beginner",     "разрешать"),
            ("appear",  "A2", "beginner",     "появляться"),
            ("believe", "B1", "intermediate", "верить"),
        ],
    )
    conn.commit()
    conn.close()
    return str(db)


def test_get_words_returns_matching_level_and_sublevel(db_path):
    result = get_words("A2", "beginner", db_path=db_path)
    assert len(result) == 2
    assert result[0] == {"word": "allow", "translation": "разрешать"}
    assert result[1] == {"word": "appear", "translation": "появляться"}


def test_get_words_filters_out_other_levels(db_path):
    result = get_words("B1", "intermediate", db_path=db_path)
    assert len(result) == 1
    assert result[0]["word"] == "believe"


def test_get_words_returns_empty_for_no_match(db_path):
    result = get_words("C1", "advance", db_path=db_path)
    assert result == []
```

- [ ] **Step 3: Запустить тест и убедиться, что он падает**

```bash
poetry run pytest tests/test_db.py -v
```

Expected: `ImportError` или `ModuleNotFoundError` — `nextword.db` не существует.

- [ ] **Step 4: Реализовать `nextword/db.py`**

```python
import sqlite3

DB_PATH = "data/words.db"


def get_words(level: str, sublevel: str, db_path: str = DB_PATH) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT word, translation FROM words WHERE level = ? AND sublevel = ? ORDER BY word",
        (level, sublevel),
    ).fetchall()
    conn.close()
    return [{"word": row["word"], "translation": row["translation"]} for row in rows]
```

- [ ] **Step 5: Запустить тесты и убедиться, что они проходят**

```bash
poetry run pytest tests/test_db.py -v
```

Expected:
```
PASSED tests/test_db.py::test_get_words_returns_matching_level_and_sublevel
PASSED tests/test_db.py::test_get_words_filters_out_other_levels
PASSED tests/test_db.py::test_get_words_returns_empty_for_no_match
```

- [ ] **Step 6: Commit**

```bash
git add nextword/__init__.py nextword/db.py tests/__init__.py tests/test_db.py
git commit -m "feat: add db.py with get_words and tests"
```

---

## Task 3: Implement LevelScreen and SublevelScreen

**Files:**
- Create: `nextword/app.py`

- [ ] **Step 1: Создать `nextword/app.py` с LevelScreen и SublevelScreen**

```python
import csv
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static


LEVELS = ["A2", "B1", "B2", "C1"]
SUBLEVELS = ["beginner", "intermediate", "advance"]


class LevelScreen(Screen):
    BINDINGS = [Binding("q", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            *[ListItem(Label(level), id=f"level-{level}") for level in LEVELS],
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "NextWord — Select Level"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        level = event.item.id.removeprefix("level-")
        self.app.push_screen(SublevelScreen(level))


class SublevelScreen(Screen):
    BINDINGS = [Binding("q", "app.quit", "Quit")]

    def __init__(self, level: str) -> None:
        super().__init__()
        self._level = level

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            *[ListItem(Label(sub), id=f"sub-{sub}") for sub in SUBLEVELS],
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"NextWord — {self._level} — Select Sublevel"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        sublevel = event.item.id.removeprefix("sub-")
        from nextword.db import get_words
        words = get_words(self._level, sublevel)
        self.app.push_screen(WordListScreen(words))


class WordListApp(App):
    def on_mount(self) -> None:
        self.push_screen(LevelScreen())
```

- [ ] **Step 2: Создать минимальный `nextword/cli.py` для ручного теста**

```python
from nextword.app import WordListApp

if __name__ == "__main__":
    WordListApp().run()
```

- [ ] **Step 3: Запустить и проверить два экрана вручную**

```bash
poetry run python nextword/cli.py
```

Проверить:
- Отображается список A2, B1, B2, C1
- Enter переходит к экрану подуровней
- Отображается список beginner, intermediate, advance
- `Q` завершает приложение

- [ ] **Step 4: Commit**

```bash
git add nextword/app.py nextword/cli.py
git commit -m "feat: add LevelScreen and SublevelScreen"
```

---

## Task 4: Implement WordListScreen

**Files:**
- Modify: `nextword/app.py`

- [ ] **Step 1: Добавить класс `WordRow` в `nextword/app.py`** (вставить перед классом `LevelScreen`; все импорты уже есть в файле)

```python
class WordRow(ListItem):
    def __init__(self, word: str, translation: str) -> None:
        super().__init__()
        self.word = word
        self.translation = translation
        self.checked = False

    def compose(self) -> ComposeResult:
        yield Static(self._text(), id="row-label")

    def _text(self) -> str:
        mark = "x" if self.checked else " "
        return f"[{mark}] {self.word:<28} {self.translation}"

    def toggle(self) -> None:
        self.checked = not self.checked
        self.query_one("#row-label", Static).update(self._text())
```

- [ ] **Step 2: Добавить класс `WordListScreen` в `nextword/app.py`** (после `SublevelScreen`; все импорты уже есть в файле)

```python
class WordListScreen(Screen):
    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("q", "app.quit", "Quit"),
        Binding("escape", "app.quit", "Quit", show=False),
        Binding("space", "toggle_item", "Toggle", show=False),
        Binding("enter", "toggle_item", "Toggle", show=False),
        Binding("tab", "toggle_item", "Toggle", show=False),
    ]

    def __init__(self, words: list[dict]) -> None:
        super().__init__()
        self._words = words
        self._highlighted: WordRow | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(*[WordRow(w["word"], w["translation"]) for w in self._words])
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_title()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._highlighted = event.item  # type: ignore[assignment]

    def action_toggle_item(self) -> None:
        if self._highlighted is not None:
            self._highlighted.toggle()
            self._refresh_title()

    def action_save(self) -> None:
        selected = [row.word for row in self.query(WordRow) if row.checked]
        out = Path("data/export.csv")
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["word"])
            for word in selected:
                writer.writerow([word])
        self.app.exit()

    def _refresh_title(self) -> None:
        count = sum(1 for row in self.query(WordRow) if row.checked)
        self.title = f"NextWord Export — Selected: {count}"
```

- [ ] **Step 3: Запустить и проверить `WordListScreen` вручную**

```bash
poetry run python nextword/cli.py
```

Проверить:
- Список слов отображается с `[ ]` перед каждым словом
- Стрелки `↑↓` прокручивают список
- `Space`, `Enter`, `Tab` переключают чекбокс текущего слова
- Заголовок обновляет счётчик `Selected: N`
- `S` сохраняет `data/export.csv` и выходит
- `Q` выходит без сохранения

- [ ] **Step 4: Проверить содержимое CSV после сохранения**

```bash
cat data/export.csv
```

Expected (пример с двумя отмеченными словами):
```
word
allow
appear
```

- [ ] **Step 5: Commit**

```bash
git add nextword/app.py
git commit -m "feat: add WordListScreen with checkbox toggle and CSV export"
```

---

## Task 5: Wire up cli.py entry point

**Files:**
- Modify: `nextword/cli.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Обновить `nextword/cli.py`**

```python
from nextword.app import WordListApp


def main() -> None:
    WordListApp().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Добавить entrypoint в `pyproject.toml`**

Добавить секцию `[project.scripts]` (или `[tool.poetry.scripts]` для poetry):

```toml
[tool.poetry.scripts]
nextword = "nextword.cli:main"
```

- [ ] **Step 3: Установить пакет и проверить команду**

```bash
poetry install
poetry run nextword
```

Expected: приложение запускается, отображается `LevelScreen`.

- [ ] **Step 4: Запустить все тесты финально**

```bash
poetry run pytest tests/ -v
```

Expected: все тесты проходят.

- [ ] **Step 5: Commit**

```bash
git add nextword/cli.py pyproject.toml
git commit -m "feat: add nextword CLI entrypoint"
```
