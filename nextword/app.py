import csv
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from nextword.db import get_words


LEVELS = ["A2", "B1", "B2", "C1"]
SUBLEVELS = ["beginner", "intermediate", "advance"]


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
        words = get_words(self._level, sublevel)
        self.app.push_screen(WordListScreen(words))


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
        if not selected:
            self.notify("No words selected.", severity="warning")
            return
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


class WordListApp(App):
    def on_mount(self) -> None:
        self.push_screen(LevelScreen())
