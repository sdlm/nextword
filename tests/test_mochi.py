import pytest
from nextword.mochi.client import make_client


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
