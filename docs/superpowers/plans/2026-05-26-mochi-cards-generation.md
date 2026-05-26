# Mochi Card Generation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pipeline that reads English words from `data/export.csv`, generates 8 card fields per word via the Anthropic Message Batches API, and writes `data/cards.json`.

**Architecture:** New `nextword/cards/` subpackage with four focused modules: `schema` (tool/JSON schema + config constants), `prompt` (system prompt built from the docs verbatim, with prompt caching), `client` (thin Anthropic SDK wrapper), `pipeline` (pure orchestration + state file). One blocking CLI command `cards generate` (submit → poll → write, with crash-recovery resume) plus a sync `cards preview <word>` for prompt debugging.

**Tech Stack:** Python 3.11+, `anthropic` SDK 0.100.x (Message Batches API, tool-use structured output, prompt caching), `python-dotenv`, `pytest`. Both runtime deps already in `pyproject.toml`.

**Reference docs (read before starting):**
- Spec: `docs/superpowers/specs/2026-05-26-mochi-cards-generation-design.md`
- Field rules: `docs/field-guidelines.md`
- Card template (field names): `docs/template.md`

**Conventions in this repo:**
- Tests use `pytest` with `tmp_path` fixtures; functions take optional path/client params so they're testable without real I/O.
- Conventional commit messages (`feat:`, `fix:`, `docs:`).
- Run a single test: `.venv/bin/pytest tests/test_x.py::test_name -v`
- Run all tests: `.venv/bin/pytest -q`

---

## File Structure

- Create: `nextword/cards/__init__.py` — empty package marker
- Create: `nextword/cards/schema.py` — `CARD_TOOL`, `FIELD_NAMES`, `PART_OF_SPEECH`, `MODEL`, `MAX_TOKENS`
- Create: `nextword/cards/prompt.py` — `build_system_blocks()`, `build_user_message(word)`
- Create: `nextword/cards/client.py` — `make_client()`, `submit_batch()`, `poll_until_done()`, `iter_results()`, `generate_one()`
- Create: `nextword/cards/pipeline.py` — `read_words()`, `build_requests()`, `extract_fields()`, `collect_cards()`, `write_cards()`, `load_state()`, `save_state()`, `generate()`, `preview()`
- Modify: `nextword/cli.py` — add `build_parser()` + route `cards generate` / `cards preview`
- Test: `tests/test_cards_schema.py`, `tests/test_cards_prompt.py`, `tests/test_cards_pipeline.py`, `tests/test_cards_client.py`, `tests/test_cli.py`

Output artifacts (gitignored, created at runtime): `data/cards.json`, `data/cards_batch.json`.

---

### Task 1: Package + schema constants

**Files:**
- Create: `nextword/cards/__init__.py`
- Create: `nextword/cards/schema.py`
- Test: `tests/test_cards_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cards_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nextword.cards'`

- [ ] **Step 3: Create the package marker and schema module**

```python
# nextword/cards/__init__.py
```

(empty file)

```python
# nextword/cards/schema.py
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

PART_OF_SPEECH = [
    "verb",
    "noun",
    "adjective",
    "adverb",
    "preposition",
    "conjunction",
    "phrase",
]

FIELD_NAMES = [
    "Word",
    "Part of speech",
    "Definition",
    "Example",
    "Translation",
    "Collocations",
    "Synonyms & Nuance",
    "Cloze",
]

CARD_TOOL = {
    "name": "card",
    "description": "A filled-in vocabulary flashcard following the field guidelines.",
    "input_schema": {
        "type": "object",
        "properties": {
            "Word": {"type": "string"},
            "Part of speech": {"type": "string", "enum": PART_OF_SPEECH},
            "Definition": {"type": "string"},
            "Example": {"type": "string"},
            "Translation": {"type": "string"},
            "Collocations": {"type": "string"},
            "Synonyms & Nuance": {"type": "string"},
            "Cloze": {"type": "string"},
        },
        "required": [name for name in FIELD_NAMES if name != "Synonyms & Nuance"],
    },
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_schema.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add nextword/cards/__init__.py nextword/cards/schema.py tests/test_cards_schema.py
git commit -m "feat: add card tool schema and config constants"
```

---

### Task 2: Prompt builder

The system prompt embeds `docs/field-guidelines.md` and `docs/template.md` verbatim (single source of truth) in one big text block tagged with `cache_control` for prompt caching. The user message is just the word.

