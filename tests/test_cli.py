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
