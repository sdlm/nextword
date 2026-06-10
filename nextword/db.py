import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "words.db"


def get_words(level: str, sublevel: str, db_path: str | Path = DB_PATH) -> list[dict]:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, word, translation FROM words WHERE level = ? AND sublevel = ? ORDER BY word",
            (level, sublevel),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "word": row["word"],
            "translation": row["translation"],
            "level": level,
            "sublevel": sublevel,
            "sublevel_num": i + 1,
        }
        for i, row in enumerate(rows)
    ]


def get_all_words(db_path: str | Path = DB_PATH) -> list[dict]:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, word, translation, level, sublevel FROM words ORDER BY id",
        ).fetchall()
    sublevel_counters: dict[tuple[str, str], int] = {}
    result = []
    for row in rows:
        key = (row["level"], row["sublevel"])
        sublevel_counters[key] = sublevel_counters.get(key, 0) + 1
        result.append({
            "id": row["id"],
            "word": row["word"],
            "translation": row["translation"],
            "level": row["level"],
            "sublevel": row["sublevel"],
            "sublevel_num": sublevel_counters[key],
        })
    return result
