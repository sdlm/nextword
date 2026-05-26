MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

PART_OF_SPEECH = [
    "verb",
    "noun",
    "adjective",
    "adverb",
    "preposition",
    "conjunction",
    "phrase",
]

FIELD_NAMES = [
    "Word",
    "Part of speech",
    "Definition",
    "Example",
    "Translation",
    "Collocations",
    "Synonyms & Nuance",
    "Cloze",
]

CARD_TOOL = {
    "name": "card",
    "description": "A filled-in vocabulary flashcard following the field guidelines.",
    "input_schema": {
        "type": "object",
        "properties": {
            "Word": {"type": "string"},
            "Part of speech": {"type": "string", "enum": PART_OF_SPEECH},
            "Definition": {"type": "string"},
            "Example": {"type": "string"},
            "Translation": {"type": "string"},
            "Collocations": {"type": "string"},
            "Synonyms & Nuance": {"type": "string"},
            "Cloze": {"type": "string"},
        },
        "required": [name for name in FIELD_NAMES if name != "Synonyms & Nuance"],
    },
}
