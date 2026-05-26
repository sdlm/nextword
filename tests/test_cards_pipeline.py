import json
from nextword.cards.pipeline import read_words, write_cards


def test_read_words_skips_header_and_blanks(tmp_path):
    csv_file = tmp_path / "export.csv"
    csv_file.write_text("word\nextra\nfact\n\nfactor\n", encoding="utf-8")
    assert read_words(csv_file) == ["extra", "fact", "factor"]


def test_read_words_keeps_first_data_row_when_not_header(tmp_path):
    csv_file = tmp_path / "export.csv"
    csv_file.write_text("extra\nfact\n", encoding="utf-8")
    assert read_words(csv_file) == ["extra", "fact"]


def test_write_cards_writes_utf8_json(tmp_path):
    out = tmp_path / "nested" / "cards.json"
    cards = [{"word": "extra", "fields": {"Translation": "дополнительный"}}]
    write_cards(cards, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == cards
    # Russian must not be escaped
    assert "дополнительный" in out.read_text(encoding="utf-8")
