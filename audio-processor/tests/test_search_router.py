from typing import Any

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.search import get_search_service

# ---------------------------------------------------------------------------
# Stub service — replaces SearchService via dependency_overrides.
# ---------------------------------------------------------------------------


class _StubSearchService:
    def __init__(self, results: list[dict[str, Any]], has_more: bool = False) -> None:
        self.results = results
        self.has_more = has_more
        self.calls: list[tuple[str, int, int]] = []  # (query, limit, offset)

    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], bool]:
        self.calls.append((query, limit, offset))
        return self.results, self.has_more


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_stub():
    """Yields (client, stub). Caller sets stub.results before requesting."""
    stub = _StubSearchService(results=[], has_more=False)
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
    assert response.json() == {"items": results, "has_more": False}
    assert stub.calls == [("anything", 5, 0)]


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
    assert stub.calls == [("x", 10, 0)]


@pytest.mark.parametrize(
    "invalid_body",
    [
        {},
        {"query": ""},
        {"query": "x", "limit": 0},
        {"query": "x", "limit": 21},
        {"query": "x", "limit": -1},
        {"query": "x" * 201},
        {"query": "x", "offset": -1},
    ],
    ids=[
        "missing-query",
        "empty-query",
        "limit-zero",
        "limit-too-high",
        "limit-negative",
        "query-too-long",
        "negative-offset",
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
    assert response.json() == {"items": mapped_results, "has_more": False}
    assert stub.calls == [(query, limit, 0)]


@pytest.mark.parametrize(
    "body,want_call",
    [
        ({"query": "x", "limit": 10, "offset": 0}, ("x", 10, 0)),
        ({"query": "x", "limit": 10, "offset": 20}, ("x", 10, 20)),
        ({"query": "x", "limit": 5, "offset": 15}, ("x", 5, 15)),
    ],
    ids=["offset-0", "offset-20", "offset-15-limit-5"],
)
def test_search_forwards_offset_to_service(body, want_call, client_with_stub):
    client, stub = client_with_stub
    response = client.post("/search", json=body)
    assert response.status_code == 200
    assert stub.calls == [want_call]


@pytest.mark.parametrize(
    "body",
    [({"query": "x"},)],
    ids=["offset-omitted"],
)
def test_search_default_offset_is_0(body, client_with_stub):
    (request_body,) = body
    client, stub = client_with_stub
    response = client.post("/search", json=request_body)
    assert response.status_code == 200
    assert stub.calls == [("x", 10, 0)]


@pytest.mark.parametrize(
    "stub_results,stub_has_more",
    [
        ([], False),
        (
            [
                {
                    "videoId": "a" * 11,
                    "title": "t",
                    "artist": "a",
                    "album": None,
                    "duration_sec": 1,
                    "thumbnail_url": "u",
                }
            ],
            False,
        ),
        (
            [
                {
                    "videoId": "a" * 11,
                    "title": "t",
                    "artist": "a",
                    "album": None,
                    "duration_sec": 1,
                    "thumbnail_url": "u",
                }
            ],
            True,
        ),
    ],
    ids=["empty-no-more", "single-no-more", "single-has-more"],
)
def test_search_envelope_shape(stub_results, stub_has_more, client_with_stub):
    client, stub = client_with_stub
    stub.results = stub_results
    stub.has_more = stub_has_more

    response = client.post("/search", json={"query": "x"})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "has_more"}
    assert body["items"] == stub_results
    assert body["has_more"] is stub_has_more


@pytest.mark.parametrize(
    "body,id_label",
    [
        ({"query": "x", "limit": 20, "offset": 81}, "limit-20-offset-81-total-101"),
        ({"query": "x", "limit": 10, "offset": 100}, "limit-10-offset-100-total-110"),
        ({"query": "x", "limit": 1, "offset": 100}, "limit-1-offset-100-total-101"),
    ],
    ids=["limit-20-offset-81", "limit-10-offset-100", "limit-1-offset-100"],
)
def test_search_rejects_offset_limit_over_cap(body, id_label, client_with_stub):
    client, stub = client_with_stub
    response = client.post("/search", json=body)
    assert response.status_code == 422
    assert stub.calls == []
