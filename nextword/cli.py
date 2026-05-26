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
