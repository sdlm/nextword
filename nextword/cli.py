# nextword/cli.py
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nextword")
    sub = parser.add_subparsers(dest="command")

    cards = sub.add_parser("cards", help="Mochi card generation")
    cards_sub = cards.add_subparsers(dest="cards_command")
    generate = cards_sub.add_parser("generate", help="Generate cards.json (parallel by default)")
    generate.add_argument(
        "--batch",
        action="store_true",
        help="Use the slower, cheaper Message Batches API instead of parallel requests",
    )
    preview = cards_sub.add_parser("preview", help="Generate one card synchronously")
    preview.add_argument("word", help="The English word to preview")

    mochi = sub.add_parser("mochi", help="Mochi card upload")
    mochi_sub = mochi.add_subparsers(dest="mochi_command")
    mochi_sub.add_parser("upload", help="Upload cards.json to Mochi")
    mochi_preview = mochi_sub.add_parser("preview", help="Dry-run: print payload for one word")
    mochi_preview.add_argument("word", help="Word to preview")

    return parser


def _run_pipeline() -> None:
    from nextword.cards import pipeline
    from nextword.mochi import upload as mochi_upload

    try:
        cards, _failed = pipeline.generate()
    except Exception as exc:  # noqa: BLE001 — top-level CLI guard, print instead of traceback
        print(f"Card generation failed: {exc}")
        return
    if not cards:
        print("No cards generated; skipping Mochi upload.")
        return
    try:
        mochi_upload.upload()
    except Exception as exc:  # noqa: BLE001 — top-level CLI guard, print instead of traceback
        print(f"Mochi upload failed: {exc}")


def _run_tui_and_pipeline() -> None:
    from nextword.app import WordListApp

    result = WordListApp().run()
    if result == "run_pipeline":
        _run_pipeline()


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "cards":
        from nextword.cards import pipeline

        if args.cards_command == "generate":
            pipeline.generate(use_batch=args.batch)
        elif args.cards_command == "preview":
            pipeline.preview(args.word)
        else:
            build_parser().parse_args(["cards", "--help"])
        return

    if args.command == "mochi":
        from nextword.mochi import upload as mochi_upload

        if args.mochi_command == "upload":
            mochi_upload.upload()
        elif args.mochi_command == "preview":
            mochi_upload.preview(args.word)
        else:
            build_parser().parse_args(["mochi", "--help"])
        return

    _run_tui_and_pipeline()


if __name__ == "__main__":
    main()
