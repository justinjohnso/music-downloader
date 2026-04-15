import argparse
import sys
from .spotify import is_spotify_link
from .core import (
    process_spotify_link,
    download_track,
    format_track_candidate,
    TrackCandidate,
)


def _prompt_for_candidate(
    search_string: str,
    candidates: list[TrackCandidate],
    source_track: dict[str, str] | None = None,
) -> int | None:
    """Prompt the user to select a Deezer match from search candidates."""
    if source_track is not None:
        print(
            f"\nSpotify match for: {source_track.get('artist', '')} - "
            f"{source_track.get('title', '')}"
        )

    print(f"\nSearch results for: {search_string}")
    for i, candidate in enumerate(candidates):
        print(format_track_candidate(candidate, i))

    while True:
        raw = input(f"Choose result [1-{len(candidates)}], s=skip, q=quit: ").strip()
        if raw.lower() == "s":
            return None
        if raw.lower() == "q":
            raise KeyboardInterrupt
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= len(candidates):
                return selected - 1
        print("Invalid choice. Please enter a result number, s, or q.")


def main():
    parser = argparse.ArgumentParser(
        description="Download music tracks from Deezer using Streamrip.",
        epilog=(
            "Spotify links use backend-first metadata resolution from mdl-config.toml:\n"
            '  [backend] resolve_url = "https://.../spotify/resolve"\n'
            '  [backend] api_key = "..."\n'
            "If backend is unavailable, you can set local fallback credentials:\n"
            '  [spotify] client_id = "..."\n'
            '  [spotify] client_secret = "..."'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input", nargs="?", help="Search query (artist and track name) or Spotify link"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print detailed output"
    )
    parser.add_argument(
        "--setup", action="store_true", help="Run first-time setup wizard"
    )
    parser.add_argument(
        "--first-result",
        action="store_true",
        help="Skip interactive candidate selection and download the first match.",
    )
    parser.add_argument(
        "--result-limit",
        type=int,
        default=10,
        help="Number of Deezer candidates to show for interactive selection (default: 10).",
    )

    args = parser.parse_args()

    if args.setup:
        from .config import run_setup_wizard

        run_setup_wizard()
    elif args.input:
        # Check if config exists before attempting a download
        from .config import load_config

        if not load_config():
            print("No config found. Run 'mdl --setup' to configure.")
            sys.exit(1)

        if is_spotify_link(args.input):
            # Handle Spotify link
            import asyncio

            interactive = not args.first_result and sys.stdin.isatty()
            try:
                asyncio.run(
                    process_spotify_link(
                        args.input,
                        None,
                        args.verbose,
                        interactive=interactive,
                        result_limit=max(1, args.result_limit),
                        selection_callback=(
                            _prompt_for_candidate if interactive else None
                        ),
                    )
                )
            except KeyboardInterrupt:
                print("\nDownload cancelled.")
        else:
            # Handle regular search string
            import asyncio

            interactive = not args.first_result and sys.stdin.isatty()
            try:
                asyncio.run(
                    download_track(
                        args.input,
                        None,
                        args.verbose,
                        interactive=interactive,
                        result_limit=max(1, args.result_limit),
                        selection_callback=(
                            _prompt_for_candidate if interactive else None
                        ),
                    )
                )
            except KeyboardInterrupt:
                print("\nDownload cancelled.")
    else:
        # No input and no flags — check if config exists
        from .config import load_config

        if not load_config():
            print("No config found. Run 'mdl --setup' to get started.")
            sys.exit(1)
        parser.print_help()


if __name__ == "__main__":
    main()