**Files:**
- Create: `nextword/cards/prompt.py`
- Test: `tests/test_cards_prompt.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cards_prompt.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_prompt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nextword.cards.prompt'`

- [ ] **Step 3: Implement the prompt builder**

```python
# nextword/cards/prompt.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_prompt.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add nextword/cards/prompt.py tests/test_cards_prompt.py
git commit -m "feat: build cached system prompt from field docs"
```

---

### Task 3: CSV reading and JSON writing

**Files:**
- Create: `nextword/cards/pipeline.py` (first functions)
- Test: `tests/test_cards_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cards_pipeline.py
import json
from nextword.cards.pipeline import read_words, write_cards


def test_read_words_skips_header_and_blanks(tmp_path):
    csv_file = tmp_path / "export.csv"
    csv_file.write_text("word\nextra\nfact\n\nfactor\n", encoding="utf-8")
    assert read_words(csv_file) == ["extra", "fact", "factor"]


def test_read_words_keeps_first_data_row_when_not_header(tmp_path):
    csv_file = tmp_path / "export.csv"
    csv_file.write_text("extra\nfact\n", encoding="utf-8")
    assert read_words(csv_file) == ["extra", "fact"]


def test_write_cards_writes_utf8_json(tmp_path):
    out = tmp_path / "nested" / "cards.json"
    cards = [{"word": "extra", "fields": {"Translation": "дополнительный"}}]
    write_cards(cards, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == cards
    # Russian must not be escaped
    assert "дополнительный" in out.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -v`
Expected: FAIL with `ImportError: cannot import name 'read_words'`

- [ ] **Step 3: Implement `read_words` and `write_cards`**

```python
# nextword/cards/pipeline.py
import csv
import json
from pathlib import Path


def read_words(csv_path: str | Path) -> list[str]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    words: list[str] = []
    for i, row in enumerate(rows):
        if not row:
            continue
        cell = row[0].strip()
        if not cell:
            continue
        if i == 0 and cell.lower() == "word":
            continue
        words.append(cell)
    return words


def write_cards(cards: list[dict], out_path: str | Path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(cards, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add nextword/cards/pipeline.py tests/test_cards_pipeline.py
git commit -m "feat: read words from CSV and write cards JSON"
```

---

### Task 4: Build batch requests

Uses index-based `custom_id` (`req-0`, `req-1`, …) because Anthropic requires `custom_id` to match `^[a-zA-Z0-9_-]{1,64}$` and some entries may be multi-word phrases.

**Files:**
- Modify: `nextword/cards/pipeline.py`
- Test: `tests/test_cards_pipeline.py`

- [ ] **Step 1: Write the failing test (append to the file)**

```python
# tests/test_cards_pipeline.py  (append)
from nextword.cards.pipeline import build_requests
from nextword.cards.schema import CARD_TOOL, MODEL


def test_build_requests_one_per_word_with_indexed_ids():
    reqs = build_requests(["extra", "give up"])
    assert [r["custom_id"] for r in reqs] == ["req-0", "req-1"]


def test_build_request_params_shape():
    req = build_requests(["extra"])[0]
    params = req["params"]
    assert params["model"] == MODEL
    assert params["tools"] == [CARD_TOOL]
    assert params["tool_choice"] == {"type": "tool", "name": "card"}
    assert params["messages"][0]["role"] == "user"
    assert "extra" in params["messages"][0]["content"]
    # system prompt is the cached block list
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k build_request -v`
Expected: FAIL with `ImportError: cannot import name 'build_requests'`

- [ ] **Step 3: Implement `build_requests`**

Add imports at the top of `nextword/cards/pipeline.py`:

```python
from nextword.cards.prompt import build_system_blocks, build_user_message
from nextword.cards.schema import CARD_TOOL, MAX_TOKENS, MODEL
```

Add the function:

```python
def build_requests(
    words: list[str],
    *,
    system: list[dict] | None = None,
    tool: dict | None = None,
    model: str = MODEL,
    max_tokens: int = MAX_TOKENS,
) -> list[dict]:
    system = system or build_system_blocks()
    tool = tool or CARD_TOOL
    return [
        {
            "custom_id": f"req-{i}",
            "params": {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [
                    {"role": "user", "content": build_user_message(word)}
                ],
                "tools": [tool],
                "tool_choice": {"type": "tool", "name": tool["name"]},
            },
        }
        for i, word in enumerate(words)
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k build_request -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add nextword/cards/pipeline.py tests/test_cards_pipeline.py
git commit -m "feat: build per-word batch requests with indexed custom ids"
```

