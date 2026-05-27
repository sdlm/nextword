import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _no_dotenv_in_mochi_tests(request):
    """Prevent load_dotenv() from reading .env during mochi unit tests.

    Tests that exercise make_client() use monkeypatch to control env vars.
    Without this fixture, load_dotenv() would re-populate vars from the real
    .env file after monkeypatch.delenv(), making the tests non-hermetic.
    """
    if "test_mochi" in request.module.__name__:
        with patch("nextword.mochi.client.load_dotenv"):
            yield
    else:
        yield
