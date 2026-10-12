import argparse
import sys

# aiodns requires the SelectorEventLoop on Windows
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .spotify import is_spotify_link
from .core import process_spotify_link, download_track, sync_downloads_db_from_library


def _positive_limit(value: str) -> int:
    limit = int(value)
    if limit < 1:
        raise argparse.ArgumentTypeError("Result limit must be positive")
    return limit


def _prompt_for_candidate(query, candidates, source_track=None):
    from .search import format_track_candidate

    print(f"\nSearch results for: {query}")
    for index, candidate in enumerate(candidates):
        print(format_track_candidate(candidate, index))
    while True:
        try:
            response = (
                input(f"Choose [1-{len(candidates)}], s=skip, q=quit: ").strip().lower()
            )
        except EOFError:
            return None
        if response == "s":
            return None
        if response == "q":
            raise KeyboardInterrupt
        if response.isdigit() and 1 <= int(response) <= len(candidates):
            return int(response) - 1
        print("Enter a result number, s, or q.")


def main():
    parser = argparse.ArgumentParser(
        description="Download music tracks from Deezer using Streamrip."
    )
    parser.add_argument(
        "input", nargs="?", help="Search query (artist and track name) or Spotify link"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print detailed output"
    )
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    parser.add_argument(
        "--setup", action="store_true", help="Run first-time setup wizard"
    )
    parser.add_argument(
        "--sync-db",
        nargs="?",
        const="",
        metavar="PATH",
        help="Sync downloads DB from configured downloads folder, or from PATH if provided.",
    )
    parser.add_argument(
        "--set-arl",
        nargs="?",
        const="",
        default=None,
        help="Update the Deezer ARL. Prompts interactively if no value provided.",
    )

    parser.add_argument(
        "-c",
        "--config",
        help="Use an explicit streamrip config for search/download commands; mdl session overrides still apply.",
    )
    matching = parser.add_mutually_exclusive_group()
    matching.add_argument(
        "--select", action="store_true", help="Choose a Deezer match interactively."
    )
    matching.add_argument(
        "--first-result",
        action="store_true",
        help="Download the first match without selection (default).",
    )
    matching.add_argument(
        "--search", action="store_true", help="List Deezer matches without downloading."
    )
    parser.add_argument(
        "--result-limit",
        type=_positive_limit,
        default=10,
        help="Maximum search matches to show (default: 10).",
    )
    args = parser.parse_args()
    if (args.select or args.search) and not args.input:
        parser.error("--select and --search require input")
    if args.config and (
        args.setup
        or args.set_arl is not None
        or args.sync_db is not None
        or args.gui
        or not args.input
    ):
        parser.error("--config applies only to search/download commands")
    selector = _prompt_for_candidate if args.select and sys.stdin.isatty() else None

    if args.setup:
        from .config import run_setup_wizard

        run_setup_wizard()
    elif args.set_arl is not None:
        # Skip ensure_mdl_config_complete: set-arl may be run precisely to fix
        # a credential problem that auto-repair can't resolve.
        from .config import set_arl

        set_arl(args.set_arl or None, verbose=args.verbose)
        return
    elif args.sync_db is not None:
        from .config import load_config, ensure_mdl_config_complete

        if not load_config():
            print("No config found. Run 'mdl --setup' to configure.")
            sys.exit(1)
        ensure_mdl_config_complete()
        sync_downloads_db_from_library(
            library_path=(args.sync_db or None),
            verbose=args.verbose,
        )
    elif args.gui:
        main_gui()
    elif args.input:
        # Check if config exists before attempting a download
        from .config import load_config, ensure_mdl_config_complete

        if not load_config():
            print("No config found. Run 'mdl --setup' to configure.")
            sys.exit(1)
        ensure_mdl_config_complete()

        if args.search:
            import asyncio
            from .search import search_track_candidates
            from .search import format_track_candidate

            for index, candidate in enumerate(
                asyncio.run(
                    search_track_candidates(
                        args.input,
                        config_path=args.config,
                        result_limit=args.result_limit,
                    )
                )
            ):
                print(format_track_candidate(candidate, index))
        elif is_spotify_link(args.input):
            # Handle Spotify link
            import asyncio

            try:
                asyncio.run(
                    process_spotify_link(
                        args.input,
                        args.config,
                        args.verbose,
                        selection_callback=selector,
                        result_limit=args.result_limit,
                    )
                )
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
        else:
            # Handle regular search string
            import asyncio

            try:
                asyncio.run(
                    download_track(
                        args.input,
                        args.config,
                        args.verbose,
                        selection_callback=selector,
                        result_limit=args.result_limit,
                    )
                )
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
    else:
        # No input and no flags — check if config exists
        from .config import load_config, ensure_mdl_config_complete

        if not load_config():
            print("No config found. Run 'mdl --setup' to get started.")
            sys.exit(1)
        ensure_mdl_config_complete()
        parser.print_help()


def main_gui():
    from .gui import launch_gui

    launch_gui()


if __name__ == "__main__":
    main()
