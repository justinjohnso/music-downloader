import asyncio
from unittest.mock import AsyncMock

from src.workflow import DownloadOutcome, run_queue


def test_retry_preserves_chosen_id_and_reports_outcome():
    attempt = AsyncMock(
        side_effect=[
            DownloadOutcome("query", "failed", candidate_id="7"),
            DownloadOutcome("query", "downloaded", candidate_id="7"),
        ]
    )
    results = asyncio.run(
        run_queue(
            [{"query": "query", "candidate": {"id": "7"}}], download=attempt, retries=1
        )
    )
    assert results[0].status == "downloaded"
    assert attempt.await_count == 2
    assert attempt.call_args.kwargs["candidate"]["id"] == "7"


def test_failures_and_skips_are_distinguishable():
    attempt = AsyncMock(
        side_effect=[
            DownloadOutcome("a", "skipped"),
            DownloadOutcome("b", "failed", message="No match"),
        ]
    )
    results = asyncio.run(run_queue([{"query": "a"}, {"query": "b"}], download=attempt))
    assert [result.status for result in results] == ["skipped", "failed"]
    assert results[1].to_dict()["message"] == "No match"


def test_retry_keeps_candidate_resolved_on_first_attempt():
    candidate = {"id": "19", "title": "Chosen"}
    attempt = AsyncMock(
        side_effect=[
            DownloadOutcome("query", "failed", candidate_id="19", candidate=candidate),
            DownloadOutcome("query", "downloaded", candidate_id="19"),
        ]
    )
    asyncio.run(run_queue([{"query": "query"}], download=attempt, retries=1))
    assert attempt.call_args.kwargs["candidate"] == candidate


def test_json_outcomes_do_not_expose_raw_candidate():
    result = DownloadOutcome(
        "query", "failed", candidate={"id": "19", "track": {"private": "value"}}
    )
    assert "candidate" not in result.to_dict()
