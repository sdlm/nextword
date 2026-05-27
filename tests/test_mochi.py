import pytest
from nextword.mochi.client import make_client
from nextword.mochi.upload import get_field_id_map, load_state, save_state, build_fields_payload


def test_make_client_raises_if_api_key_missing(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    monkeypatch.delenv("MOCHI_DECK_ID", raising=False)
    monkeypatch.delenv("MOCHI_TEMPLATE_ID", raising=False)
    with pytest.raises(RuntimeError, match="MOCHI_API_KEY"):
        make_client()


def test_make_client_raises_if_deck_id_missing(monkeypatch):
    monkeypatch.setenv("MOCHI_API_KEY", "key")
    monkeypatch.delenv("MOCHI_DECK_ID", raising=False)
    monkeypatch.setenv("MOCHI_TEMPLATE_ID", "tmpl")
    with pytest.raises(RuntimeError, match="MOCHI_DECK_ID"):
        make_client()


def test_make_client_raises_if_template_id_missing(monkeypatch):
    monkeypatch.setenv("MOCHI_API_KEY", "key")
    monkeypatch.setenv("MOCHI_DECK_ID", "deck")
    monkeypatch.delenv("MOCHI_TEMPLATE_ID", raising=False)
    with pytest.raises(RuntimeError, match="MOCHI_TEMPLATE_ID"):
        make_client()


TEMPLATE_FIXTURE = {
    "fields": {
        "name":     {"id": "name",     "name": "Word"},
        "39H26Wpc": {"id": "39H26Wpc", "name": "Part of speech"},
        "C8cx6HFb": {"id": "C8cx6HFb", "name": "Definition"},
        "9sbCiG4l": {"id": "9sbCiG4l", "name": "Cloze"},
    }
}


def test_get_field_id_map_word_maps_to_name():
    result = get_field_id_map(TEMPLATE_FIXTURE)
    assert result["Word"] == "name"


def test_get_field_id_map_all_fields_present():
    result = get_field_id_map(TEMPLATE_FIXTURE)
    assert result["Part of speech"] == "39H26Wpc"
    assert result["Definition"] == "C8cx6HFb"
    assert result["Cloze"] == "9sbCiG4l"


def test_load_state_returns_empty_dict_if_missing(tmp_path):
    assert load_state(tmp_path / "nope.json") == {}


def test_save_and_load_state_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = {"extra": "card_abc", "fact": "card_xyz"}
    save_state(path, state)
    assert load_state(path) == state


def test_build_fields_payload_structure():
    field_id_map = {"Word": "name", "Definition": "C8cx6HFb"}
    card_fields = {"Word": "undertake", "Definition": "to take on a task"}
    payload = build_fields_payload(card_fields, field_id_map)
    assert payload == {
        "name":     {"id": "name",     "value": "undertake"},
        "C8cx6HFb": {"id": "C8cx6HFb", "value": "to take on a task"},
    }
