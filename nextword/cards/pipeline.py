import csv
import json
from pathlib import Path

from nextword.cards.prompt import build_system_blocks, build_user_message
from nextword.cards.schema import CARD_TOOL, MAX_TOKENS, MODEL


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
