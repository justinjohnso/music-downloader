import argparse
import sys
import os

# aiodns requires the SelectorEventLoop on Windows
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .gui import launch_gui
from .spotify import is_spotify_link
from .core import process_spotify_link, download_track, sync_downloads_db_from_library


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

    args = parser.parse_args()

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
        launch_gui()
    elif args.input:
        # Check if config exists before attempting a download
        from .config import load_config, ensure_mdl_config_complete

        if not load_config():
            print("No config found. Run 'mdl --setup' to configure.")
            sys.exit(1)
        ensure_mdl_config_complete()

        if is_spotify_link(args.input):
            # Handle Spotify link
            import asyncio

            try:
                asyncio.run(process_spotify_link(args.input, None, args.verbose))
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
        else:
            # Handle regular search string
            import asyncio

            try:
                asyncio.run(download_track(args.input, None, args.verbose))
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
    launch_gui()


if __name__ == "__main__":
    main()
