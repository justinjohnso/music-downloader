from __future__ import annotations

import argparse
import asyncio
import sys
from contextlib import contextmanager
from importlib.metadata import version

from . import legacy_cli

legacy_main = legacy_cli.main


@contextmanager
def _arguments(arguments: list[str]):
    original = sys.argv
    sys.argv = [original[0], *arguments]
    try:
        yield
    finally:
        sys.argv = original


def _common(parser: argparse.ArgumentParser, *, config: bool = False) -> None:
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Show diagnostic output.",
    )
    if config:
        parser.add_argument(
            "-c",
            "--config",
            default=argparse.SUPPRESS,
            help="Engine config path; mdl session settings still apply.",
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download music or interactively search Deezer.",
        epilog="Bare INPUT is shorthand for download INPUT. Legacy --setup, --set-arl, --sync-db and --gui remain compatibility aliases.",
    )
    parser.add_argument(
        "--version", action="version", version=version("music-downloader")
    )
    _common(parser, config=True)
    commands = parser.add_subparsers(dest="command")
    download = commands.add_parser(
        "download", help="Download a Spotify URL/URI or first Deezer query match."
    )
    _common(download, config=True)
    download.add_argument("input", nargs="?")
    download.add_argument(
        "--batch", metavar="FILE", help="UTF-8 queries or Spotify links, one per line."
    )
    download.add_argument(
        "--retries", type=int, default=0, help="Retry failed queue items 0-10 times."
    )
    download.add_argument(
        "--retry-failed",
        action="store_true",
        help="Offer failed-item retry/rematch in a terminal.",
    )
    download.add_argument(
        "--json", action="store_true", help="Write per-track JSON outcomes."
    )
    search = commands.add_parser(
        "search", help="Interactive Deezer search: Enter downloads, Escape exits."
    )
    _common(search, config=True)
    search.add_argument("query")
    search.add_argument(
        "--type",
        choices=("track", "album"),
        default="track",
        help="Media type (default: track).",
    )
    mode = search.add_mutually_exclusive_group()
    mode.add_argument(
        "-f",
        "--first",
        action="store_true",
        help="Download the first result without a menu.",
    )
    mode.add_argument(
        "-o", "--output-file", help="Export search results as JSON without downloading."
    )
    search.add_argument(
        "-n",
        "--num-results",
        type=legacy_cli._positive_limit,
        default=100,
        help="Maximum results (default: 100).",
    )
    setup = commands.add_parser(
        "setup", help="Configure credentials and download settings."
    )
    _common(setup)
    auth = commands.add_parser("auth", help="Manage credentials.")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True)
    refresh = auth_commands.add_parser(
        "refresh", help="Validate and refresh the Deezer ARL."
    )
    _common(refresh)
    refresh.add_argument(
        "arl", nargs="?", help="Prefer omitting this value for a masked prompt."
    )
    library = commands.add_parser(
        "library", help="Manage download history from library files."
    )
    library_commands = library.add_subparsers(dest="library_command", required=True)
    sync = library_commands.add_parser(
        "sync", help="Record matching Deezer IDs from existing audio tags."
    )
    _common(sync)
    sync.add_argument("path", nargs="?")
    gui = commands.add_parser("gui", help="Launch the graphical interface.")
    _common(gui)
    return parser


def _verb_index(arguments: list[str]) -> int | None:
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in ("--config", "-c"):
            index += 2
        elif argument.startswith("-c") and not argument.startswith("--"):
            index += 1
        elif argument in ("--verbose", "-v") or argument.startswith("--config="):
            index += 1
        elif argument.startswith("-"):
            return None
        else:
            return (
                index
                if argument in ("download", "search", "setup", "auth", "library", "gui")
                else None
            )
    return None


