from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_GUIDELINES_PATH = _REPO_ROOT / "docs" / "field-guidelines.md"
_TEMPLATE_PATH = _REPO_ROOT / "docs" / "template.md"

_INSTRUCTIONS = (
    "Ты заполняешь словарную карточку для одного английского слова. "
    "Вызови инструмент `card` и заполни все поля строго по гайдлайнам ниже. "
    "Язык всех полей — английский, кроме поля `Translation`, которое на русском. "
    "Следуй форматам из гайдлайнов: списки в markdown, выделение слова **жирным**, "
    "проценты частотности в Translation, ровно один пропуск `...` в Cloze. "
    "Поле `Synonyms & Nuance` оставляй пустой строкой, если значимых синонимов нет."
)


def build_system_blocks(
    guidelines_path: Path = _GUIDELINES_PATH,
    template_path: Path = _TEMPLATE_PATH,
) -> list[dict]:
    guidelines = Path(guidelines_path).read_text(encoding="utf-8")
    template = Path(template_path).read_text(encoding="utf-8")
    text = (
        f"{_INSTRUCTIONS}\n\n"
        f"# ГАЙДЛАЙНЫ ПО ПОЛЯМ\n\n{guidelines}\n\n"
        f"# ШАБЛОН КАРТОЧКИ\n\n{template}"
    )
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def build_user_message(word: str) -> str:
    return f"Word: {word}"
