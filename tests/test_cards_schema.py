from nextword.cards.schema import (
    CARD_TOOL,
    FIELD_NAMES,
    PART_OF_SPEECH,
    MODEL,
    MAX_TOKENS,
)


def test_field_names_match_template():
    assert FIELD_NAMES == [
        "Word",
        "Part of speech",
        "Definition",
        "Example",
        "Translation",
        "Collocations",
        "Synonyms & Nuance",
        "Cloze",
    ]


def test_card_tool_has_all_fields_as_string_properties():
    props = CARD_TOOL["input_schema"]["properties"]
    assert set(props.keys()) == set(FIELD_NAMES)
    for name in FIELD_NAMES:
        assert props[name]["type"] == "string"


def test_part_of_speech_is_enum():
    assert CARD_TOOL["input_schema"]["properties"]["Part of speech"]["enum"] == PART_OF_SPEECH
    assert "verb" in PART_OF_SPEECH and "phrase" in PART_OF_SPEECH


def test_synonyms_is_optional_everything_else_required():
    required = CARD_TOOL["input_schema"]["required"]
    assert "Synonyms & Nuance" not in required
    assert set(required) == set(FIELD_NAMES) - {"Synonyms & Nuance"}


def test_tool_name_and_config():
    assert CARD_TOOL["name"] == "card"
    assert MODEL == "claude-sonnet-4-6"
    assert MAX_TOKENS >= 1024
