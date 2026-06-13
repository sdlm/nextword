import sqlite3
from contextlib import closing
from pathlib import Path

from wordfreq import zipf_frequency

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
            "freq": zipf_frequency(row["word"].strip().lower(), "en"),
        }
        for row in rows
    ]


def get_all_words(db_path: str | Path = DB_PATH) -> list[dict]:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, word, translation, level, sublevel FROM words ORDER BY id",
        ).fetchall()
    return [
        {
            "id": row["id"],
            "word": row["word"],
            "translation": row["translation"],
            "level": row["level"],
            "sublevel": row["sublevel"],
            "freq": zipf_frequency(row["word"].strip().lower(), "en"),
        }
        for row in rows
    ]
