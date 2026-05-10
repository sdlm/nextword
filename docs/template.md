# Шаблон карточки

**Название:** Custom template
**Настройка:** ☑️ Show each side separately

### Поля

| # | Поле | Multi-line | Описание |
|---|---|---|---|
| 1 | `Word` | нет | Слово или фраза |
| 2 | `Part of speech` | нет | Часть речи (verb, noun, adj...) |
| 3 | `Definition` | да | Определение на английском |
| 4 | `Example` | да | Предложение с использованием слова |
| 5 | `Translation` | нет | Перевод на русский |
| 6 | `Collocations` | да | Устойчивые сочетания |
| 7 | `Synonyms & Nuance` | да | Синонимы + чем отличаются |
| 8 | `Cloze` | да | Предложение с пропуском `[...]` |

### Разметка шаблона (Template Content)

```
## << Word >>  *(<<Part of speech>>)*
---
**Definition:**
<< Definition >>

**Example:**
<< Example >>

**Перевод:**
<< Translation >>

**Collocations:**
<< Collocations >>

**Synonyms & Nuance:**
<< Synonyms & Nuance >>
---
<< Cloze >>
```

### 3 стороны карточки (отдельные SRS-интервалы)

| Сторона | Ты видишь | Что делаешь |
|---|---|---|
| **Side 1 — Recognition** | `undertake *(verb)*` | Вспоминаешь значение |
| **Side 2 — Full Info** | Definition, Example, перевод, Collocations, Synonyms | Вспоминаешь какое слово |
| **Side 3 — Recall (Cloze)** | `The company [...] a major restructuring` | Вспоминаешь слово по контексту |

---

## Пример заполненной карточки

| Поле | Значение |
|---|---|
| **Word** | undertake |
| **Part of speech** | verb |
| **Definition** | to commit yourself to do something; to take on a task or responsibility |
| **Example** | The company undertook a major restructuring of its operations. |
| **Translation** | предпринимать, браться за |
| **Collocations** | undertake a task / project / responsibility / journey / review |
| **Synonyms & Nuance** | *take on* — менее формально · *embark on* — акцент на начале масштабного · *assume* — про обязанности и роли |
| **Cloze** | The company [...] a major restructuring of its operations. |
