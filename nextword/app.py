import csv
import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from nextword.db import get_all_words, get_words


LEVELS = ["A2", "B1", "B2", "C1"]
SUBLEVELS = ["beginner", "intermediate", "advance"]

_SUBLEVEL_SHORT: dict[str, str] = {
    "beginner": "begin",
    "intermediate": "interm",
    "advance": "advanc",
}

_SETTINGS_PATH = Path.home() / ".config" / "nextword" / "settings.json"
_DEFAULT_THEME = "textual-dark"

_POSITION_PATH = Path(__file__).resolve().parent.parent / "data" / "position.json"
_MOCHI_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "mochi_state.json"

PAGE_SIZE = 300


def _load_position() -> int:
    try:
        data = json.loads(_POSITION_PATH.read_text(encoding="utf-8"))
        return int(data.get("word_id", 1))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 1


def _load_mochi_words(path: Path = _MOCHI_STATE_PATH) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.keys())
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return set()


def _save_position(word_id: int) -> None:
    try:
        _POSITION_PATH.parent.mkdir(parents=True, exist_ok=True)
        _POSITION_PATH.write_text(json.dumps({"word_id": word_id}), encoding="utf-8")
    except OSError:
        pass


class WordRow(ListItem):
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

    def compose(self) -> ComposeResult:
        yield Static(self._text(), id="row-label")

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

    def toggle(self) -> None:
        self.checked = not self.checked
        self.query_one("#row-label", Static).update(self._text())


class LevelScreen(Screen):
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("й", "app.quit", "Quit", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            ListItem(Label("All"), id="level-ALL"),
            *[ListItem(Label(level), id=f"level-{level}") for level in LEVELS],
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "NextWord — Select Level"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        level = event.item.id.removeprefix("level-")
        if level == "ALL":
            words = get_all_words()
            self.app.push_screen(WordListScreen(words, level="All", sublevel="all"))
        else:
            self.app.push_screen(SublevelScreen(level))


class SublevelScreen(Screen):
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("й", "app.quit", "Quit", show=False),
        Binding("escape", "pop_screen", "Back"),
    ]

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
        self.app.push_screen(WordListScreen(words, level=self._level, sublevel=sublevel))


class WordListScreen(Screen):
    BINDINGS = [
        Binding("s", "save", "Save"),
        Binding("ы", "save", "Save", show=False),
        Binding("q", "quit_and_save", "Quit"),
        Binding("й", "quit_and_save", "Quit", show=False),
        Binding("escape", "quit_and_save", "Quit", show=False),
        Binding("space", "toggle_item", "Toggle", show=False),
        Binding("enter", "toggle_item", "Toggle", show=False),
        Binding("[", "prev_page", "Prev page"),
        Binding("х", "prev_page", "Prev page", show=False),
        Binding("]", "next_page", "Next page"),
        Binding("ъ", "next_page", "Next page", show=False),
    ]

    def __init__(
        self,
        words: list[dict],
        level: str,
        sublevel: str,
        initial_page: int = 0,
        initial_idx: int = 0,
    ) -> None:
        super().__init__()
        self._all_words = words
        self._level = level
        self._sublevel = sublevel
        self._page = initial_page
        self._initial_idx = initial_idx
        self._checked_ids: set[int] = set()
        self._highlighted: WordRow | None = None

    @property
    def _total_pages(self) -> int:
        return max(1, (len(self._all_words) + PAGE_SIZE - 1) // PAGE_SIZE)

    @property
    def _page_words(self) -> list[dict]:
        start = self._page * PAGE_SIZE
        return self._all_words[start : start + PAGE_SIZE]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            *[
                WordRow(
                    w["word"],
                    w["translation"],
                    global_num=w["id"],
                    sublevel_num=w["sublevel_num"],
                    level=w["level"],
                    sublevel=w["sublevel"],
                    checked=w["id"] in self._checked_ids,
                )
                for w in self._page_words
            ]
        )
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_title()
        self.call_after_refresh(self._set_initial_cursor)

    def _set_initial_cursor(self) -> None:
        lv = self.query_one(ListView)
        lv.index = self._initial_idx

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._highlighted = event.item  # type: ignore[assignment]
        if event.item:
            self.query_one(ListView).scroll_to_widget(event.item, center=True, animate=False)

    def action_toggle_item(self) -> None:
        if self._highlighted is not None:
            self._highlighted.toggle()
            word_id: int = self._highlighted.global_num
            if self._highlighted.checked:
                self._checked_ids.add(word_id)
            else:
                self._checked_ids.discard(word_id)
            self._refresh_title()

    def action_next_page(self) -> None:
        if self._page < self._total_pages - 1:
            self._page += 1
            self._rebuild_list()

    def action_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._rebuild_list()

    def _rebuild_list(self) -> None:
        self._highlighted = None
        lv = self.query_one(ListView)
        lv.clear()
        for w in self._page_words:
            lv.append(
                WordRow(
                    w["word"],
                    w["translation"],
                    global_num=w["id"],
                    sublevel_num=w["sublevel_num"],
                    level=w["level"],
                    sublevel=w["sublevel"],
                    checked=w["id"] in self._checked_ids,
                )
            )
        self._refresh_title()

    def _current_word_id(self) -> int:
        if self._highlighted is not None:
            return self._highlighted.global_num
        lv = self.query_one(ListView)
        idx = lv.index or 0
        page_words = self._page_words
        if 0 <= idx < len(page_words):
            return page_words[idx]["id"]
        return page_words[0]["id"] if page_words else 1

    def action_quit_and_save(self) -> None:
        _save_position(self._current_word_id())
        self.app.exit()

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

    def _refresh_title(self) -> None:
        self.title = (
            f"NextWord — Page {self._page + 1}/{self._total_pages}"
            f" — Selected: {len(self._checked_ids)}"
        )


def _load_theme() -> str:
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        return str(data.get("theme", _DEFAULT_THEME))
    except (FileNotFoundError, json.JSONDecodeError):
        return _DEFAULT_THEME


def _save_theme(theme: str) -> None:
    try:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_PATH.write_text(json.dumps({"theme": theme}), encoding="utf-8")
    except OSError:
        pass


class WordListApp(App):
    def on_mount(self) -> None:
        self.theme = _load_theme()
        words = get_all_words()
        saved_id = _load_position()
        idx = next((i for i, w in enumerate(words) if w["id"] == saved_id), 0)
        initial_page = idx // PAGE_SIZE
        initial_idx = idx % PAGE_SIZE
        self.push_screen(
            WordListScreen(
                words,
                level="All",
                sublevel="all",
                initial_page=initial_page,
                initial_idx=initial_idx,
            )
        )

    def watch_theme(self, theme: str) -> None:
        _save_theme(theme)
