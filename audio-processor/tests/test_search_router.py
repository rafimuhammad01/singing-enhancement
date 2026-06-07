from typing import Any

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.search import get_search_service

# ---------------------------------------------------------------------------
# Stub service — replaces SearchService via dependency_overrides.
# ---------------------------------------------------------------------------


class _StubSearchService:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = results
        self.calls: list[tuple[str, int]] = []  # (query, limit)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        self.calls.append((query, limit))
        return self.results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_stub():
    """Yields (client, stub). Caller sets stub.results before requesting."""
    stub = _StubSearchService(results=[])
    app.dependency_overrides[get_search_service] = lambda: stub
    try:
        yield TestClient(app), stub
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mapped_results",
    [
        (
            [
                {
                    "videoId": "dQw4w9WgXcQ",
                    "title": "Never Gonna Give You Up",
                    "artist": "Rick Astley",
                    "album": "Whenever You Need Somebody",
                    "duration_sec": 213,
                    "thumbnail_url": "https://example.com/large.jpg",
                },
                {
                    "videoId": "abc1234567A",
                    "title": "Another Song",
                    "artist": "Some Artist",
                    "album": None,
                    "duration_sec": 180,
                    "thumbnail_url": "https://example.com/small.jpg",
                },
            ],
        ),
    ],
    ids=["typical-mapped-results"],
)
def test_search_happy_path_returns_stub_results(mapped_results, client_with_stub):
    (results,) = mapped_results
    client, stub = client_with_stub
    stub.results = results

    response = client.post("/search", json={"query": "anything", "limit": 5})

    assert response.status_code == 200
    assert response.json() == results
    assert stub.calls == [("anything", 5)]


@pytest.mark.parametrize(
    "body",
    [
        ({"query": "x"},),
    ],
    ids=["limit-omitted"],
)
def test_search_default_limit_is_10(body, client_with_stub):
    (request_body,) = body
    client, stub = client_with_stub

    response = client.post("/search", json=request_body)

    assert response.status_code == 200
    assert stub.calls == [("x", 10)]


@pytest.mark.parametrize(
    "invalid_body",
    [
        {},
        {"query": ""},
        {"query": "x", "limit": 0},
        {"query": "x", "limit": 21},
        {"query": "x", "limit": -1},
        {"query": "x" * 201},
    ],
    ids=[
        "missing-query",
        "empty-query",
        "limit-zero",
        "limit-too-high",
        "limit-negative",
        "query-too-long",
    ],
)
def test_search_rejects_invalid_request(invalid_body, client_with_stub):
    client, stub = client_with_stub

    response = client.post("/search", json=invalid_body)

    assert response.status_code == 422
    assert stub.calls == []


@pytest.mark.parametrize(
    "query,limit,mapped_results",
    [
        ("wish you were here", 10, []),
        (
            "bohemian rhapsody",
            5,
            [
                {
                    "videoId": "x",
                    "title": "t",
                    "artist": "a",
                    "album": None,
                    "duration_sec": 100,
                    "thumbnail_url": "u",
                }
            ],
        ),
    ],
    ids=["empty-results", "single-result"],
)
def test_search_passes_through_to_service(query, limit, mapped_results, client_with_stub):
    client, stub = client_with_stub
    stub.results = mapped_results

    response = client.post("/search", json={"query": query, "limit": limit})

    assert response.status_code == 200
    assert response.json() == mapped_results
    assert stub.calls == [(query, limit)]
