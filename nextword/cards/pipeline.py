import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from nextword.cards.client import (
    generate_one,
    iter_results,
    make_client,
    poll_until_done,
    submit_batch,
)
from nextword.cards.prompt import build_system_blocks, build_user_message
from nextword.cards.schema import CARD_TOOL, MAX_TOKENS, MODEL

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_CSV = _DATA_DIR / "export.csv"
DEFAULT_OUT = _DATA_DIR / "cards.json"
DEFAULT_STATE = _DATA_DIR / "cards_batch.json"


def read_words(csv_path: str | Path) -> list[str]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    words: list[str] = []
    for i, row in enumerate(rows):
        if not row:
            continue
        cell = row[0].strip()
        if not cell:
            continue
        if i == 0 and cell.lower() == "word":
            continue
        words.append(cell)
    return words


def write_cards(cards: list[dict], out_path: str | Path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(cards, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_requests(
    words: list[str],
    *,
    system: list[dict] | None = None,
    tool: dict | None = None,
    model: str = MODEL,
    max_tokens: int = MAX_TOKENS,
) -> list[dict]:
    system = system or build_system_blocks()
    tool = tool or CARD_TOOL
    return [
        {
            "custom_id": f"req-{i}",
            "params": {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [
                    {"role": "user", "content": build_user_message(word)}
                ],
                "tools": [tool],
                "tool_choice": {"type": "tool", "name": tool["name"]},
            },
        }
        for i, word in enumerate(words)
    ]


def extract_fields(content: list) -> dict:
    for block in content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise ValueError("response has no tool_use block")


def collect_cards(responses, id_to_word: dict[str, str]) -> tuple[list[dict], list[str]]:
    cards: list[dict] = []
    failed: list[str] = []
    for response in responses:
        word = id_to_word.get(response.custom_id, response.custom_id)
        if response.result.type == "succeeded":
            fields = extract_fields(response.result.message.content)
            cards.append({"word": word, "fields": fields})
        else:
            failed.append(word)
    return cards, failed


def load_state(path: str | Path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(path: str | Path, state: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def generate(
    csv_path: str | Path = DEFAULT_CSV,
    out_path: str | Path = DEFAULT_OUT,
    state_path: str | Path = DEFAULT_STATE,
    *,
    client=None,
    poll_interval: int = 30,
    sleep=time.sleep,
) -> tuple[list[dict], list[str]]:
    client = client or make_client()
    state = load_state(state_path)

    if state and state.get("status") == "in_progress":
        batch_id = state["batch_id"]
        words = state["words"]
        print(f"Resuming in-flight batch {batch_id} ({len(words)} words)")
    else:
        words = read_words(csv_path)
        if not words:
            raise RuntimeError(f"No words found in {csv_path}")
        batch_id = submit_batch(client, build_requests(words))
        save_state(state_path, {
            "batch_id": batch_id,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "words": words,
            "status": "in_progress",
        })
        print(f"Submitted batch {batch_id} ({len(words)} words)")

    poll_until_done(client, batch_id, interval=poll_interval, sleep=sleep)
    id_to_word = {f"req-{i}": w for i, w in enumerate(words)}
    cards, failed = collect_cards(iter_results(client, batch_id), id_to_word)
    write_cards(cards, out_path)
    save_state(state_path, {**load_state(state_path), "status": "collected"})

    print(f"Wrote {len(cards)} cards to {out_path}")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")
    return cards, failed


def preview(word: str, *, client=None) -> dict:
    client = client or make_client()
    request = build_requests([word])[0]
    message = generate_one(client, request)
    card = {"word": word, "fields": extract_fields(message.content)}
    print(json.dumps(card, ensure_ascii=False, indent=2))
    return card
