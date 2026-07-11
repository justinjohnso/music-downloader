import os
import asyncio
import sys
from typing import Optional, List, Dict, Literal, Tuple
from streamrip.client import DeezerClient
from streamrip.config import Config
from streamrip.db import Database, Downloads, Failed, Dummy
from streamrip.exceptions import AuthenticationError, MissingCredentialsError
from streamrip.media import PendingTrack
from streamrip.metadata import AlbumMetadata
from streamrip.media.artwork import download_artwork

ANSI_RESET = "\033[0m"
ANSI_CYAN = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_GREEN = "\033[92m"
ANSI_BOLD = "\033[1m"


async def download_track_with_client(
    client,
    config,
    search_string: str,
    db=None,
    verbose: bool = False,
    duplicate_mode: Literal["prompt", "skip", "redownload"] = "prompt",
) -> Tuple[Literal["downloaded", "duplicate_skipped", "failed"], Optional[str]]:
    """
    Search for a track on Deezer using the provided client and download the first result.

    Args:
        client: An initialized DeezerClient
        config: The loaded config
        search_string (str): The search query (artist and track name).
        db: The database instance to use
        verbose (bool): Whether to print detailed output

    Returns:
        Tuple of (status, track label)
    """
    try:
        # Search for the track
        try:
            results = await client.search(query=search_string, media_type="track")
        except Exception as e:
            print(f"Error during search: {e}")
            return "failed", None

        # Process search results
        tracks = results
        if isinstance(tracks, dict) and "data" in tracks:
            tracks = tracks["data"]
        if not tracks:
            print(f"No tracks found for query: '{search_string}'")
            return "failed", None

        track = tracks[0]
        if isinstance(track, dict) and "data" in track:
            track = track["data"][0]

        # Extract track information
        track_id = track.get("id")
        title = track.get("title")
        artist = None
        if isinstance(track.get("artist"), dict):
            artist = track["artist"].get("name")
        elif isinstance(track.get("artist"), str):
            artist = track["artist"]
        print(f"Found track: {title} by {artist}")

        if not track_id:
            print("Error: Could not determine track ID.")
            return "failed", None

        # Use provided database or create one from config.
        if db is None:
            db = _build_database_from_config(config)

        track_label = f"{title} by {artist}"
        effective_db = db
        if db.downloaded(str(track_id)):
            action = _resolve_duplicate_action(track_label, duplicate_mode)
            if action == "skip":
                print(_warn(f"Track already downloaded, skipping: {track_label}"))
                return "duplicate_skipped", track_label
            print(_ok(f"Duplicate detected, re-downloading: {track_label}"))
            effective_db = Database(downloads=Dummy(), failed=db.failed)

        download_folder = config.file.downloads.folder

        try:
            # Get album metadata
            album_id = track["album"]["id"]
            album_data = await client.get_metadata(album_id, "album")
            album = AlbumMetadata.from_album_resp(album_data, client.source)

            if verbose:
                print(f"Got album metadata: {album.album}")

            # Download album artwork
            artwork_folder = os.path.join(download_folder, ".artwork")
            os.makedirs(artwork_folder, exist_ok=True)

            cover_path, _ = await download_artwork(
                client.session,
                artwork_folder,
                album.covers,
                config.file.artwork,
                for_playlist=False,
            )

            if verbose:
                print("Downloaded album artwork")

            # Create a PendingTrack with all required parameters
            pending = PendingTrack(
                id=track_id,
                album=album,
                client=client,
                config=config,
                folder=download_folder,
                db=effective_db,
                cover_path=cover_path,
            )
        except Exception as e:
            print(f"Error preparing download: {e}")
            return "failed", None

        try:
            # Resolve and download the track
            print(f"Downloading '{title}' by {artist}...")
            resolved = await pending.resolve()
            if resolved is None:
                print(_warn(f"Track already downloaded, skipping: {track_label}"))
                return "duplicate_skipped", track_label
            await resolved.rip()
            print(f"Successfully downloaded '{title}' by {artist}")
            return "downloaded", track_label
        except Exception as e:
            print(f"Error downloading track: {e}")
            return "failed", track_label
    except Exception as e:
        print(f"Error during track processing: {e}")
        return "failed", None


