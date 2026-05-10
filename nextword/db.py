import sqlite3

DB_PATH = "data/words.db"


def get_words(level: str, sublevel: str, db_path: str = DB_PATH) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT word, translation FROM words WHERE level = ? AND sublevel = ? ORDER BY word",
            (level, sublevel),
        ).fetchall()
    return [{"word": row["word"], "translation": row["translation"]} for row in rows]
