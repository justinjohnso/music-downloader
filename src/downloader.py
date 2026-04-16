import argparse
import sys
from .gui import launch_gui
from .spotify import is_spotify_link
from .core import process_spotify_link, download_track

def main():
    parser = argparse.ArgumentParser(description="Download music tracks from Deezer using Streamrip.")
    parser.add_argument("input", nargs="?", help="Search query (artist and track name) or Spotify link")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print detailed output")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    parser.add_argument("--setup", action="store_true", help="Run first-time setup wizard")

    args = parser.parse_args()

    if args.setup:
        from .config import run_setup_wizard
        run_setup_wizard()
    elif args.gui:
        launch_gui()
    elif args.input:
        # Check if config exists before attempting a download
        from .config import load_config
        if not load_config():
            print("No config found. Run 'mdl --setup' to configure.")
            sys.exit(1)

        if is_spotify_link(args.input):
            # Handle Spotify link
            import asyncio
            asyncio.run(process_spotify_link(args.input, None, args.verbose))
        else:
            # Handle regular search string
            import asyncio
            asyncio.run(download_track(args.input, None, args.verbose))
    else:
        # No input and no flags — check if config exists
        from .config import load_config
        if not load_config():
            print("No config found. Run 'mdl --setup' to get started.")
            sys.exit(1)
        parser.print_help()


def main_gui():
    launch_gui()

if __name__ == "__main__":
    main()
