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


from unittest.mock import MagicMock, call
from requests.exceptions import HTTPError
from nextword.mochi.upload import _with_retry


def test_retry_succeeds_on_first_try():
    fn = MagicMock(return_value="ok")
    assert _with_retry(fn) == "ok"
    fn.assert_called_once()


def test_retry_succeeds_after_two_failures():
    fn = MagicMock(side_effect=[HTTPError(), HTTPError(), "ok"])
    sleep = MagicMock()
    assert _with_retry(fn, sleep=sleep) == "ok"
    assert fn.call_count == 3
    assert sleep.call_args_list == [call(1), call(2)]


def test_retry_raises_after_all_attempts_fail():
    fn = MagicMock(side_effect=HTTPError("boom"))
    sleep = MagicMock()
    with pytest.raises(HTTPError):
        _with_retry(fn, sleep=sleep)
    assert fn.call_count == 3
    assert sleep.call_count == 2


import json
from types import SimpleNamespace
from nextword.mochi.upload import upload

CARDS_FIXTURE = [
    {"word": "extra", "fields": {
        "Word": "extra", "Part of speech": "adjective",
        "Definition": "More than usual", "Example": "Extra chairs.",
        "Translation": "дополнительный", "Collocations": "extra time",
        "Synonyms & Nuance": "additional", "Cloze": "We ordered [...] chairs.",
    }},
    {"word": "fact", "fields": {
        "Word": "fact", "Part of speech": "noun",
        "Definition": "A known truth", "Example": "That is a fact.",
        "Translation": "факт", "Collocations": "hard fact",
        "Synonyms & Nuance": "truth", "Cloze": "Base it on [...].",
    }},
]

FULL_TEMPLATE_FIXTURE = {
    "fields": {
        "name":     {"id": "name",     "name": "Word"},
        "39H26Wpc": {"id": "39H26Wpc", "name": "Part of speech"},
        "C8cx6HFb": {"id": "C8cx6HFb", "name": "Definition"},
        "fYg9Kx07": {"id": "fYg9Kx07", "name": "Example"},
        "yeAAPAUQ": {"id": "yeAAPAUQ", "name": "Translation"},
        "igIW8zAx": {"id": "igIW8zAx", "name": "Collocations"},
        "THTJKPzM": {"id": "THTJKPzM", "name": "Synonyms & Nuance"},
        "9sbCiG4l": {"id": "9sbCiG4l", "name": "Cloze"},
    }
}

def _make_mock_client(template_fixture, card_id="card_001"):
    return SimpleNamespace(
        templates=SimpleNamespace(
            get_template=MagicMock(return_value=template_fixture)
        ),
        cards=SimpleNamespace(
            create_card=MagicMock(return_value={"id": card_id}),
            update_card=MagicMock(return_value={"id": card_id}),
        ),
    )

def test_upload_creates_new_cards(tmp_path):
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps(CARDS_FIXTURE), encoding="utf-8")
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)

    new, updated, failed = upload(
        cards_file, tmp_path / "state.json",
        client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None,
    )

    assert new == 2
    assert updated == 0
    assert failed == []
    assert client.cards.create_card.call_count == 2
    assert client.cards.update_card.call_count == 0

def test_upload_content_is_word(tmp_path):
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps([CARDS_FIXTURE[0]]), encoding="utf-8")
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)

    upload(cards_file, tmp_path / "state.json",
           client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None)

    args, kwargs = client.cards.create_card.call_args
    assert args[0] == "extra"   # content = word

def test_upload_update_receives_only_content_and_fields(tmp_path):
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps([CARDS_FIXTURE[0]]), encoding="utf-8")
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"extra": "card_001"}), encoding="utf-8")
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)

    upload(cards_file, state_path,
           client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None)

    assert client.cards.update_card.call_count == 1
    assert client.cards.create_card.call_count == 0
    _, kwargs = client.cards.update_card.call_args
    assert "template_id" not in kwargs
    assert "deck_id" not in kwargs
    assert "content" in kwargs
    assert "fields" in kwargs

def test_upload_writes_state_incrementally(tmp_path):
    """State must be on disk after each card, not just at the end."""
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps(CARDS_FIXTURE), encoding="utf-8")
    state_path = tmp_path / "state.json"
    snapshots: list[dict] = []

    def capturing_create(*args, **kwargs):
        result = {"id": f"card_{args[0]}"}
        snapshots.append(json.loads(state_path.read_text()))
        return result

    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)
    client.cards.create_card = capturing_create

    upload(cards_file, state_path,
           client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None)

    assert "extra" in snapshots[0]

def test_upload_collects_failures_and_continues(tmp_path):
    from requests.exceptions import HTTPError
    cards_file = tmp_path / "cards.json"
    cards_file.write_text(json.dumps(CARDS_FIXTURE), encoding="utf-8")
    client = _make_mock_client(FULL_TEMPLATE_FIXTURE)
    client.cards.create_card = MagicMock(
        side_effect=[HTTPError(), HTTPError(), HTTPError(),
                     {"id": "card_fact"}]
    )

    new, updated, failed = upload(
        cards_file, tmp_path / "state.json",
        client=client, deck_id="deck1", template_id="tmpl1", sleep=lambda s: None,
    )

    assert "extra" in failed
    assert new == 1
