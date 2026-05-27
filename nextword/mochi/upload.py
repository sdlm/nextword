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
    """Call fn(). On HTTPError retry with exponential backoff (2**i seconds between attempts).

    Raises the last HTTPError if all attempts fail.
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


def upload(
    cards_path: Path = DEFAULT_CARDS,
    state_path: Path = DEFAULT_STATE,
    *,
    client: Any = None,
    deck_id: str | None = None,
    template_id: str | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[int, int, list[str]]:
    """Upload all cards from cards_path to Mochi.

    - New word (not in state): create_card(content, deck_id, template_id=..., fields=...)
    - Existing word (in state): update_card(card_id, content=..., fields=...)
      NOTE: update_card receives ONLY content and fields.
    - State written to disk after EACH successful card (incremental).
    - Failed words (HTTPError after all retries) collected and returned.

    Returns: (new_count, updated_count, failed_words)
    """
    if client is None:
        from nextword.mochi.client import make_client

        client, deck_id, template_id = make_client()

    cards: list[dict] = json.loads(cards_path.read_text(encoding="utf-8"))
    state: dict[str, str] = load_state(state_path)

    template = client.templates.get_template(template_id)
    field_id_map = get_field_id_map(template)

    new_count = 0
    updated_count = 0
    failed_words: list[str] = []

    for card in cards:
        word: str = card["fields"]["Word"]
        fields_payload = build_fields_payload(card["fields"], field_id_map)
        is_update = word in state

        try:
            if is_update:
                card_id = state[word]
                _with_retry(
                    lambda cid=card_id: client.cards.update_card(
                        cid,
                        content=word,
                        fields=fields_payload,
                    ),
                    sleep=sleep,
                )
                updated_count += 1
                print(f"  updated {word}")
                save_state(state_path, state)
            else:
                # Pre-save with sentinel so state file exists before the API call.
                # This provides crash-safety: on restart the word is in state and
                # will be treated as an update (idempotent).
                state[word] = ""
                save_state(state_path, state)
                result = _with_retry(
                    lambda: client.cards.create_card(
                        word,
                        deck_id,
                        template_id=template_id,
                        fields=fields_payload,
                    ),
                    sleep=sleep,
                )
                state[word] = result["id"]
                save_state(state_path, state)
                new_count += 1
                print(f"  created {word}")
        except HTTPError:
            if not is_update:
                state.pop(word, None)
                save_state(state_path, state)
            failed_words.append(word)
            print(f"  FAILED {word}")

    print(
        f"Uploaded {new_count + updated_count} cards "
        f"({new_count} new, {updated_count} updated, {len(failed_words)} failed)"
    )
    return new_count, updated_count, failed_words
