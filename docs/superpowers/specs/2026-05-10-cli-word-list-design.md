# CLI Word List Export — Design Spec

**Date:** 2026-05-10  
**Status:** Approved

## Overview

Terminal UI (TUI) утилита на Python для просмотра слов из `data/words.db` с возможностью отметить нужные и сохранить их в CSV. Реализована на `textual`.

## User Flow

1. Запуск: `python cli.py`
2. **LevelScreen** — выбор CEFR-уровня: A2, B1, B2, C1 (стрелки + Enter)
3. **SublevelScreen** — выбор подуровня: beginner, intermediate, advance (стрелки + Enter)
4. **WordListScreen** — полноэкранный скроллируемый список слов с чекбоксами
5. Нажатие `S` — сохранить отмеченные слова в `data/export.csv` и выйти

## Screens

### LevelScreen
- Список из 4 пунктов: A2, B1, B2, C1
- Навигация стрелками, выбор Enter
- Переход на SublevelScreen через `app.push_screen`

### SublevelScreen
- Список из 3 пунктов: beginner, intermediate, advance
- Навигация стрелками, выбор Enter
- Переход на WordListScreen через `app.push_screen`

### WordListScreen
- Textual `ListView` со строками вида: `[x]  allow          разрешать, позволять`
- Показывает только то, что помещается на экран; прокрутка стрелками
- Заголовок: `NextWord Export — Selected: N`
- Footer с подсказками: `↑↓ navigate  Space toggle  S save  Q quit`

## Keyboard Bindings

| Клавиша | Действие |
|---|---|
| `↑` / `↓` | Перемещение по списку |
| `Space` / `Enter` / `Tab` | Отметить / снять чекбокс |
| `S` | Сохранить в CSV и выйти |
| `Q` / `Esc` | Выйти без сохранения |

## File Structure

```
nextword/
├── cli.py     # точка входа, запуск app
├── db.py      # SQLite-запросы (изолированы от UI)
└── app.py     # Textual App + LevelScreen, SublevelScreen, WordListScreen
```

## Data

- **Источник:** `data/words.db`, таблица `words`
- **Фильтрация:** по полям `level` и `sublevel`
- **Отображение:** поля `word` и `translation`
- **Экспорт:** `data/export.csv`, одна колонка `word`, перезаписывается при каждом сохранении

## Dependencies

- `textual` — добавить в `pyproject.toml`
