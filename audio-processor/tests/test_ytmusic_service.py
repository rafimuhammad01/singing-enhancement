from typing import Any

import pytest

from services.ytmusic_service import SearchService

# ---------------------------------------------------------------------------
# Stub client — no unittest.mock; a small hand-written stub is clearer.
# ---------------------------------------------------------------------------


class _StubYTMusic:
    """Records calls and returns a pre-loaded list. One per test instance."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = results
        self.calls: list[tuple[str, str, int]] = []  # (query, filter, limit)

    def search(self, query: str, filter: str, limit: int) -> list[dict[str, Any]]:
        self.calls.append((query, filter, limit))
        return self._results


# ---------------------------------------------------------------------------
# Raw-song factory — covers the happy-path shape.
# Pass video_id=None to omit "videoId" entirely (skip-case).
# ---------------------------------------------------------------------------


# Sentinel distinguishes "caller passed nothing" from "caller passed None".
_UNSET: Any = object()


def _raw_song(
    *,
    video_id: str | None = "dQw4w9WgXcQ",
    title: str = "Never Gonna Give You Up",
    artists: list[dict[str, str]] | None = None,
    album: Any = _UNSET,
    duration_seconds: int = 213,
    thumbnails: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "title": title,
        "artists": artists or [{"name": "Rick Astley", "id": "UC1"}],
        "album": (
            {"name": "Whenever You Need Somebody", "id": "MPRE1"} if album is _UNSET else album
        ),
        "duration": "3:33",  # ignored by the impl
        "duration_seconds": duration_seconds,
        "thumbnails": thumbnails
        or [
            {"url": "https://small.jpg", "width": 60, "height": 60},
            {"url": "https://large.jpg", "width": 544, "height": 544},
        ],
    }
    if video_id is not None:
        raw["videoId"] = video_id
    return raw


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_results",
    [
        ([_raw_song()],),
    ],
    ids=["all-fields-present"],
)
def test_search_maps_raw_song_to_clean_shape(raw_results):
    (results,) = raw_results
    stub = _StubYTMusic(results)
    service = SearchService(client=stub)

    mapped = service.search("rick astley")

    assert len(mapped) == 1
    item = mapped[0]
    assert set(item.keys()) == {
        "videoId",
        "title",
        "artist",
        "album",
        "duration_sec",
        "thumbnail_url",
    }
    assert item["videoId"] == "dQw4w9WgXcQ"
    assert item["title"] == "Never Gonna Give You Up"
    assert item["artist"] == "Rick Astley"
    assert item["album"] == "Whenever You Need Somebody"
    assert item["duration_sec"] == 213
    assert item["thumbnail_url"] == "https://large.jpg"


@pytest.mark.parametrize(
    "artists,expected_artist_str",
    [
        (
            [{"name": "Alice", "id": "UA1"}],
            "Alice",
        ),
        (
            [{"name": "Alice", "id": "UA1"}, {"name": "Bob", "id": "UB1"}],
            "Alice, Bob",
        ),
        (
            [
                {"name": "Alice", "id": "UA1"},
                {"name": "Bob", "id": "UB1"},
                {"name": "Charlie", "id": "UC1"},
            ],
            "Alice, Bob, Charlie",
        ),
    ],
    ids=["one", "two", "three"],
)
def test_search_joins_multiple_artists(artists, expected_artist_str):
    stub = _StubYTMusic([_raw_song(artists=artists)])
    service = SearchService(client=stub)

    mapped = service.search("any query")

    assert len(mapped) == 1
    assert mapped[0]["artist"] == expected_artist_str


@pytest.mark.parametrize(
    "build_raw",
    [
        # album key present but value is None
        (lambda: _raw_song(album=None),),
        # album key entirely absent — build inline
        (
            lambda: {
                "videoId": "dQw4w9WgXcQ",
                "title": "No Album Song",
                "artists": [{"name": "Rick Astley", "id": "UC1"}],
                "duration": "3:33",
                "duration_seconds": 213,
                "thumbnails": [
                    {"url": "https://small.jpg", "width": 60, "height": 60},
                    {"url": "https://large.jpg", "width": 544, "height": 544},
                ],
            },
        ),
    ],
    ids=["album-none", "album-key-absent"],
)
def test_search_album_is_none_when_missing(build_raw):
    (factory,) = build_raw
    stub = _StubYTMusic([factory()])
    service = SearchService(client=stub)

    mapped = service.search("any query")

    assert len(mapped) == 1
    assert mapped[0]["album"] is None


@pytest.mark.parametrize(
    "raw_items,expected_len",
    [
        (
            [_raw_song(), _raw_song(video_id="abc1234567A"), _raw_song(video_id="xyz9876543Z")],
            3,
        ),
        (
            [_raw_song(), _raw_song(video_id=None), _raw_song(video_id="xyz9876543Z")],
            2,
        ),
        (
            [_raw_song(video_id=None), _raw_song(video_id=None), _raw_song(video_id=None)],
            0,
        ),
    ],
    ids=["all-present", "one-missing", "all-missing"],
)
def test_search_skips_items_missing_videoId(raw_items, expected_len):
    stub = _StubYTMusic(raw_items)
    service = SearchService(client=stub)

    mapped = service.search("any query")

    assert len(mapped) == expected_len


@pytest.mark.parametrize(
    "query,limit",
    [
        ("wish you were here", 10),
        ("bohemian rhapsody", 5),
    ],
    ids=["wish-10", "bohemian-5"],
)
def test_search_passes_filter_songs_and_limit_to_client(query, limit):
    stub = _StubYTMusic([_raw_song()])
    service = SearchService(client=stub)

    service.search(query, limit)

    assert stub.calls == [(query, "songs", limit)]


@pytest.mark.parametrize(
    "query,limit",
    [
        ("x", 10),
    ],
    ids=["same-args"],
)
def test_search_caches_repeat_calls_with_same_args(query, limit):
    stub = _StubYTMusic([_raw_song()])
    service = SearchService(client=stub)

    service.search(query, limit)
    service.search(query, limit)
    service.search(query, limit)

    assert len(stub.calls) == 1


@pytest.mark.parametrize(
    "call_sequence,expected_call_count",
    [
        ([("pink floyd", 10), ("led zeppelin", 10)], 2),
        ([("pink floyd", 10), ("pink floyd", 5)], 2),
        ([("pink floyd", 10), ("led zeppelin", 10), ("rolling stones", 5)], 3),
    ],
    ids=["diff-query", "diff-limit", "three-distinct"],
)
def test_search_does_not_cache_when_args_differ(call_sequence, expected_call_count):
    stub = _StubYTMusic([_raw_song()])
    service = SearchService(client=stub)

    for q, lim in call_sequence:
        service.search(q, lim)

    assert len(stub.calls) == expected_call_count


@pytest.mark.parametrize(
    "query,limit",
    [
        ("q", 10),
    ],
    ids=["identity-on-hit"],
)
def test_search_returns_same_list_object_on_cache_hit(query, limit):
    stub = _StubYTMusic([_raw_song()])
    service = SearchService(client=stub)

    first = service.search(query, limit)
    second = service.search(query, limit)

    assert first is second


@pytest.mark.parametrize(
    "ttl_seconds,maxsize",
    [
        (1, 4),
    ],
    ids=["custom-cache-config"],
)
def test_construct_with_explicit_ttl_and_maxsize(ttl_seconds, maxsize):
    stub = _StubYTMusic([_raw_song()])
    service = SearchService(client=stub, ttl_seconds=ttl_seconds, maxsize=maxsize)

    result = service.search("any query")

    assert isinstance(result, list)


@pytest.mark.parametrize(
    "raw_count,limit,expected_len",
    [
        (20, 10, 10),  # ytmusicapi-style: returns 20 regardless of limit; we trim to 10
        (20, 5, 5),
        (20, 20, 20),  # limit at upstream cap — no trim needed
        (3, 10, 3),  # upstream returns fewer than limit — no trim
    ],
    ids=["raw20-cap10", "raw20-cap5", "raw20-cap20", "raw3-cap10"],
)
def test_search_trims_results_to_requested_limit(raw_count, limit, expected_len):
    # Defensive: ytmusicapi v1.12.1 ignores `limit` and returns 20 unconditionally.
    # SearchService must enforce the limit so callers get at most `limit` results.
    raw_items = [_raw_song(video_id=f"v{i:010d}") for i in range(raw_count)]
    stub = _StubYTMusic(raw_items)
    service = SearchService(client=stub)

    mapped = service.search("anything", limit)

    assert len(mapped) == expected_len
