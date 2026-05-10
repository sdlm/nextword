import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "words.db"


def get_words(level: str, sublevel: str, db_path: str | Path = DB_PATH) -> list[dict]:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT word, translation FROM words WHERE level = ? AND sublevel = ? ORDER BY word",
            (level, sublevel),
        ).fetchall()
    return [{"word": row["word"], "translation": row["translation"]} for row in rows]
