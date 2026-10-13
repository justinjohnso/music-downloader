from __future__ import annotations

import asyncio
import copy
import json
import sys
from pathlib import Path

from .config import Config, _apply_to_session, _secure_write, load_config
from .core import _build_database_from_config
from .search import extract_track_results


def _search_config(path: str | None) -> Config:
    """Build a session without executing upstream CLI configuration callbacks."""
    config = Config(path) if path else Config.defaults()
    _apply_to_session(config.session, load_config())
    if not config.session.deezer.arl:
        raise RuntimeError(
            "No Deezer ARL configured. Run mdl setup or mdl auth refresh."
        )
    if not config.session.downloads.folder:
        raise RuntimeError("No download folder configured. Run mdl setup.")
    from .config import _default_database_paths

    defaults = _default_database_paths()
    if not config.session.database.downloads_path:
        config.session.database.downloads_path = defaults[0]
    if not config.session.database.failed_downloads_path:
        config.session.database.failed_downloads_path = defaults[1]
    config.session.update_toml()
    return config


def _normalized_pages(pages, limit: int) -> list[dict]:
    items = []
    for result in extract_track_results(pages):
        item = copy.deepcopy(result)
        if not item.get("id") or not isinstance(
            item.get("title") or item.get("name"), str
        ):
            continue
        artist = item.get("artist") or item.get("artists")
        if isinstance(artist, list):
            artist = artist[0] if artist else None
        if isinstance(artist, str):
            artist = {"name": artist}
        if not isinstance(artist, dict) or not isinstance(artist.get("name"), str):
            artist = {"name": "Unknown Artist"}
        item["artist"] = artist
        items.append(item)
        if len(items) >= limit:
            break
    return [{"data": items}] if items else []


async def run_search(
    query: str,
    *,
    media_type: str = "track",
    config_path: str | None = None,
    first: bool = False,
    output_file: str | None = None,
    num_results: int = 100,
    verbose: bool = False,
    engine_factory=None,
) -> int:
    """Delegate selection to streamrip with mdl-owned config and lifecycle."""
    if media_type not in ("track", "album"):
        raise ValueError("Search type must be track or album")
    if num_results < 1:
        raise ValueError("Number of results must be positive")
    if first and output_file:
        raise ValueError("Choose --first or --output-file, not both")
    if (
        not first
        and not output_file
        and not (sys.stdin.isatty() and sys.stdout.isatty())
    ):
        raise RuntimeError(
            "Interactive search requires a terminal. Use --first or --output-file."
        )
    if output_file and Path(output_file).exists():
        raise ValueError("Output file already exists; choose a new file")
    from streamrip.client import DeezerClient
    from streamrip.exceptions import AuthenticationError, MissingCredentialsError
    from streamrip.metadata.search_results import SearchResults
    from streamrip.rip.main import Main

    config = _search_config(config_path)
    client = DeezerClient(config)
    original_search = client.search
    limit = 1 if first else num_results

    async def bounded_search(media_type, query, limit=100):
        pages = await original_search(
            media_type=media_type,
            query=query,
            limit=min(limit, num_results) if not first else 1,
        )
        return _normalized_pages(pages, 1 if first else num_results)

    client.search = bounded_search

    class SearchSession(Main):
        def __init__(self):
            self.config = config
            self.clients = {"deezer": client}
            if not output_file:
                for enabled, path in (
                    (
                        config.session.database.downloads_enabled,
                        config.session.database.downloads_path,
                    ),
                    (
                        config.session.database.failed_downloads_enabled,
                        config.session.database.failed_downloads_path,
                    ),
                ):
                    if enabled:
                        Path(path).parent.mkdir(parents=True, exist_ok=True)
                self.database = _build_database_from_config(config)
            else:
                self.database = None
            self.pending = []
            self.media = []

        async def get_logged_in_client(self, source):
            if source != "deezer":
                raise ValueError("Only Deezer search is supported")
            if not client.logged_in:
                await client.login()
            return client

    from streamrip.media import artwork
    from streamrip import progress

    artwork_before = set(artwork._artwork_tempdirs)
    engine = engine_factory(config, client) if engine_factory else SearchSession()
    try:
        try:
            await engine.get_logged_in_client("deezer")
        except (AuthenticationError, MissingCredentialsError) as error:
            raise RuntimeError(
                "Deezer login failed. Run mdl auth refresh or mdl setup."
            ) from error
        if output_file:
            pages = await client.search(media_type, query, limit=limit)
            results = SearchResults.from_pages("deezer", media_type, pages)
            _secure_write(
                Path(output_file), json.dumps(results.as_list("deezer"), indent=2)
            )
            print(f"Wrote {len(results.results)} results to {output_file}")
            return 0
        if first:
            pages = await client.search(media_type, query, limit=1)
            if not pages:
                print(f"No search results found for query {query}")
                return 0
            result = SearchResults.from_pages("deezer", media_type, pages).results[0]
            await engine.add_by_id("deezer", result.media_type(), result.id)
        else:
            await engine.search_interactive("deezer", media_type, query)
        from streamrip.media.album import Album
        from mutagen import File

        async def rip_pending(pending, item_type):
            if item_type == "track" and engine.database.downloaded(str(pending.id)):
                print(f"Skipping downloaded item {pending.id}")
                return 0
            try:
                media = await pending.resolve()
                if media is None:
                    print(
                        f"Unable to resolve selected {item_type} {pending.id}",
                        file=sys.stderr,
                    )
                    return 1
                if isinstance(media, Album):
                    await media.preprocess()
                    try:
                        return sum(
                            [
                                await rip_pending(track, "track")
                                for track in media.tracks
                            ]
                        )
                    finally:
                        await media.postprocess()
                await media.rip()
                output = getattr(media, "download_path", None)
                if (
                    not output
                    or not Path(output).is_file()
                    or await asyncio.to_thread(File, output) is None
                ):
                    print(
                        f"Selected track {pending.id} did not produce readable audio",
                        file=sys.stderr,
                    )
                    return 1
                return 0
            except asyncio.CancelledError:
                raise
            except Exception as error:
                print(
                    f"Download failed: {str(error) or type(error).__name__}",
                    file=sys.stderr,
                )
                return 1

        return (
            1
            if sum(
                [
                    await rip_pending(pending, media_type)
                    for pending in list(engine.pending)
                ]
            )
            else 0
        )
    finally:
        session = getattr(client, "session", None)
        try:
            if session is not None and not session.closed:
                await session.close()
        finally:
            progress.clear_progress()
            import shutil

            for folder in set(artwork._artwork_tempdirs) - artwork_before:
                shutil.rmtree(folder, ignore_errors=True)
                artwork._artwork_tempdirs.discard(folder)
