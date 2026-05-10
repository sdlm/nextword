# Формат данных

Локальная база слов хранится в `data/` как JSON-файлы — по одному на CEFR-уровень:

```
data/
├── a2.json
├── b1.json
├── b2.json
└── c1.json
```

## Схема записи

Каждый файл — массив объектов. Одна запись = одно слово:

| Поле | Тип | Описание |
|---|---|---|
| `word` | string | Слово или фраза |
| `part_of_speech` | string | Часть речи: `verb`, `noun`, `adjective`, `adverb`, `preposition`, `conjunction`, `phrase` |
| `level` | string | CEFR-уровень: `A2`, `B1`, `B2`, `C1` |
| `sublevel` | string | Подуровень: `beginner`, `intermediate`, `advance` |
| `definition` | string | Определение на английском |
| `example` | string | Предложение-пример на английском |
| `translation` | string | Перевод на русский |
| `collocations` | string | Устойчивые сочетания на английском |
| `synonyms_nuance` | string | Синонимы + чем отличаются (на английском) |
| `cloze` | string | Предложение с пропуском `[...]` |

## Пример записи

```json
{
  "word": "undertake",
  "part_of_speech": "verb",
  "level": "B2",
  "sublevel": "intermediate",
  "definition": "to commit yourself to do something; to take on a task or responsibility",
  "example": "The company undertook a major restructuring of its operations.",
  "translation": "предпринимать, браться за",
  "collocations": "undertake a task / project / responsibility / journey / review",
  "synonyms_nuance": "*take on* — less formal · *embark on* — emphasis on starting something large · *assume* — for duties and roles",
  "cloze": "The company [...] a major restructuring of its operations."
}
```

## Маппинг на шаблон Mochi

При загрузке в Mochi поля маппятся на шаблон `Custom template`:

| JSON-поле | Поле шаблона |
|---|---|
| `word` | Word |
| `part_of_speech` | Part of speech |
| `definition` | Definition |
| `example` | Example |
| `translation` | Translation |
| `collocations` | Collocations |
| `synonyms_nuance` | Synonyms & Nuance |
| `cloze` | Cloze |

Поля `level` и `sublevel` определяют целевую колоду (см. `docs/decks.md`).
