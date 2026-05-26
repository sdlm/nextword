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


from nextword.cards.pipeline import build_requests
from nextword.cards.schema import CARD_TOOL, MODEL


def test_build_requests_one_per_word_with_indexed_ids():
    reqs = build_requests(["extra", "give up"])
    assert [r["custom_id"] for r in reqs] == ["req-0", "req-1"]


def test_build_request_params_shape():
    req = build_requests(["extra"])[0]
    params = req["params"]
    assert params["model"] == MODEL
    assert params["tools"] == [CARD_TOOL]
    assert params["tool_choice"] == {"type": "tool", "name": "card"}
    assert params["messages"][0]["role"] == "user"
    assert "extra" in params["messages"][0]["content"]
    # system prompt is the cached block list
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}


from types import SimpleNamespace
from nextword.cards.pipeline import extract_fields, collect_cards


def _tool_use_message(fields):
    block = SimpleNamespace(type="tool_use", name="card", input=fields)
    return SimpleNamespace(content=[block])


def test_extract_fields_returns_tool_input():
    msg = _tool_use_message({"Word": "extra", "Translation": "дополнительный"})
    assert extract_fields(msg.content) == {"Word": "extra", "Translation": "дополнительный"}


def test_extract_fields_raises_without_tool_use():
    text_block = SimpleNamespace(type="text", text="oops")
    try:
        extract_fields([text_block])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_collect_cards_maps_ids_to_words_and_reports_failures():
    words = ["extra", "fact"]
    id_to_word = {f"req-{i}": w for i, w in enumerate(words)}
    responses = [
        SimpleNamespace(
            custom_id="req-0",
            result=SimpleNamespace(
                type="succeeded",
                message=_tool_use_message({"Word": "extra"}),
            ),
        ),
        SimpleNamespace(
            custom_id="req-1",
            result=SimpleNamespace(type="errored", message=None),
        ),
    ]
    cards, failed = collect_cards(responses, id_to_word)
    assert cards == [{"word": "extra", "fields": {"Word": "extra"}}]
    assert failed == ["fact"]


from nextword.cards.pipeline import load_state, save_state


def test_load_state_returns_none_when_missing(tmp_path):
    assert load_state(tmp_path / "nope.json") is None


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "state" / "cards_batch.json"
    state = {"batch_id": "msgbatch_1", "words": ["extra"], "status": "in_progress"}
    save_state(path, state)
    assert load_state(path) == state