---

### Task 5: Extract fields and collect cards from results

`extract_fields` pulls the `tool_use` block's input out of a message's content. `collect_cards` walks the batch results, maps each `custom_id` back to its word via the ordered words list, keeps succeeded cards, and reports failed words.

**Files:**
- Modify: `nextword/cards/pipeline.py`
- Test: `tests/test_cards_pipeline.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_cards_pipeline.py  (append)
from types import SimpleNamespace
from nextword.cards.pipeline import extract_fields, collect_cards


def _tool_use_message(fields):
    block = SimpleNamespace(type="tool_use", name="card", input=fields)
    return SimpleNamespace(content=[block])


def test_extract_fields_returns_tool_input():
    msg = _tool_use_message({"Word": "extra", "Translation": "дополнительный"})
    assert extract_fields(msg.content) == {"Word": "extra", "Translation": "дополнительный"}


def test_extract_fields_raises_without_tool_use():
    text_block = SimpleNamespace(type="text", text="oops")
    try:
        extract_fields([text_block])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_collect_cards_maps_ids_to_words_and_reports_failures():
    words = ["extra", "fact"]
    id_to_word = {f"req-{i}": w for i, w in enumerate(words)}
    responses = [
        SimpleNamespace(
            custom_id="req-0",
            result=SimpleNamespace(
                type="succeeded",
                message=_tool_use_message({"Word": "extra"}),
            ),
        ),
        SimpleNamespace(
            custom_id="req-1",
            result=SimpleNamespace(type="errored", message=None),
        ),
    ]
    cards, failed = collect_cards(responses, id_to_word)
    assert cards == [{"word": "extra", "fields": {"Word": "extra"}}]
    assert failed == ["fact"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k "extract_fields or collect_cards" -v`
Expected: FAIL with `ImportError: cannot import name 'extract_fields'`

- [ ] **Step 3: Implement `extract_fields` and `collect_cards`**

```python
# nextword/cards/pipeline.py  (append)
def extract_fields(content: list) -> dict:
    for block in content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise ValueError("response has no tool_use block")


def collect_cards(responses, id_to_word: dict[str, str]) -> tuple[list[dict], list[str]]:
    cards: list[dict] = []
    failed: list[str] = []
    for response in responses:
        word = id_to_word.get(response.custom_id, response.custom_id)
        if response.result.type == "succeeded":
            fields = extract_fields(response.result.message.content)
            cards.append({"word": word, "fields": fields})
        else:
            failed.append(word)
    return cards, failed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k "extract_fields or collect_cards" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add nextword/cards/pipeline.py tests/test_cards_pipeline.py
git commit -m "feat: extract tool-use fields and collect cards from batch results"
```

---

### Task 6: State file load/save

**Files:**
- Modify: `nextword/cards/pipeline.py`
- Test: `tests/test_cards_pipeline.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_cards_pipeline.py  (append)
from nextword.cards.pipeline import load_state, save_state


def test_load_state_returns_none_when_missing(tmp_path):
    assert load_state(tmp_path / "nope.json") is None


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "state" / "cards_batch.json"
    state = {"batch_id": "msgbatch_1", "words": ["extra"], "status": "in_progress"}
    save_state(path, state)
    assert load_state(path) == state
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k state -v`
Expected: FAIL with `ImportError: cannot import name 'load_state'`

- [ ] **Step 3: Implement `load_state` and `save_state`**

```python
# nextword/cards/pipeline.py  (append)
def load_state(path: str | Path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(path: str | Path, state: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k state -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add nextword/cards/pipeline.py tests/test_cards_pipeline.py
git commit -m "feat: persist batch state to a JSON file"
```

---

### Task 7: Anthropic client wrapper

Thin wrapper around the SDK. `poll_until_done` takes injectable `sleep` and `interval` so tests run instantly. All functions take an explicit `client` so tests pass a fake object — no network.

