import re

from nextword.cards.schema import (
    CARD_TOOL,
    FIELD_NAMES,
    KEY_TO_FIELD,
    PART_OF_SPEECH,
    SCHEMA_KEYS,
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
    assert set(props.keys()) == set(SCHEMA_KEYS)
    for key in SCHEMA_KEYS:
        assert props[key]["type"] == "string"


def test_part_of_speech_is_enum():
    assert CARD_TOOL["input_schema"]["properties"]["part_of_speech"]["enum"] == PART_OF_SPEECH
    assert "verb" in PART_OF_SPEECH and "phrase" in PART_OF_SPEECH


def test_synonyms_is_optional_everything_else_required():
    required = CARD_TOOL["input_schema"]["required"]
    assert "synonyms_nuance" not in required
    assert set(required) == set(SCHEMA_KEYS) - {"synonyms_nuance"}


def test_key_to_field_maps_schema_keys_to_display_names():
    assert list(KEY_TO_FIELD.keys()) == SCHEMA_KEYS
    assert list(KEY_TO_FIELD.values()) == FIELD_NAMES


def test_tool_name_and_config():
    assert CARD_TOOL["name"] == "card"
    assert MODEL == "claude-sonnet-4-6"
    assert MAX_TOKENS >= 1024


def test_tool_property_keys_are_api_safe():
    # Anthropic rejects tool input_schema property keys that don't match this pattern.
    pattern = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")
    props = CARD_TOOL["input_schema"]["properties"]
    for key in props:
        assert pattern.match(key), f"invalid property key: {key!r}"
    for key in CARD_TOOL["input_schema"]["required"]:
        assert pattern.match(key), f"invalid required key: {key!r}"
