import sqlite3
import pytest
from nextword.db import get_words


@pytest.fixture
def db_path(tmp_path):
    db = tmp_path / "test_words.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE words (
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL,
            part_of_speech TEXT,
            level TEXT,
            sublevel TEXT,
            definition TEXT,
            example TEXT,
            translation TEXT,
            collocations TEXT,
            synonyms_nuance TEXT,
            cloze TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO words (word, level, sublevel, translation) VALUES (?, ?, ?, ?)",
        [
            ("allow",   "A2", "beginner",     "разрешать"),
            ("appear",  "A2", "beginner",     "появляться"),
            ("believe", "B1", "intermediate", "верить"),
        ],
    )
    conn.commit()
    conn.close()
    return str(db)


def test_get_words_returns_matching_level_and_sublevel(db_path):
    result = get_words("A2", "beginner", db_path=db_path)
    assert len(result) == 2
    assert result[0] == {"word": "allow", "translation": "разрешать"}
    assert result[1] == {"word": "appear", "translation": "появляться"}


def test_get_words_filters_out_other_levels(db_path):
    result = get_words("B1", "intermediate", db_path=db_path)
    assert len(result) == 1
    assert result[0]["word"] == "believe"


def test_get_words_returns_empty_for_no_match(db_path):
    result = get_words("C1", "advance", db_path=db_path)
    assert result == []
