# Генерация Mochi-карточек: дизайн

**Дата:** 2026-05-26
**Статус:** проект (design), утверждён к реализации

## Цель

Пайплайн: `data/export.csv` (список английских слов) → Anthropic **Message Batches API** → `data/cards.json` (на каждое слово 8 заполненных полей карточки).

Карточки заполняются по правилам `docs/field-guidelines.md`, поля соответствуют шаблону `docs/template.md`.

## Границы задачи (scope)

**В рамках этой задачи:** только до `data/cards.json`.

**Вне рамок:** импорт карточек в Mochi (через MCP `@fredrika/mcp-mochi` или `mochi-api-client`) — отдельная последующая задача. JSON-схема проектируется так, чтобы будущий импорт был тривиальным.

## Принятые решения

| Развилка | Решение |
|---|---|
| Где заканчивается задача | Только до JSON; импорт в Mochi — отдельно |
| Модель выполнения запросов | **Параллельные sync-запросы (по умолчанию)** через `ThreadPoolExecutor`; Message Batches API — опционально через флаг `--batch` |
| Источник полей | Все 8 полей генерируются через API; на входе только слово (без зависимости от `words.db`) |
| Валидация контента | Нет; только tool-схема (типы/наличие полей) |
| Структура команд | Блокирующая `cards generate` (по умолчанию параллельно → write); с `--batch` — submit → poll → write + crash-recovery через state-файл |

**Осознанные компромиссы:**
- Уровень CEFR слова потерян в `export.csv` — модель не калибрует примеры под уровень слова. Приемлемо: микс примеров (2–3 простых + 1–2 уровня C1) задан гайдлайнами, а не уровнем слова.
- Курированные переводы из `words.db` (формат `— XX%`) игнорируются — Translation генерируется заново. Принято ради простоты входа.

## Архитектура

Новый подпакет в существующем пакете `nextword/`:

```
nextword/cards/
  __init__.py
  schema.py    — tool input_schema для 8 полей; Part of speech как enum
  prompt.py    — сборка system-промта из docs/field-guidelines.md +
                 docs/template.md (читаются в рантайме), с cache_control
  client.py    — обёртка Anthropic SDK: generate_one (один sync-запрос),
                 generate_many (ThreadPoolExecutor, параллельно);
                 submit_batch, poll_status, fetch_results (для --batch)
  pipeline.py  — оркестрация: csv → запросы → (параллельно | батч) →
                 collect → cards.json; state-файл только для --batch
nextword/cli.py — добавить подкоманды cards generate / cards preview
```

Каждый модуль изолирован и тестируется отдельно:
- `schema.py` — чистые данные (структура tool-схемы)
- `prompt.py` — чистая функция (что доки вшиты вербатим + проставлен cache_control)
- `client.py` — тонкая обёртка SDK (мокается в тестах)
- `pipeline.py` — оркестрация (тестируется с замоканным client)

## Промт и структурированный вывод

**System-промт** собирается в рантайме из двух файлов — единый источник правды, правила не дублируются в коде:
- содержимое `docs/field-guidelines.md` (вербатим)
- содержимое `docs/template.md` (вербатим)
- короткая инструкция: заполнить поля для данного английского слова; язык полей — английский, кроме `Translation` (русский); следовать форматам из гайдлайнов.

Большой статичный блок промта помечается `cache_control: {"type": "ephemeral"}` — он одинаков для всех запросов (и параллельных, и батч), что даёт экономию 75–90% на кэшируемых входных токенах. (Соответствует требованию навыка `claude-api` о prompt caching.)

**User-сообщение** — только слово, напр. `Word: undertake`.

**Структурированный вывод** через tool-use:
- инструмент `card` с `input_schema` из 8 строковых свойств;
- `Part of speech` — enum: `verb`, `noun`, `adjective`, `adverb`, `preposition`, `conjunction`, `phrase`;
- `Synonyms & Nuance` — допускает пустую строку (опциональное поле);
- `tool_choice: {"type": "tool", "name": "card"}` форсит вызов инструмента.

Контентной валидации (bold, формат списков, `...` в Cloze, `— XX%`) нет — только схема типов/наличия.

**Модель:** `claude-sonnet-4-6` (константа в коде, легко заменить на Opus). Параллельность ограничена константой `CONCURRENCY` (по умолчанию 5) во избежание rate limits. `--batch` даёт −50% к цене, но медленный (минуты–часы).

## Поток данных

1. Прочитать `data/export.csv` — пропустить заголовок и пустые строки → список слов.
2. На каждое слово собрать запрос с индексным `custom_id = req-{i}` (ключ маппинга результата обратно на слово; `custom_id` Anthropic должен матчить `^[a-zA-Z0-9_.-]{1,64}$`, поэтому не само слово).

