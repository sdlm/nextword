from pathlib import Path
from unittest.mock import MagicMock, patch

from nextword import cli
from nextword.cards import pipeline
from nextword.cli import build_parser


def test_no_command_parses_to_none():
    args = build_parser().parse_args([])
    assert args.command is None


def test_cards_generate_parses_parallel_by_default():
    args = build_parser().parse_args(["cards", "generate"])
    assert args.command == "cards"
    assert args.cards_command == "generate"
    assert args.batch is False


def test_cards_generate_batch_flag():
    args = build_parser().parse_args(["cards", "generate", "--batch"])
    assert args.cards_command == "generate"
    assert args.batch is True


def test_cards_preview_parses_word():
    args = build_parser().parse_args(["cards", "preview", "undertake"])
    assert args.command == "cards"
    assert args.cards_command == "preview"
    assert args.word == "undertake"
    assert not hasattr(args, "batch")


def test_mochi_upload_parses():
    args = build_parser().parse_args(["mochi", "upload"])
    assert args.command == "mochi"
    assert args.mochi_command == "upload"


def test_mochi_preview_parses_word():
    args = build_parser().parse_args(["mochi", "preview", "undertake"])
    assert args.command == "mochi"
    assert args.mochi_command == "preview"
    assert args.word == "undertake"


def _make_card(word: str) -> dict:
    return {"word": word, "fields": {"Word": word}}


def _write_csv(path: Path, words: list[str]) -> None:
    pipeline.write_words(path, words)


def test_run_pipeline_generates_then_uploads(tmp_path):
    csv_path = tmp_path / "export.csv"
    _write_csv(csv_path, ["x"])
    with patch("nextword.cards.pipeline.generate", return_value=([_make_card("x")], [])) as gen, \
         patch("nextword.mochi.upload.upload", return_value=(1, 0, [])) as up, \
         patch("nextword.cards.pipeline.DEFAULT_CSV", csv_path):
        cli._run_pipeline()
    gen.assert_called_once()
    up.assert_called_once()


def test_run_pipeline_skips_upload_when_no_cards():
    with patch("nextword.cards.pipeline.generate", return_value=([], ["x"])), \
         patch("nextword.mochi.upload.upload") as up:
        cli._run_pipeline()
    up.assert_not_called()


def test_run_pipeline_handles_generate_error(capsys):
    with patch("nextword.cards.pipeline.generate", side_effect=RuntimeError("boom")), \
         patch("nextword.mochi.upload.upload") as up:
        cli._run_pipeline()  # must not raise
    up.assert_not_called()
    assert "Card generation failed" in capsys.readouterr().out


def test_run_pipeline_handles_upload_error(capsys):
    with patch("nextword.cards.pipeline.generate", return_value=([{"word": "x"}], [])), \
         patch("nextword.mochi.upload.upload", side_effect=RuntimeError("boom")):
        cli._run_pipeline()  # must not raise
    assert "Mochi upload failed" in capsys.readouterr().out


def test_tui_runs_pipeline_when_signaled():
    fake_app = MagicMock()
    fake_app.run.return_value = "run_pipeline"
    with patch("nextword.app.WordListApp", return_value=fake_app), \
         patch("nextword.cli._run_pipeline") as rp:
        cli._run_tui_and_pipeline()
    rp.assert_called_once()


def test_tui_skips_pipeline_on_plain_exit():
    fake_app = MagicMock()
    fake_app.run.return_value = None
    with patch("nextword.app.WordListApp", return_value=fake_app), \
         patch("nextword.cli._run_pipeline") as rp:
        cli._run_tui_and_pipeline()
    rp.assert_not_called()


# ---------------------------------------------------------------------------
# CSV cleanup after upload
# ---------------------------------------------------------------------------


def test_run_pipeline_all_uploaded_clears_csv(tmp_path):
    """All words succeed → CSV is rewritten with header only (no words)."""
    csv_path = tmp_path / "export.csv"
    _write_csv(csv_path, ["fence", "abrupt"])
    cards = [_make_card("fence"), _make_card("abrupt")]

    with patch("nextword.cards.pipeline.generate", return_value=(cards, [])), \
         patch("nextword.mochi.upload.upload", return_value=(2, 0, [])), \
         patch("nextword.cards.pipeline.DEFAULT_CSV", csv_path):
        cli._run_pipeline()

    remaining = pipeline.read_words(csv_path)
    assert remaining == []


def test_run_pipeline_partial_failure_keeps_failed_words(tmp_path):
    """Partial failure → only failed words remain in CSV."""
    csv_path = tmp_path / "export.csv"
    _write_csv(csv_path, ["fence", "abrupt", "ponder"])
    cards = [_make_card("fence"), _make_card("abrupt"), _make_card("ponder")]

    with patch("nextword.cards.pipeline.generate", return_value=(cards, [])), \
         patch("nextword.mochi.upload.upload", return_value=(1, 0, ["abrupt", "ponder"])), \
         patch("nextword.cards.pipeline.DEFAULT_CSV", csv_path):
        cli._run_pipeline()

    remaining = pipeline.read_words(csv_path)
    assert remaining == ["abrupt", "ponder"]


def test_run_pipeline_upload_exception_does_not_touch_csv(tmp_path):
    """Upload raises an exception → CSV is NOT modified."""
    csv_path = tmp_path / "export.csv"
    _write_csv(csv_path, ["fence", "abrupt"])
    original_content = csv_path.read_text(encoding="utf-8")
    cards = [_make_card("fence"), _make_card("abrupt")]

    with patch("nextword.cards.pipeline.generate", return_value=(cards, [])), \
         patch("nextword.mochi.upload.upload", side_effect=RuntimeError("network error")), \
         patch("nextword.cards.pipeline.DEFAULT_CSV", csv_path):
        cli._run_pipeline()  # must not raise

    assert csv_path.read_text(encoding="utf-8") == original_content


def test_run_pipeline_all_failed_does_not_touch_csv(tmp_path):
    """All words fail upload (empty uploaded set) → CSV is NOT modified."""
    csv_path = tmp_path / "export.csv"
    _write_csv(csv_path, ["fence", "abrupt"])
    cards = [_make_card("fence"), _make_card("abrupt")]

    with patch("nextword.cards.pipeline.generate", return_value=(cards, [])), \
         patch("nextword.mochi.upload.upload", return_value=(0, 0, ["fence", "abrupt"])), \
         patch("nextword.cards.pipeline.DEFAULT_CSV", csv_path):
        cli._run_pipeline()

    remaining = pipeline.read_words(csv_path)
    assert remaining == ["fence", "abrupt"]


def test_run_pipeline_csv_not_exists_is_noop(tmp_path):
    """When DEFAULT_CSV does not exist, cleanup is a no-op — no exception, no file created."""
    missing_csv = tmp_path / "nonexistent.csv"
    cards = [_make_card("fence")]

    with patch("nextword.cards.pipeline.generate", return_value=(cards, [])), \
         patch("nextword.mochi.upload.upload", return_value=(1, 0, [])), \
         patch("nextword.cards.pipeline.DEFAULT_CSV", missing_csv):
        cli._run_pipeline()  # must not raise

    assert not missing_csv.exists()
