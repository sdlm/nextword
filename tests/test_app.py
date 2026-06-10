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
