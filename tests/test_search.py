import asyncio
from unittest.mock import AsyncMock

import pytest

from src.search import (
    extract_track_results,
    search_track_candidates_with_client,
    format_track_candidate,
)


def track(identifier="1", title="Song"):
    return {
        "id": identifier,
        "title": title,
        "artist": {"name": "Artist"},
        "album": {"id": "2", "title": "Album"},
        "duration": 123,
    }


def test_result_pages_are_flattened_and_invalid_entries_skipped():
    assert extract_track_results(
        [{"data": [track(), None]}, {"data": [track("3")]}]
    ) == [track(), track("3")]
    assert extract_track_results({"data": []}) == []
    assert extract_track_results(None) == []


def test_search_limit_and_display():
    client = AsyncMock()
    client.search.return_value = [{"data": [track(), {"title": "invalid"}, track("3")]}]
    candidates = asyncio.run(search_track_candidates_with_client(client, "query", 1))
    assert len(candidates) == 1
    assert candidates[0]["id"] == "1"
    assert "Album" in format_track_candidate(candidates[0], 0)
    assert "2:03" in format_track_candidate(candidates[0])


def test_search_retries_broader_query_only_when_empty():
    client = AsyncMock()
    client.search.side_effect = [[], {"data": [track()]}]
    assert (
        asyncio.run(search_track_candidates_with_client(client, "Artist - Song"))[0][
            "title"
        ]
        == "Song"
    )
    assert client.search.call_args_list[1].kwargs["query"] == "Artist Song"


@pytest.mark.parametrize("limit", [0, -1])
def test_invalid_limit_is_rejected(limit):
    with pytest.raises(ValueError):
        asyncio.run(search_track_candidates_with_client(AsyncMock(), "query", limit))