def main() -> None:
    arguments = sys.argv[1:]
    parser = _parser()
    if not arguments:
        parser.print_help()
        return
    if _verb_index(arguments) is None and any(
        flag in arguments for flag in ("--help", "-h", "--version")
    ):
        parser.parse_args(arguments)
        return
    if _verb_index(arguments) is None and arguments not in (
        ["--help"],
        ["-h"],
        ["--version"],
    ):
        if any(
            flag in arguments
            for flag in (
                "--search",
                "--select",
                "--first-result",
                "--setup",
                "--set-arl",
                "--sync-db",
                "--gui",
            )
        ):
            print(
                "Legacy action flags are deprecated; use mdl search/setup/auth refresh/library sync/gui.",
                file=sys.stderr,
            )
        with _arguments(arguments):
            legacy_main()
        return
    args = parser.parse_args(arguments)
    verbose = getattr(args, "verbose", False)
    config_path = getattr(args, "config", None)
    if config_path and args.command not in ("download", "search"):
        parser.error("--config applies only to download/search commands")
    try:
        if args.command == "download":
            if not args.input and not args.batch:
                parser.error("download requires INPUT or --batch FILE")
            if args.input and args.batch:
                parser.error("Choose INPUT or --batch, not both")
            if not 0 <= args.retries <= 10:
                parser.error("--retries must be between 0 and 10")
            if args.json and args.retry_failed:
                parser.error("JSON downloads cannot use interactive retry")
            if args.batch or args.retries or args.retry_failed or args.json:
                _download_queue(args, config_path, verbose)
                return
            forwarded = (
                (["--verbose"] if verbose else [])
                + (["--config", config_path] if config_path else [])
                + ["--", args.input]
            )
            with _arguments(forwarded):
                legacy_main()
        elif args.command == "search":
            from .streamrip_search import run_search

            code = asyncio.run(
                run_search(
                    args.query,
                    media_type=args.type,
                    config_path=config_path,
                    first=args.first,
                    output_file=args.output_file,
                    num_results=args.num_results,
                    verbose=verbose,
                )
            )
            if code:
                raise SystemExit(code)
        elif args.command == "setup":
            from .config import run_setup_wizard

            run_setup_wizard()
        elif args.command == "auth":
            from .config import set_arl

            set_arl(args.arl, verbose=verbose)
        elif args.command == "library":
            from .config import ensure_mdl_config_complete
            from .core import sync_downloads_db_from_library

            ensure_mdl_config_complete()
            sync_downloads_db_from_library(args.path, verbose=verbose)
        elif args.command == "gui":
            main_gui()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)


def _download_queue(args, config_path, verbose) -> None:
    import contextlib
    import io
    import json
    from pathlib import Path
    from .workflow import expand_input, run_queue
    from .config import load_config, ensure_mdl_config_complete

    with (
        contextlib.redirect_stdout(sys.stderr)
        if args.json
        else contextlib.nullcontext()
    ):
        if not load_config():
            raise RuntimeError("No mdl config found. Run mdl setup.")
        ensure_mdl_config_complete()
    values = (
        [
            line.strip()
            for line in Path(args.batch).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if args.batch
        else [args.input]
    )

    async def queued():
        items = []
        for value in values:
            items.extend(await expand_input(value))
        outcomes = await run_queue(
            items, config_path=config_path, retries=args.retries, verbose=verbose
        )
        if args.retry_failed and sys.stdin.isatty():
            for index, outcome in enumerate(outcomes):
                if outcome.status != "failed":
                    continue
                try:
                    action = (
                        input(f"Failed {outcome.query}: r=retry, m=rematch, s=skip: ")
                        .strip()
                        .lower()
                    )
                except EOFError:
                    break
                if action in ("r", "m"):
                    outcomes[index] = (
                        await run_queue(
                            [
                                {
                                    "query": items[index]["query"],
                                    "candidate": outcome.candidate
                                    if action == "r"
                                    else None,
                                }
                            ],
                            config_path=config_path,
                            selection_callback=legacy_cli._prompt_for_candidate
                            if action == "m"
                            else None,
                            verbose=verbose,
                        )
                    )[0]
        return outcomes

    with (
        contextlib.redirect_stdout(io.StringIO())
        if args.json
        else contextlib.nullcontext()
    ):
        outcomes = asyncio.run(queued())
    if args.json:
        print(json.dumps([outcome.to_dict() for outcome in outcomes]))
    else:
        for outcome in outcomes:
            print(f"{outcome.status}: {outcome.query} ({outcome.message})")
    if any(outcome.status == "failed" for outcome in outcomes):
        raise SystemExit(1)


def main_gui() -> None:
    from .gui import launch_gui

    launch_gui()


if __name__ == "__main__":
    main()
