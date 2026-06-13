import io
import json

from rich.console import Console

from nextword.app import WordRow, _freq_bar, _load_mochi_words


def test_load_mochi_words_returns_keys(tmp_path):
    state = tmp_path / "mochi_state.json"
    state.write_text(
        json.dumps({"reluctant": "abc", "genuine": "def"}),
        encoding="utf-8",
    )
    assert _load_mochi_words(state) == {"reluctant", "genuine"}


def test_load_mochi_words_missing_file_returns_empty(tmp_path):
    assert _load_mochi_words(tmp_path / "nope.json") == set()


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


def test_text_wraps_loaded_word_in_green():
    text = _make_row(loaded=True)._text()
    assert text.startswith("[green]")
    assert text.endswith("[/green]")
    assert "reluctant" in text


def test_text_no_green_when_not_loaded():
    text = _make_row(loaded=False)._text()
    assert "[green]" not in text
    assert "reluctant" in text


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
