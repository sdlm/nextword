# nextword

CLI tool for building English vocabulary flashcards and syncing them to [Mochi](https://mochi.cards/).

**Workflow:** pick words in the TUI → generate cards with Claude AI → upload to Mochi.

## Features

- Terminal UI for browsing words by CEFR level and sublevel, with CSV export
- Card generation via Claude (parallel by default, or cheaper batch API with `--batch`)
- Incremental Mochi upload with retry and state persistence

## Setup

```bash
pip install poetry
poetry install
cp .env.example .env   # fill in your API keys
```

`.env` keys:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |
| `MOCHI_API_KEY` | Mochi account settings |
| `MOCHI_DECK_ID` | Target deck ID |
| `MOCHI_TEMPLATE_ID` | Card template ID |

## Usage

The TUI runs the whole pipeline for you:

```bash
# Launch TUI — browse words by level, select with Space
nextword
```

In the word list, press `s` to save your selection. A prompt asks
*"Generate N cards and upload to Mochi?"* — press **Enter** to confirm or
**Esc** to cancel. On confirm, nextword writes the words to `data/export.csv`,
generates cards with Claude, and uploads them to Mochi — end to end.
Press `q` to quit without running anything.

You can also run each step on its own:

```bash
# Generate cards from data/export.csv → data/cards.json
nextword cards generate

# Slower but cheaper (Anthropic Batch API)
nextword cards generate --batch

# Preview a single card without writing anything
nextword cards preview "undertake"

# Upload data/cards.json to Mochi
nextword mochi upload

# Dry-run upload for one word
nextword mochi preview "undertake"
```

## Project structure

```
nextword/
  app.py          # Textual TUI
  db.py           # SQLite access
  cards/          # Claude card generation pipeline
  mochi/          # Mochi API upload
data/
  words.db        # SQLite word database
docs/             # Field guidelines for card generation prompt
tests/
```
