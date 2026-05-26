from nextword.cards.prompt import build_system_blocks, build_user_message


def test_system_blocks_single_cached_block():
    blocks = build_system_blocks()
    assert len(blocks) == 1
    assert blocks[0]["type"] == "text"
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_system_block_embeds_both_docs_verbatim():
    text = build_system_blocks()[0]["text"]
    # substring from docs/field-guidelines.md
    assert "Гайдлайны по заполнению полей" in text
    # substring from docs/template.md
    assert "Шаблон карточки" in text


def test_system_block_states_translation_is_russian():
    text = build_system_blocks()[0]["text"].lower()
    assert "translation" in text
    assert "русск" in text


def test_user_message_contains_word():
    assert "undertake" in build_user_message("undertake")