**Files:**
- Create: `nextword/cards/client.py`
- Test: `tests/test_cards_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cards_client.py
from types import SimpleNamespace
from nextword.cards.client import submit_batch, poll_until_done, iter_results, generate_one


class FakeBatches:
    def __init__(self, statuses):
        self._statuses = list(statuses)
        self.retrieve_calls = 0
        self.created_with = None

    def create(self, requests):
        self.created_with = requests
        return SimpleNamespace(id="msgbatch_123")

    def retrieve(self, batch_id):
        self.retrieve_calls += 1
        status = self._statuses.pop(0)
        return SimpleNamespace(processing_status=status)

    def results(self, batch_id):
        return iter([SimpleNamespace(custom_id="req-0")])


class FakeMessages:
    def __init__(self, statuses):
        self.batches = FakeBatches(statuses)
        self.created_with = None

    def create(self, **params):
        self.created_with = params
        return SimpleNamespace(content=["msg"])


def _client(statuses=("ended",)):
    return SimpleNamespace(messages=FakeMessages(statuses))


def test_submit_batch_returns_id():
    client = _client()
    bid = submit_batch(client, [{"custom_id": "req-0", "params": {}}])
    assert bid == "msgbatch_123"
    assert client.messages.batches.created_with == [{"custom_id": "req-0", "params": {}}]


def test_poll_until_done_loops_until_ended():
    client = _client(statuses=["in_progress", "in_progress", "ended"])
    calls = []
    poll_until_done(client, "msgbatch_123", interval=5, sleep=calls.append)
    assert client.messages.batches.retrieve_calls == 3
    assert calls == [5, 5]  # slept twice, not after the final "ended"


def test_iter_results_delegates():
    client = _client()
    out = list(iter_results(client, "msgbatch_123"))
    assert out[0].custom_id == "req-0"


def test_generate_one_calls_messages_create_with_params():
    client = _client()
    request = {"custom_id": "req-0", "params": {"model": "m", "max_tokens": 10}}
    msg = generate_one(client, request)
    assert msg.content == ["msg"]
    assert client.messages.created_with == {"model": "m", "max_tokens": 10}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nextword.cards.client'`

- [ ] **Step 3: Implement the client wrapper**

```python
# nextword/cards/client.py
import os
import time

from anthropic import Anthropic
from dotenv import load_dotenv


def make_client() -> Anthropic:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set (add it to .env)")
    return Anthropic()


def submit_batch(client, requests: list[dict]) -> str:
    batch = client.messages.batches.create(requests=requests)
    return batch.id


def poll_until_done(client, batch_id: str, interval: int = 30, sleep=time.sleep):
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return batch
        sleep(interval)


def iter_results(client, batch_id: str):
    return client.messages.batches.results(batch_id)


def generate_one(client, request: dict):
    return client.messages.create(**request["params"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_client.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add nextword/cards/client.py tests/test_cards_client.py
git commit -m "feat: add Anthropic batches client wrapper"
```

---

### Task 8: Orchestration — `generate()` and `preview()`

`generate()` ties everything together: resume an in-flight batch if the state file says so (crash-recovery), otherwise submit a new one; then poll, collect, write JSON, and mark the state collected. `preview()` does a single synchronous request for prompt debugging. Both accept an injectable `client` and paths so tests use a fake client and `tmp_path`.