**Параллельный путь (по умолчанию):**
3. `generate_many(client, requests)` — `ThreadPoolExecutor` (max `CONCURRENCY`) шлёт все запросы параллельно, результат сразу. Каждый успешный → `tool_use.input`; упавшие собираются в `failed`.
4. Записать `data/cards.json`. State-файл не используется.

**Батч-путь (`--batch`):**
3. `submit_batch(requests)` → `batch_id`. Записать state в `data/cards_batch.json`: `{ "batch_id": ..., "submitted_at": ..., "words": [...], "status": "in_progress" }`.
4. Поллить статус батча до `ended` (с crash-recovery resume).
5. Из каждого результата извлечь `tool_use.input` по `custom_id`.
6. Записать `data/cards.json`.

Оба пути: ключи `tool_use.input` (snake_case) мапятся на display-имена `template.md`; отсутствующие поля → `""`.

### Формат `data/cards.json`

Ключи в `fields` совпадают с именами полей из `template.md` — чтобы будущий импорт в Mochi был `mochi.create(template_id, fields=card["fields"])`. В `fields` всегда присутствуют все 8 ключей: опциональное `Synonyms & Nuance`, если модель его не вернула, нормализуется в пустую строку `""`.

```json
[
  {
    "word": "undertake",
    "fields": {
      "Word": "undertake",
      "Part of speech": "verb",
      "Definition": "to commit yourself to do something; to take on a task",
      "Example": "- She **undertook** the task without hesitation.\n- ...",
      "Translation": "- предпринимать, браться за — 60%\n- ...",
      "Collocations": "- **undertake** a task / project / review\n- ...",
      "Synonyms & Nuance": "- take on — less formal\n- ...",
      "Cloze": "The company ... a major restructuring of its operations."
    }
  }
]
```

## Команды (CLI)

- **`cards generate`** (блокирующая, по умолчанию параллельно): прочитать csv → собрать запросы → `generate_many` (параллельные sync-запросы) → записать `cards.json`. State-файл не используется.
- **`cards generate --batch`**: путь через Message Batches API:
  - если в `data/cards_batch.json` есть незавершённый батч → **дожать его** (resume poll), не сабмитя новый (crash-recovery, чтобы не платить дважды);
  - иначе: собрать запросы → submit → записать state → поллить до конца → записать `cards.json`.
- **`cards preview <word>`** (sync): один запрос `messages.create` с тем же промтом и tool-схемой, печатает JSON одной карточки в stdout. Для отладки качества промта. Флаг `--batch` не принимает.

## Обработка ошибок

- **Частичные сбои (оба пути)**: упавшие запросы (исключение в параллельном пути; статус `error`/`expired` в батче) пропускаются; успешные пишутся в `cards.json`; в конце печатается список проблемных слов. Инкрементального ретрая нет: повторный `cards generate` обрабатывает **все** слова из `export.csv` заново и **перезаписывает** `cards.json` целиком. Чтобы перегенерировать только упавшие, временно сократи `export.csv`.
- **State-файл** (только `--batch`): предотвращает дубль-сабмит; повторный сбор уже завершённого батча идемпотентен (перезаписывает `cards.json`).
- **Нет `ANTHROPIC_API_KEY`**: понятная ошибка на старте. Ключ читается из `.env` (`python-dotenv` уже в зависимостях; SDK сам читает `ANTHROPIC_API_KEY`).

## Тестирование (TDD)

- `pipeline.py`: парсинг csv (пропуск заголовка/пустых), сборка запросов с корректным `custom_id`, разбор `tool_use.input` → `fields`, запись `cards.json`; параллельный `generate` (маппинг слово↔результат, частичные сбои) и батч-`generate` (`--batch`, resume) — с замоканным `client`.
- `client.py`: корректные параметры запроса (модель, tools, tool_choice, cache_control); `generate_many` сохраняет порядок и ловит исключения по запросам; разбор результатов батча — с замоканным Anthropic SDK.
- `schema.py`: схема содержит 8 полей, POS-enum, обязательные ключи, опциональность Synonyms.
- `prompt.py`: содержимое обоих доков вшито в system-промт; на большом блоке проставлен `cache_control`; user-сообщение содержит слово.

## Зависимости

`anthropic` и `python-dotenv` уже в `pyproject.toml`. Параллельность — на `concurrent.futures` из stdlib. Новых зависимостей не требуется. (`mochi-api-client` остаётся неиспользуемым до задачи импорта.)
