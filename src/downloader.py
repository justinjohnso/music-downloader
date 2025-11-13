import argparse
from .spotify import is_spotify_link
from .core import process_spotify_link, download_track


def main() -> None:
    """Parse command line arguments and start the download process."""
    parser = argparse.ArgumentParser(description="Download music tracks from Deezer using Streamrip.")
    parser.add_argument("input", type=str, help="Search query (artist and track name) or Spotify link")
    parser.add_argument("-c", "--config", type=str, help="Path to streamrip config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print detailed output")

    args = parser.parse_args()

    if is_spotify_link(args.input):
        # Handle Spotify link
        import asyncio
        asyncio.run(process_spotify_link(args.input, args.config, args.verbose))
    else:
        # Handle regular search string
        import asyncio
        asyncio.run(download_track(args.input, args.config, args.verbose))


if __name__ == "__main__":
    main()
