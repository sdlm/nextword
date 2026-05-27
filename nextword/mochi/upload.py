from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from requests.exceptions import HTTPError

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_CARDS = _DATA_DIR / "cards.json"
DEFAULT_STATE = _DATA_DIR / "mochi_state.json"


def _with_retry(fn: Callable, *, attempts: int = 3, sleep: Callable[[float], None] = time.sleep) -> Any:
    """Call fn(). On HTTPError retry up to `attempts` times with 1s/2s/4s backoff.

    Raises the last HTTPError if all attempts fail.
    Backoff delay before retry i is 2 ** (i-1): 1s, 2s, 4s, ...
    """
    last_error: HTTPError
    for i in range(attempts):
        try:
            return fn()
        except HTTPError as exc:
            last_error = exc
            if i < attempts - 1:
                sleep(2 ** i)
    raise last_error


def get_field_id_map(template: dict) -> dict[str, str]:
    """Extract {display_name: field_id} from get_template() response.

    Example:
        {"Word": "name", "Definition": "C8cx6HFb", "Cloze": "9sbCiG4l", ...}
    """
    return {
        field["name"]: field["id"]
        for field in template["fields"].values()
    }


def load_state(path: Path) -> dict[str, str]:
    """Return word->card_id dict from mochi_state.json. Return {} if file missing."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, str]) -> None:
    """Write word->card_id dict to mochi_state.json (creates parent dirs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def build_fields_payload(
    card_fields: dict[str, str],
    field_id_map: dict[str, str],
) -> dict:
    """Convert card fields + name->ID map to Mochi API fields payload.

    Returns: {field_id: {"id": field_id, "value": field_value}, ...}
    """
    return {
        field_id_map[name]: {"id": field_id_map[name], "value": value}
        for name, value in card_fields.items()
        if name in field_id_map
    }
