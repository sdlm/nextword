import os

from dotenv import load_dotenv
from mochi.auth import Auth
from mochi.client import Mochi


def make_client() -> tuple[Mochi, str, str]:
    """Load .env, return (mochi_client, deck_id, template_id).

    Reads: MOCHI_API_KEY, MOCHI_DECK_ID, MOCHI_TEMPLATE_ID.
    Raises RuntimeError("<VAR> is not set") if any var is missing.
    """
    load_dotenv()

    api_key = os.environ.get("MOCHI_API_KEY")
    if not api_key:
        raise RuntimeError("MOCHI_API_KEY is not set")

    deck_id = os.environ.get("MOCHI_DECK_ID")
    if not deck_id:
        raise RuntimeError("MOCHI_DECK_ID is not set")

    template_id = os.environ.get("MOCHI_TEMPLATE_ID")
    if not template_id:
        raise RuntimeError("MOCHI_TEMPLATE_ID is not set")

    return Mochi(Auth.Token(api_key)), deck_id, template_id
