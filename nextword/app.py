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
