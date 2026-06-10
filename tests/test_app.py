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
