from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Callable

from .search import search_track_candidates_with_client


@dataclass
class DownloadOutcome:
    query: str
    status: str
    message: str = ""
    candidate_id: str | None = None
    path: str | None = None
    candidate: dict | None = None

    def to_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if key != "candidate"}


async def download_item(
    query: str,
    *,
    candidate: dict | None = None,
    config_path: str | None = None,
    selection_callback=None,
    result_limit: int = 10,
    verbose: bool = False,
) -> DownloadOutcome:
    """Use one configured download path for both CLI and GUI queue items."""
    from .config import (
        Config,
        load_config,
        ensure_streamrip_config_exists,
        apply_config_overrides,
    )
    from .core import download_track_with_client, _build_database_from_config
    from streamrip.client import DeezerClient
    from streamrip.exceptions import AuthenticationError, MissingCredentialsError

    client = None
    selected = candidate
    try:
        config = Config(config_path or ensure_streamrip_config_exists())
        apply_config_overrides(config, load_config())
        client = DeezerClient(config)
        await client.login()
        if selected is None:
            matches = await search_track_candidates_with_client(
                client, query, result_limit
            )
            if not matches:
                return DownloadOutcome(query, "failed", "No Deezer match")
            index = (
                selection_callback(query, matches, None) if selection_callback else 0
            )
            if index is None:
                return DownloadOutcome(query, "skipped", "Selection skipped")
            if not isinstance(index, int) or not 0 <= index < len(matches):
                return DownloadOutcome(query, "failed", "Invalid match selection")
            selected = matches[index]
        details = []
        status, label = await download_track_with_client(
            client,
            config,
            query,
            db=_build_database_from_config(config),
            verbose=verbose,
            duplicate_mode="skip",
            selected_candidate=selected,
            outcome_callback=lambda status, message, path: details.append(
                (status, message, path)
            ),
        )
        return DownloadOutcome(
            query,
            "skipped" if status == "duplicate_skipped" else status,
            details[-1][1] if details else (label or "Duplicate skipped"),
            str(selected["id"]),
            path=details[-1][2] if details else None,
            candidate=selected,
        )
    except asyncio.CancelledError:
        raise
    except (AuthenticationError, MissingCredentialsError):
        return DownloadOutcome(
            query,
            "failed",
            "Deezer login failed. Run mdl --set-arl or mdl --setup.",
            str(selected["id"]) if selected else None,
            candidate=selected,
        )
    except Exception as error:
        return DownloadOutcome(
            query,
            "failed",
            str(error) or type(error).__name__,
            str(selected["id"]) if selected else None,
            candidate=selected,
        )
    finally:
        session = getattr(client, "session", None)
        if session is not None and not session.closed:
            await session.close()


async def run_queue(
    items: list[dict],
    *,
    download: Callable = download_item,
    retries: int = 0,
    config_path: str | None = None,
    selection_callback=None,
    result_limit: int = 10,
    verbose: bool = False,
    outcome_callback=None,
) -> list[DownloadOutcome]:
    """Process source-ordered items with bounded retries and distinct outcomes."""
    if not 0 <= retries <= 10:
        raise ValueError("Retries must be between 0 and 10")
    outcomes = []
    for item in items:
        if "error" in item:
            result = DownloadOutcome(item["query"], "failed", item["error"])
            outcomes.append(result)
            if outcome_callback is not None:
                outcome_callback(result)
            continue
        chosen = item.get("candidate")
        for attempt in range(retries + 1):
            result = await download(
                item["query"],
                candidate=chosen,
                config_path=config_path,
                selection_callback=selection_callback if attempt == 0 else None,
                result_limit=result_limit,
                verbose=verbose,
            )
            chosen = result.candidate or chosen
            if result.status != "failed":
                break
        outcomes.append(result)
        if outcome_callback is not None:
            outcome_callback(result)
    return outcomes


async def expand_input(value: str) -> list[dict]:
    """Expand queries and Spotify metadata into the same queue item contract."""
    from .spotify import is_spotify_link, get_spotify_tracks

    if not is_spotify_link(value):
        return [{"query": value}]
    try:
        tracks, _ = await asyncio.to_thread(get_spotify_tracks, value)
        if not tracks:
            return [{"query": value, "error": "No Spotify tracks found"}]
        return [{"query": f"{track['artist']} {track['title']}"} for track in tracks]
    except Exception as error:
        return [{"query": value, "error": str(error) or type(error).__name__}]