**Files:**
- Modify: `nextword/cards/pipeline.py`
- Test: `tests/test_cards_pipeline.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_cards_pipeline.py  (append)
from nextword.cards.pipeline import generate, preview


class FakeBatchesOrch:
    def __init__(self):
        self.created = None

    def create(self, requests):
        self.created = requests
        return SimpleNamespace(id="msgbatch_xyz")

    def retrieve(self, batch_id):
        return SimpleNamespace(processing_status="ended")

    def results(self, batch_id):
        block = SimpleNamespace(type="tool_use", name="card", input={"Word": "extra"})
        return iter([
            SimpleNamespace(
                custom_id="req-0",
                result=SimpleNamespace(type="succeeded",
                                       message=SimpleNamespace(content=[block])),
            )
        ])


class FakeClientOrch:
    def __init__(self):
        self.messages = SimpleNamespace(
            batches=FakeBatchesOrch(),
            create=self._create,
        )
        self.create_params = None

    def _create(self, **params):
        self.create_params = params
        block = SimpleNamespace(type="tool_use", name="card", input={"Word": "extra"})
        return SimpleNamespace(content=[block])


def test_generate_fresh_submit_writes_cards_and_state(tmp_path):
    csv_file = tmp_path / "export.csv"
    csv_file.write_text("word\nextra\n", encoding="utf-8")
    out = tmp_path / "cards.json"
    state = tmp_path / "cards_batch.json"
    client = FakeClientOrch()

    cards, failed = generate(
        csv_path=csv_file, out_path=out, state_path=state,
        client=client, poll_interval=0, sleep=lambda _: None,
    )

    assert cards == [{"word": "extra", "fields": {"Word": "extra"}}]
    assert failed == []
    assert json.loads(out.read_text(encoding="utf-8")) == cards
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["batch_id"] == "msgbatch_xyz"
    assert saved["status"] == "collected"


def test_generate_resumes_in_flight_batch_without_resubmitting(tmp_path):
    csv_file = tmp_path / "export.csv"
    csv_file.write_text("word\nextra\n", encoding="utf-8")
    out = tmp_path / "cards.json"
    state = tmp_path / "cards_batch.json"
    state.write_text(json.dumps({
        "batch_id": "msgbatch_existing",
        "words": ["extra"],
        "status": "in_progress",
    }), encoding="utf-8")
    client = FakeClientOrch()

    cards, failed = generate(
        csv_path=csv_file, out_path=out, state_path=state,
        client=client, poll_interval=0, sleep=lambda _: None,
    )

    assert client.messages.batches.created is None  # did NOT submit a new batch
    assert cards == [{"word": "extra", "fields": {"Word": "extra"}}]


def test_preview_returns_single_card(capsys, tmp_path):
    client = FakeClientOrch()
    card = preview("extra", client=client)
    assert card == {"word": "extra", "fields": {"Word": "extra"}}
    assert "extra" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k "generate or preview" -v`
Expected: FAIL with `ImportError: cannot import name 'generate'`

- [ ] **Step 3: Implement `generate` and `preview`**

Add imports at the top of `nextword/cards/pipeline.py`:

```python
from datetime import datetime, timezone

from nextword.cards.client import (
    generate_one,
    iter_results,
    make_client,
    poll_until_done,
    submit_batch,
)
```

Add path defaults (below the existing imports):

```python
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_CSV = _DATA_DIR / "export.csv"
DEFAULT_OUT = _DATA_DIR / "cards.json"
DEFAULT_STATE = _DATA_DIR / "cards_batch.json"
```

Add the orchestration functions:

```python
def generate(
    csv_path: str | Path = DEFAULT_CSV,
    out_path: str | Path = DEFAULT_OUT,
    state_path: str | Path = DEFAULT_STATE,
    *,
    client=None,
    poll_interval: int = 30,
    sleep=time.sleep,
) -> tuple[list[dict], list[str]]:
    client = client or make_client()
    state = load_state(state_path)

    if state and state.get("status") == "in_progress":
        batch_id = state["batch_id"]
        words = state["words"]
        print(f"Resuming in-flight batch {batch_id} ({len(words)} words)")
    else:
        words = read_words(csv_path)
        if not words:
            raise RuntimeError(f"No words found in {csv_path}")
        batch_id = submit_batch(client, build_requests(words))
        save_state(state_path, {
            "batch_id": batch_id,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "words": words,
            "status": "in_progress",
        })
        print(f"Submitted batch {batch_id} ({len(words)} words)")

    poll_until_done(client, batch_id, interval=poll_interval, sleep=sleep)
    id_to_word = {f"req-{i}": w for i, w in enumerate(words)}
    cards, failed = collect_cards(iter_results(client, batch_id), id_to_word)
    write_cards(cards, out_path)
    save_state(state_path, {**load_state(state_path), "status": "collected"})

    print(f"Wrote {len(cards)} cards to {out_path}")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")
    return cards, failed


def preview(word: str, *, client=None) -> dict:
    client = client or make_client()
    request = build_requests([word])[0]
    message = generate_one(client, request)
    card = {"word": word, "fields": extract_fields(message.content)}
    print(json.dumps(card, ensure_ascii=False, indent=2))
    return card
```

Add `import time` to the top imports of `nextword/cards/pipeline.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -k "generate or preview" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the whole pipeline test file**

Run: `.venv/bin/pytest tests/test_cards_pipeline.py -v`
Expected: PASS (all tasks 3–8 tests green)

- [ ] **Step 6: Commit**

```bash
git add nextword/cards/pipeline.py tests/test_cards_pipeline.py
git commit -m "feat: orchestrate batch generate with resume and sync preview"
```

---

### Task 9: CLI subcommands

Keep `nextword` (no args) launching the TUI. Add `nextword cards generate` and `nextword cards preview <word>`. The parser is factored into `build_parser()` so it can be unit-tested without side effects.

**Files:**
- Modify: `nextword/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from nextword.cli import build_parser