async def download_multiple_tracks(
    tracks: List[Dict[str, str]],
    config_path: str = None,
    verbose: bool = False,
    is_playlist: bool = False,
    playlist_name: Optional[str] = None,
) -> None:
    """
    Download multiple tracks from Deezer based on artist and title information.

    Args:
        tracks: List of dictionaries with track information (artist and title)
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
        is_playlist: Whether this is from a Spotify playlist
        playlist_name: Name of the playlist if applicable
    """
    from src.config import (
        load_config_with_path,
        ensure_streamrip_config_exists,
        apply_config_overrides,
    )

    # Load configuration from mdl-config.toml
    config_data, mdl_config_path = load_config_with_path(verbose=verbose)

    if verbose and mdl_config_path:
        print(f"Using mdl config: {mdl_config_path}")

    # Use provided config path or ensure default exists
    config_path = config_path or ensure_streamrip_config_exists()

    if verbose:
        print(f"Using streamrip config: {config_path}")

    # Load configuration and initialize client (only once for all tracks)
    config = Config(config_path)
    apply_config_overrides(config, config_data)
    config.session.update_toml()  # Sync session changes back to file config
    client = DeezerClient(config)
    db = _build_database_from_config(config)

    try:
        try:
            await client.login()
        except AuthenticationError:
            print("Deezer login failed — your ARL may be expired. Run 'mdl --set-arl' to update it.")
            return
        except MissingCredentialsError:
            print("No Deezer ARL configured. Run 'mdl --setup' to add one.")
            return
        print("Logged in to Deezer.")

        if verbose:
            print(
                f"Actual download folder from config.file: {config.file.downloads.folder}"
            )
            print(f"Session download folder: {config.session.downloads.folder}")

        successful_downloads = 0
        failed_downloads = 0
        duplicate_downloads = 0
        duplicate_tracks: List[Dict[str, str]] = []

        total_tracks = len(tracks)
        print(f"Processing {total_tracks} tracks...")

        # Process each track
        for i, track in enumerate(tracks):
            artist = track.get("artist", "")
            title = track.get("title", "")
            search_string = f"{artist} {title}"

            print(f"\nProcessing track {i + 1}/{total_tracks}: {artist} - {title}")

            # Use the download function with shared client
            status, track_label = await download_track_with_client(
                client,
                config,
                search_string,
                db,
                verbose,
                duplicate_mode="skip",
            )

            if status == "downloaded":
                successful_downloads += 1
            elif status == "duplicate_skipped":
                duplicate_downloads += 1
                if track_label:
                    duplicate_tracks.append(
                        {"label": track_label, "search_string": search_string}
                    )
            else:
                failed_downloads += 1

            # Add a small delay between downloads to avoid hammering the API
            if i < total_tracks - 1:
                await asyncio.sleep(1)

        print(
            f"\nDownload summary: {successful_downloads} successful, {duplicate_downloads} duplicates skipped, {failed_downloads} failed out of {total_tracks} total"
        )
        tracks_to_redownload = _offer_duplicate_review(duplicate_tracks)
        if tracks_to_redownload:
            print(
                _action(
                    f"\nRe-downloading {len(tracks_to_redownload)} selected duplicate track(s)..."
                )
            )
            redownload_successful = 0
            redownload_failed = 0
            for track in tracks_to_redownload:
                status, _ = await download_track_with_client(
                    client,
                    config,
                    track["search_string"],
                    db,
                    verbose,
                    duplicate_mode="redownload",
                )
                if status == "downloaded":
                    redownload_successful += 1
                else:
                    redownload_failed += 1

            print(
                _info(
                    f"Re-download summary: {redownload_successful} successful, {redownload_failed} failed"
                )
            )

        # Generate M3U playlist file for Spotify playlists
        if is_playlist and successful_downloads > 0 and playlist_name:
            download_folder = config.file.downloads.folder
            # Sanitize playlist name for filename
            safe_name = "".join(
                c for c in playlist_name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            m3u_filename = f"{safe_name}.m3u"
            m3u_path = os.path.join(download_folder, m3u_filename)
            try:
                # List all .mp3 files in the download folder
                mp3_files = [
                    f for f in os.listdir(download_folder) if f.endswith(".mp3")
                ]
                mp3_files.sort()  # Sort for consistent order
                with open(m3u_path, "w", encoding="utf-8") as f:
                    for mp3 in mp3_files:
                        f.write(f"{mp3}\n")
                print(f"Generated M3U playlist '{playlist_name}' at: {m3u_path}")
            except Exception as e:
                print(f"Warning: Could not generate M3U playlist: {e}")

    finally:
        # Clean up client session
        if hasattr(client, "session") and client.session:
            try:
                if not client.session.closed:
                    # Cancel any pending requests
                    for task in asyncio.all_tasks():
                        if not task.done() and task != asyncio.current_task():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                    # Close the session
                    await client.session.close()

                # Close the connector
                if hasattr(client.session, "_connector") and client.session._connector:
                    await client.session._connector.close()

                await asyncio.sleep(0.1)

                if verbose:
                    print("Successfully closed client session")
            except (Exception, asyncio.CancelledError) as e:
                if verbose:
                    print(f"Error while closing client session: {e}")


async def download_track(
    search_string: str, config_path: str = None, verbose: bool = False
) -> None:
    """
    Search for a track on Deezer using the provided search string and download the first result.

    Args:
        search_string (str): The search query (artist and track name).
        config_path (str, optional): Path to streamrip config file.
        verbose (bool): Whether to print detailed output.
    """
    from src.config import (
        load_config_with_path,
        ensure_streamrip_config_exists,
        apply_config_overrides,
    )

    # Load configuration from mdl-config.toml
    config_data, mdl_config_path = load_config_with_path(verbose=verbose)

    if verbose and mdl_config_path:
        print(f"Using mdl config: {mdl_config_path}")

    # Use provided config path or ensure default exists
    config_path = config_path or ensure_streamrip_config_exists()

    if verbose:
        print(f"Using streamrip config: {config_path}")

    # Load configuration and initialize client
    config = Config(config_path)
    apply_config_overrides(config, config_data)
    config.session.update_toml()  # Sync session changes back to file config
    client = DeezerClient(config)

    try:
        try:
            await client.login()
        except AuthenticationError:
            print("Deezer login failed — your ARL may be expired. Run 'mdl --set-arl' to update it.")
            return
        except MissingCredentialsError:
            print("No Deezer ARL configured. Run 'mdl --setup' to add one.")
            return
        print("Logged in to Deezer.")

        if verbose:
            print(
                f"Actual download folder from config.file: {config.file.downloads.folder}"
            )
            print(f"Session download folder: {config.session.downloads.folder}")

        # Use the shared download function
        await download_track_with_client(
            client, config, search_string, verbose=verbose, duplicate_mode="prompt"
        )

    finally:
        # Clean up client session
        if hasattr(client, "session") and client.session:
            try:
                if not client.session.closed:
                    # Cancel any pending requests
                    for task in asyncio.all_tasks():
                        if not task.done() and task != asyncio.current_task():
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                    # Close the session
                    await client.session.close()

                # Close the connector
                if hasattr(client.session, "_connector") and client.session._connector:
                    await client.session._connector.close()

                await asyncio.sleep(0.1)

                if verbose:
                    print("Successfully closed client session")
            except (Exception, asyncio.CancelledError) as e:
                if verbose:
                    print(f"Error while closing client session: {e}")


def _build_database_from_config(config: Config) -> Database:
    """Create a streamrip Database that respects the active config flags and paths."""
    database_config = config.session.database
    downloads_db = (
        Downloads(database_config.downloads_path)
        if database_config.downloads_enabled
        else Dummy()
    )
    failed_db = (
        Failed(database_config.failed_downloads_path)
        if database_config.failed_downloads_enabled
        else Dummy()
    )
    return Database(downloads=downloads_db, failed=failed_db)


def _can_prompt_user() -> bool:
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


def _colorize(text: str, *styles: str) -> str:
    if not _can_prompt_user():
        return text
    return f"{''.join(styles)}{text}{ANSI_RESET}"


def _info(text: str) -> str:
    return _colorize(text, ANSI_CYAN)


def _action(text: str) -> str:
    return _colorize(text, ANSI_BOLD, ANSI_CYAN)


def _warn(text: str) -> str:
    return _colorize(text, ANSI_BOLD, ANSI_YELLOW)


def _ok(text: str) -> str:
    return _colorize(text, ANSI_BOLD, ANSI_GREEN)


def _resolve_duplicate_action(
    track_label: str, duplicate_mode: Literal["prompt", "skip", "redownload"]
) -> Literal["skip", "redownload"]:
    if duplicate_mode == "redownload":
        return "redownload"
    if duplicate_mode == "skip" or not _can_prompt_user():
        return "skip"

    prompt = (
        f"{_warn('Duplicate found:')} {_info(track_label)}\n"
        f"{_action('Download again? [y/n]:')} "
    )
    while True:
        response = input(prompt).strip().lower()
        if response in {"", "n", "no"}:
            return "skip"
        if response in {"y", "yes"}:
            return "redownload"
        print(_warn("Invalid choice. Enter y or n."))


def _offer_duplicate_review(
    duplicate_tracks: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    if not duplicate_tracks:
        return []

    if not _can_prompt_user():
        print(
            f"Skipped {len(duplicate_tracks)} duplicate track(s). Re-run with --verbose to see per-track output."
        )
        return []

    print(
        _action(
            f"Skipped {len(duplicate_tracks)} duplicate track(s). Opening review selector (q to continue)."
        )
    )

    if os.name == "posix":
        try:
            return _offer_duplicate_review_arrow_mode(duplicate_tracks)
        except KeyboardInterrupt:
            print(_warn("\nDuplicate review cancelled."))
            return []
        except Exception:
            # Fall back to prompt commands if raw key handling is unavailable.
            pass

    return _offer_duplicate_review_line_mode(duplicate_tracks)


def _offer_duplicate_review_arrow_mode(
    duplicate_tracks: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    import curses

    selected_indices: set[int] = set()
    cursor_index = 0
    controls_line = "↑/↓ move • Enter/space/←/→ toggle • a all • d download selected • q keep skipped"

    def _selector(stdscr):
        nonlocal cursor_index, selected_indices, controls_line

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)  # info/action
            curses.init_pair(2, curses.COLOR_YELLOW, -1)  # warning/highlighted labels
            curses.init_pair(3, curses.COLOR_GREEN, -1)  # selected

        def _style(pair: int, bold: bool = False, reverse: bool = False) -> int:
            attrs = curses.color_pair(pair) if curses.has_colors() else curses.A_NORMAL
            if bold:
                attrs |= curses.A_BOLD
            if reverse:
                attrs |= curses.A_REVERSE
            return attrs

        curses.curs_set(0)
        stdscr.keypad(True)

        while True:
            height, width = stdscr.getmaxyx()
            stdscr.erase()
            stdscr.addstr(
                0,
                0,
                "DUPLICATE REVIEW"[: max(0, width - 1)],
                _style(2, bold=True),
            )
            stdscr.addstr(
                1,
                0,
                f"{len(duplicate_tracks)} duplicate track(s) were skipped. Select any to re-download now."[
                    : max(0, width - 1)
                ],
                _style(1, bold=True),
            )
            stdscr.addstr(2, 0, controls_line[: max(0, width - 1)], _style(1))

            list_start_row = 4
            footer_rows = 2
            max_rows = max(0, height - list_start_row - footer_rows)
            start_index = 0
            if cursor_index >= max_rows and max_rows > 0:
                start_index = cursor_index - max_rows + 1
            visible_tracks = duplicate_tracks[start_index : start_index + max_rows]

            for row_offset, track in enumerate(visible_tracks, start=0):
                idx = start_index + row_offset
                pointer = ">" if idx == cursor_index else " "
                marker = "[x]" if idx in selected_indices else "[ ]"
                line = f"{pointer} {marker} {idx + 1}. {track['label']}"
                line_attr = _style(
                    2 if idx == cursor_index else 1, bold=idx == cursor_index
                )
                if idx in selected_indices:
                    line_attr = _style(3, bold=True, reverse=(idx == cursor_index))
                elif idx == cursor_index:
                    line_attr = _style(2, bold=True, reverse=True)
                stdscr.addstr(
                    row_offset + list_start_row, 0, line[: max(0, width - 1)], line_attr
                )

            selected_count = len(selected_indices)
            stdscr.addstr(
                height - 2,
                0,
                f"Selected: {selected_count}/{len(duplicate_tracks)}"[
                    : max(0, width - 1)
                ],
                _style(3 if selected_count > 0 else 1, bold=True),
            )
            action_parts = [
                ("[D]", _style(3, bold=True)),
                (" Download selected   ", _style(1)),
                ("[Q]", _style(2, bold=True)),
                (" Quit", _style(1)),
            ]
            x = 0
            for text, attr in action_parts:
                remaining = max(0, width - 1 - x)
                if remaining <= 0:
                    break
                chunk = text[:remaining]
                if chunk:
                    stdscr.addstr(height - 1, x, chunk, attr)
                    x += len(chunk)
            stdscr.refresh()

            key = stdscr.getch()
            if key == 3:  # Ctrl+C
                raise KeyboardInterrupt
            if key in (curses.KEY_UP,):
                cursor_index = (cursor_index - 1) % len(duplicate_tracks)
                continue
            if key in (curses.KEY_DOWN,):
                cursor_index = (cursor_index + 1) % len(duplicate_tracks)
                continue
            if key in (curses.KEY_LEFT, curses.KEY_RIGHT, ord(" "), ord("t"), ord("T")):
                if cursor_index in selected_indices:
                    selected_indices.remove(cursor_index)
                else:
                    selected_indices.add(cursor_index)
                continue
            if key in (ord("a"), ord("A")):
                if len(selected_indices) == len(duplicate_tracks):
                    selected_indices.clear()
                else:
                    selected_indices = set(range(len(duplicate_tracks)))
                continue
            if key in (10, 13, curses.KEY_ENTER):
                if cursor_index in selected_indices:
                    selected_indices.remove(cursor_index)
                else:
                    selected_indices.add(cursor_index)
                continue
            if key in (ord("d"), ord("D")):
                if selected_indices:
                    return [duplicate_tracks[i] for i in sorted(selected_indices)]
                return []
            if key in (ord("q"), ord("Q")):
                return []

    return curses.wrapper(_selector)


def _offer_duplicate_review_line_mode(
    duplicate_tracks: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    from rich.prompt import Prompt

    selected_indices: set[int] = set()
    cursor_index = 0

    while True:
        print(_info("\nToggle duplicate tracks for re-download:"))
        print(
            _info(
                "Use [n] next, [p] previous, [enter]/[t] toggle current, [a] all, [d] download selected, [q] quit"
            )
        )
        for idx, track in enumerate(duplicate_tracks, start=1):
            pointer = _action(">") if (idx - 1) == cursor_index else " "
            marker = _ok("[x]") if (idx - 1) in selected_indices else _info("[ ]")
            print(f"{pointer} {marker} {_info(str(idx) + '.')} {_ok(track['label'])}")

        try:
            response = (
                Prompt.ask("[bold cyan]Selection[/bold cyan]", default="")
                .strip()
                .lower()
            )
        except KeyboardInterrupt:
            print(_warn("\nDuplicate review cancelled."))
            return []

        if response == "":
            if cursor_index in selected_indices:
                selected_indices.remove(cursor_index)
            else:
                selected_indices.add(cursor_index)
            continue
        if response == "d":
            if not selected_indices:
                print(_warn("No tracks selected. Toggle at least one item first."))
                continue
            return [duplicate_tracks[i] for i in sorted(selected_indices)]
        if response in {"n", "next"}:
            cursor_index = (cursor_index + 1) % len(duplicate_tracks)
            continue
        if response in {"p", "prev", "previous"}:
            cursor_index = (cursor_index - 1) % len(duplicate_tracks)
            continue
        if response == "a":
            if len(selected_indices) == len(duplicate_tracks):
                selected_indices.clear()
            else:
                selected_indices = set(range(len(duplicate_tracks)))
            continue
        if response in {"q", "quit"}:
            return []
        if response in {"t", "toggle"}:
            if cursor_index in selected_indices:
                selected_indices.remove(cursor_index)
            else:
                selected_indices.add(cursor_index)
            continue

        print(
            _warn(
                "Invalid selection. Use [n], [p], [t], [a], [d], [q] (quit), or Enter."
            )
        )


async def process_spotify_link(
    spotify_link: str, config_path: str = None, verbose: bool = False
) -> None:
    """
    Process a Spotify link to download tracks.

    Args:
        spotify_link: Spotify track or playlist link
        config_path: Path to streamrip config file
        verbose: Whether to print detailed output
    """
    from src.spotify import get_spotify_tracks

    try:
        # Get tracks from Spotify
        print("Retrieving track information from Spotify...")

        # Run the synchronous Spotify API call in a thread
        tracks, info = await asyncio.get_event_loop().run_in_executor(
            None, get_spotify_tracks, spotify_link
        )

        if not tracks:
            print("No tracks found in the Spotify link.")
            return

        print(f"Found {len(tracks)} tracks")

        # Download tracks
        playlist_name = info["name"] if info["is_playlist"] else None
        await download_multiple_tracks(
            tracks, config_path, verbose, info["is_playlist"], playlist_name
        )

    except Exception as e:
        msg = str(e) or type(e).__name__
        print(f"Error processing Spotify link: {msg}")


def sync_downloads_db_from_library(
    library_path: Optional[str] = None, verbose: bool = False
) -> None:
    """
    Sync downloads DB by scanning the configured library folder for media files.
    This reads the tags from local files, searches Deezer for matching tracks,
    and populates the streamrip downloads database to prevent duplicates.
    """
    from src.config import (
        load_config_with_path,
        ensure_streamrip_config_exists,
        apply_config_overrides,
    )
    import os
    import asyncio
    from mutagen import File

    config_data, _ = load_config_with_path(verbose=verbose)
    config_path = ensure_streamrip_config_exists()

    config = Config(config_path)
    apply_config_overrides(config, config_data)

    db = _build_database_from_config(config)

    target_path = library_path or config.file.downloads.folder
    if target_path:
        target_path = os.path.expanduser(target_path)

    if not target_path or not os.path.exists(target_path):
        print(_warn(f"Library path does not exist: {target_path}"))
        return

    print(_info(f"Scanning library at '{target_path}' for media files..."))

    async def _sync_impl():
        client = DeezerClient(config)
        try:
            try:
                await client.login()
            except AuthenticationError:
                print("Deezer login failed — your ARL may be expired. Run 'mdl --set-arl' to update it.")
                return
            except MissingCredentialsError:
                print("No Deezer ARL configured. Run 'mdl --setup' to add one.")
                return

            synced_count = 0
            skipped_count = 0
            files_to_process = []

            for root, _, files in os.walk(target_path):
                for file in files:
                    if file.endswith((".flac", ".mp3", ".m4a", ".ogg")):
                        files_to_process.append(os.path.join(root, file))

            print(
                f"Found {len(files_to_process)} media files. This may take a while..."
            )

            for filepath in files_to_process:
                try:
                    audio = File(filepath, easy=True)
                    if not audio:
                        continue

                    title = audio.get("title", [None])[0]
                    artist = audio.get("artist", [None])[0]
                    isrc = audio.get("isrc", [None])[0]

                    if not title or not artist:
                        continue

                    search_query = (
                        f"isrc:{isrc}" if isrc else f'artist:"{artist}" track:"{title}"'
                    )

                    if verbose:
                        print(f"Searching Deezer for: {search_query}")

                    results = await client.search(
                        query=search_query, media_type="track"
                    )
                    tracks = (
                        results.get("data", [])
                        if isinstance(results, dict)
                        else results
                    )

                    if tracks:
                        track = (
                            tracks[0].get("data", [tracks[0]])[0]
                            if "data" in tracks[0]
                            else tracks[0]
                        )
                        track_id = track.get("id")

                        if track_id:
                            if not db.downloaded(str(track_id)):
                                db.set_downloaded(str(track_id))
                                synced_count += 1
                                if verbose:
                                    print(
                                        _ok(
                                            f"Added ID {track_id} for '{title}' by '{artist}'"
                                        )
                                    )
                            else:
                                skipped_count += 1
                                if verbose:
                                    print(f"ID {track_id} already in DB for '{title}'.")
                except Exception as e:
                    if verbose:
                        print(_warn(f"Error processing {filepath}: {e}"))

                # Rate limit safety
                await asyncio.sleep(0.5)

            print(
                _info(
                    f"\nSync complete: {synced_count} new tracks added to DB ({skipped_count} already existed)."
                )
            )
        finally:
            if (
                hasattr(client, "session")
                and client.session
                and not client.session.closed
            ):
                await client.session.close()

    asyncio.run(_sync_impl())
