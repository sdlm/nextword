MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

# Max concurrent requests for the default parallel path (ThreadPoolExecutor),
# kept modest to stay under Anthropic rate limits.
CONCURRENCY = 5

PART_OF_SPEECH = [
    "verb",
    "noun",
    "adjective",
    "adverb",
    "preposition",
    "conjunction",
    "phrase",
]

# (schema_key, display_name). schema_key is the tool input_schema property key —
# Anthropic requires it to match ^[a-zA-Z0-9_.-]{1,64}$ (no spaces, no "&"), so it
# is snake_case. display_name is the template.md field name written to cards.json.
FIELDS = [
    ("word", "Word"),
    ("part_of_speech", "Part of speech"),
    ("definition", "Definition"),
    ("example", "Example"),
    ("translation", "Translation"),
    ("collocations", "Collocations"),
    ("synonyms_nuance", "Synonyms & Nuance"),
    ("cloze", "Cloze"),
]
SCHEMA_KEYS = [key for key, _ in FIELDS]
FIELD_NAMES = [name for _, name in FIELDS]
KEY_TO_FIELD = dict(FIELDS)
OPTIONAL_SCHEMA_KEY = "synonyms_nuance"


def _property(schema_key: str) -> dict:
    prop = {"type": "string", "description": KEY_TO_FIELD[schema_key]}
    if schema_key == "part_of_speech":
        prop["enum"] = PART_OF_SPEECH
    return prop


CARD_TOOL = {
    "name": "card",
    "description": "A filled-in vocabulary flashcard following the field guidelines.",
    "input_schema": {
        "type": "object",
        "properties": {key: _property(key) for key in SCHEMA_KEYS},
        "required": [key for key in SCHEMA_KEYS if key != OPTIONAL_SCHEMA_KEY],
    },
}
