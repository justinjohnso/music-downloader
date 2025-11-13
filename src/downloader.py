import argparse
import sys
from .gui import launch_gui
from .spotify import is_spotify_link
from .core import process_spotify_link, download_track

def main():
    parser = argparse.ArgumentParser(description="Download music tracks from Deezer using Streamrip.")
    parser.add_argument("input", nargs='?', help="Search query (artist and track name) or Spotify link")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print detailed output")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")

    args = parser.parse_args()

    if args.gui:
        launch_gui()
    elif args.input:
        if is_spotify_link(args.input):
            # Handle Spotify link
            import asyncio
            asyncio.run(process_spotify_link(args.input, None, args.verbose))
        else:
            # Handle regular search string
            import asyncio
            asyncio.run(download_track(args.input, None, args.verbose))
    else:
        parser.print_help()


def main_gui():
    launch_gui()

if __name__ == "__main__":
    main()
