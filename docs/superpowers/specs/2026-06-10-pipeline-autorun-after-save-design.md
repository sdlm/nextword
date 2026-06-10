# Автозапуск пайплайна после `/save`

**Дата:** 2026-06-10
**Статус:** дизайн утверждён, готов к плану

## Проблема

Сейчас в TUI клавиша `s` (`/save`) лишь пишет выбранные слова в `data/export.csv`
и выходит. Дальнейшие шаги пайплайна (`nextword cards generate`,
`nextword mochi upload`) пользователь запускает руками. Цель — чтобы после
`/save` сразу выполнялась вся цепочка: `export.csv → cards.json → Mochi`.

## Решение (spine)

TUI плохо подходит для показа `print()`-вывода долгих сетевых шагов и держит
терминал. Поэтому при подтверждении **TUI выходит** и передаёт сигнал в
`cli.main()` через `app.exit(result=...)`; пайплайн выполняется уже в обычном
терминале после `app.run()`. Сами шаги пайплайна (`cards generate`,
`mochi upload`) переиспользуются как есть — их I/O не переписываем.

## Поток в TUI (`nextword/app.py`)

1. `s` / `ы` → существующий гард «нет выбранных слов» (`notify(...)`, выход).
2. Показываем модальный экран `ConfirmScreen` с текстом
   «Сгенерировать N карточек и залить в Mochi? Enter — да, Esc — отмена».
   Управление — **Enter (подтвердить) / Esc (отмена)**, чтобы не зависеть от
   раскладки клавиатуры (в приложении уже есть кириллические дубли клавиш;
   `y`/`n` ломались бы под кириллицей).
3. `action_save` остаётся **синхронным** и использует
   `self.app.push_screen(ConfirmScreen(n), self._on_save_confirm)` —
   колбэк-форму, а не `await push_screen_wait(...)` (та требует worker-контекста
   и упала бы с `NoActiveWorker` из голого async-обработчика).
4. Колбэк `_on_save_confirm(run: bool)`:
   - **`run is True`** → пишем `data/export.csv` (как сейчас), сохраняем позицию
     (`_save_position`), `app.exit(result="run_pipeline", message="Saved N words …")`.
   - **`run is False`** → ничего не делаем, модалка закрыта, возвращаемся к списку.

### Изменение поведения (утверждено)

Отдельного «сохранить только CSV без пайплайна» больше нет. `s` всегда ведёт
к модалке: подтверждение = сохранить + запустить пайплайн; отмена = вернуться
к списку (файл не пишется). Прежний сценарий чистого экспорта в CSV убирается
сознательно.

## Поток в `cli.main()` (`nextword/cli.py`)

В ветке «нет подкоманды» (запуск TUI):

```python
from nextword.app import WordListApp

result = WordListApp().run()
if result == "run_pipeline":
    _run_pipeline()
```

```python
def _run_pipeline() -> None:
    from nextword.cards import pipeline
    from nextword.mochi import upload as mochi_upload

    try:
        cards, _failed = pipeline.generate()          # export.csv → cards.json (parallel)
    except Exception as exc:                            # noqa: BLE001 — top-level CLI guard
        print(f"Card generation failed: {exc}")
        return
    if not cards:
        print("No cards generated; skipping Mochi upload.")
        return
    try:
        mochi_upload.upload()                          # cards.json → Mochi
    except Exception as exc:                            # noqa: BLE001
        print(f"Mochi upload failed: {exc}")
```

### Решения по краевым случаям

- **Режим генерации:** `parallel` (дефолт CLI), не `--batch`.
- **Жёсткий сбой vs частичный:** `pipeline.generate()` сам собирает пофразовые
  сбои в `failed` и печатает их. Но `make_client()` / `get_template()` падают
  с трейсбеком при отсутствии API-ключа или сети. Ловим на верхнем уровне и
  печатаем чистое сообщение (`Card generation failed: …` / `Mochi upload failed: …`)
  вместо трейсбека.
- **Гейт на upload:** `upload()` вызывается только если `generate` дал ≥1 карточку.
- **Язык сообщений:** строки в коде — английские, в тон существующим
  (`"Saved N words"`, `"No words selected."`).

## Компоненты

| Компонент | Где | Что делает | Зависит от |
|---|---|---|---|
| `ConfirmScreen(ModalScreen[bool])` | `app.py` | модалка «да/нет»; Enter→`dismiss(True)`, Esc→`dismiss(False)` | Textual |
| `WordListScreen.action_save` | `app.py` | гард + `push_screen(ConfirmScreen, _on_save_confirm)` | `ConfirmScreen` |
| `WordListScreen._on_save_confirm` | `app.py` | пишет CSV + позицию + `exit(result="run_pipeline")` | существующая логика записи |
| `_run_pipeline` | `cli.py` | оркестрирует `generate → upload` с обработкой ошибок | `cards.pipeline`, `mochi.upload` |
| `main` | `cli.py` | `result = run(); if result == "run_pipeline": _run_pipeline()` | `WordListApp`, `_run_pipeline` |

## Тестирование

Тесты живут на уровне CLI/пайплайна с фейками; TUI не тестируется (как и сейчас).

- **`test_cli`:** `_run_pipeline` / диспетчеризация `main`:
  - застабить `WordListApp.run` → `"run_pipeline"`, замокать `pipeline.generate`
    (вернуть `([card], [])`) и `mochi_upload.upload`; проверить, что обе вызваны.
  - `generate` вернул `([], [...])` → `upload` **не** вызывается.
  - `run` вернул `None` (обычный выход/quit) → ни `generate`, ни `upload` не зовутся.
  - `generate` бросает исключение → печатается сообщение, `upload` не зовётся.

Модалку через Textual pilot не гоняем (вне зоны тестов проекта).

## Вне объёма (YAGNI)

- Выбор `batch`/`parallel` из TUI.
- Показ прогресса пайплайна внутри TUI.
- Возврат в TUI после завершения пайплайна.
- Ретрай/резюме всего пайплайна как единицы (резюме есть только у `--batch` внутри `generate`).
