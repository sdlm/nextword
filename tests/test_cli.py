from unittest.mock import MagicMock, patch

from nextword import cli
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


def test_run_pipeline_generates_then_uploads():
    with patch("nextword.cards.pipeline.generate", return_value=([{"word": "x"}], [])) as gen, \
         patch("nextword.mochi.upload.upload") as up:
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
