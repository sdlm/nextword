import csv
import json
from pathlib import Path


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
