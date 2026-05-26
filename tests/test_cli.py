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