def test_no_command_parses_to_none():
    args = build_parser().parse_args([])
    assert args.command is None


def test_cards_generate_parses():
    args = build_parser().parse_args(["cards", "generate"])
    assert args.command == "cards"
    assert args.cards_command == "generate"


def test_cards_preview_parses_word():
    args = build_parser().parse_args(["cards", "preview", "undertake"])
    assert args.command == "cards"
    assert args.cards_command == "preview"
    assert args.word == "undertake"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cli.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_parser'`

- [ ] **Step 3: Rewrite `nextword/cli.py`**

```python
# nextword/cli.py
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nextword")
    sub = parser.add_subparsers(dest="command")

    cards = sub.add_parser("cards", help="Mochi card generation")
    cards_sub = cards.add_subparsers(dest="cards_command")
    cards_sub.add_parser("generate", help="Generate cards.json via the Batches API")
    preview = cards_sub.add_parser("preview", help="Generate one card synchronously")
    preview.add_argument("word", help="The English word to preview")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "cards":
        from nextword.cards import pipeline

        if args.cards_command == "generate":
            pipeline.generate()
        elif args.cards_command == "preview":
            pipeline.preview(args.word)
        else:
            build_parser().parse_args(["cards", "--help"])
        return

    from nextword.app import WordListApp

    WordListApp().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cli.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Verify the TUI entrypoint still imports cleanly**

Run: `.venv/bin/python -c "from nextword.cli import build_parser, main; print('ok')"`
Expected: prints `ok`

- [ ] **Step 6: Commit**

```bash
git add nextword/cli.py tests/test_cli.py
git commit -m "feat: route cards generate/preview subcommands in CLI"
```

---

### Task 10: Ignore runtime artifacts + full suite

**Files:**
- Modify/Create: `.gitignore`

- [ ] **Step 1: Add runtime artifacts to `.gitignore`**

Append these lines to `.gitignore` (create the file if it does not exist):

```
data/cards.json
data/cards_batch.json
```

- [ ] **Step 2: Run the entire test suite**

Run: `.venv/bin/pytest -q`
Expected: PASS — all tests across `test_db.py`, `test_cards_schema.py`, `test_cards_prompt.py`, `test_cards_pipeline.py`, `test_cards_client.py`, `test_cli.py`

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore generated card artifacts"
```

---

## Manual Verification (after all tasks)

These require a real `ANTHROPIC_API_KEY` in `.env` and make real (billed) API calls.

1. **Preview one word (fast, sync):**
   `.venv/bin/python -m nextword.cli cards preview undertake`
   Expect: a JSON card printed to stdout with all 8 fields; `Translation` in Russian; `**undertake**` bolded in `Example`/`Collocations`; exactly one `...` in `Cloze`. Iterate on `docs/field-guidelines.md` wording if output is off — the prompt reads it at runtime.

2. **Full batch run:**
   `.venv/bin/python -m nextword.cli cards generate`
   Expect: prints `Submitted batch …`, blocks while polling, then `Wrote N cards to …/data/cards.json`. Inspect `data/cards.json`.

3. **Crash-recovery:** interrupt step 2 during polling (Ctrl-C), then re-run `cards generate`. Expect: `Resuming in-flight batch …` (no new submission).

---

## Self-Review Notes

- **Spec coverage:** CSV→JSON pipeline (Tasks 3–8), Batches API submit/poll/collect (Tasks 7–8), structured tool-use output (Task 1), prompt caching from docs verbatim (Task 2), JSON keys = template field names (Tasks 1/5, `FIELD_NAMES`), no content validation (schema-only — Task 1), one blocking command + crash-recovery (Task 8), `preview` sync helper (Task 8), partial-failure reporting (Task 5/8), API key from `.env` (Task 7). All covered.
- **Type consistency:** `build_requests` emits `custom_id="req-{i}"`; `generate` rebuilds the identical `{f"req-{i}": w}` mapping for `collect_cards`. `extract_fields` consumes `message.content`; `collect_cards` passes `response.result.message.content`. `poll_until_done(interval=, sleep=)` signature matches all call sites.
- **No placeholders:** every code step contains complete code; every run step has an exact command and expected result.
