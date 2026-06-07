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
        self.calls: list[tuple[str, str, int, bool]] = []  # (query, filter, limit, ignore_spelling)

    def search(
        self,
        query: str,
        filter: str,
        limit: int,
        ignore_spelling: bool = False,
    ) -> list[dict[str, Any]]:
        self.calls.append((query, filter, limit, ignore_spelling))
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

    mapped, _ = service.search("rick astley")

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

    mapped, _ = service.search("any query")

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

    mapped, _ = service.search("any query")

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

    mapped, _ = service.search("any query")

    assert len(mapped) == expected_len


@pytest.mark.parametrize(
    "query,limit",
    [
        ("wish you were here", 10),
        ("bohemian rhapsody", 5),
    ],
    ids=["wish-10", "bohemian-5"],
)
def test_search_passes_filter_limit_and_ignore_spelling_to_client(query, limit):
    stub = _StubYTMusic([_raw_song()])
    service = SearchService(client=stub)

    service.search(query, limit, 0)

    assert stub.calls == [(query, "songs", limit, True)]


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

    service.search(query, limit, 0)
    service.search(query, limit, 0)
    service.search(query, limit, 0)

    assert len(stub.calls) == 1


@pytest.mark.parametrize(
    "call_sequence,expected_upstream_call_count",
    [
        # Different queries always miss
        ([("pink floyd", 10, 0), ("led zeppelin", 10, 0)], 2),
        # Same query, same args = cache hit
        ([("pink floyd", 10, 0), ("pink floyd", 10, 0)], 1),
        # Same query, smaller need = cache hit (cache has enough)
        ([("pink floyd", 10, 0), ("pink floyd", 5, 0)], 1),
        # Same query, second need <= cache size = cache hit
        # (cache holds 20 items after first call even when we only asked for 5)
        ([("pink floyd", 5, 0), ("pink floyd", 10, 0)], 1),
        # Same query, second need > cache size, not exhausted = refetch
        ([("pink floyd", 5, 0), ("pink floyd", 10, 15)], 2),
    ],
    ids=[
        "different-queries-always-fetch",
        "same-query-same-args-cached",
        "same-query-smaller-need-cached",
        "same-query-second-need-within-cache",
        "same-query-second-need-exceeds-cache",
    ],
)
def test_cache_behavior_by_query_and_size(call_sequence, expected_upstream_call_count):
    # The stub returns 20 raw items for any call (matching ytmusicapi's batch overshoot).
    # That means cache will hold up to 20 mapped items after first fetch.
    stub = _StubYTMusic([_raw_song(video_id=f"v{i:010d}") for i in range(20)])
    service = SearchService(client=stub)

    for q, lim, off in call_sequence:
        service.search(q, lim, off)

    assert len(stub.calls) == expected_upstream_call_count


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

    result, has_more = service.search("any query")

    assert isinstance(result, list)
    assert isinstance(has_more, bool)


@pytest.mark.parametrize(
    "title,want_kept",
    [
        # Clean studio titles — KEEP
        ("Fake Plastic Trees", True),
        ("Bohemian Rhapsody", True),
        ("Live Forever", True),  # word in title, not parens
        ("Live and Let Die", True),
        ("Discover", True),  # 'cover' as substring
        ("Undercover", True),
        ("Aliveness (Studio Version)", True),  # substring inside word + no keyword
        ("Fake Plastic Trees (feat. Jeff Hall)", True),  # feat. is not a non-studio marker
        ("Bohemian Rhapsody (Remastered 2011)", True),  # remaster not in list
        ("Strobe (Original Mix)", True),  # 'mix' not in list
        # Parenthetical non-studio markers — DROP
        ("Fake Plastic Trees (2 Meter Session)", False),
        ("Wonderwall (Live at Wembley)", False),
        ("Wonderwall [Live]", False),  # brackets too
        ("Creep (Acoustic Version)", False),
        ("Heart-Shaped Box (MTV Unplugged)", False),
        ("Wonderwall (Karaoke Version)", False),
        ("Songbird (Demo)", False),
        ("Random Track (Bootleg)", False),
        ("Bad Habit (Khruangbin Remix)", False),
        ("Some Song (Acoustic Cover)", False),  # both 'acoustic' and 'cover' present
        ("Crazy Train (Instrumental)", False),
        ("Track Title (LIVE)", False),  # uppercase
        ("Track Title (live in tokyo 1992)", False),  # mixed words
    ],
    ids=[
        "plain",
        "plain-bohemian",
        "live-at-title-start",
        "live-and-let-die",
        "discover-substring",
        "undercover-substring",
        "aliveness-substring",
        "feat-collab",
        "remastered",
        "original-mix",
        "session-paren",
        "live-paren",
        "live-bracket",
        "acoustic-paren",
        "unplugged-paren",
        "karaoke-paren",
        "demo-paren",
        "bootleg-paren",
        "remix-paren",
        "acoustic-cover-paren",
        "instrumental-paren",
        "uppercase-live",
        "live-mixed-words",
    ],
)
def test_search_filters_non_studio_titles(title, want_kept):
    # SearchService drops items whose title contains live/session/acoustic/unplugged/
    # karaoke/demo/bootleg/remix/cover/instrumental as a whole word inside () or [].
    stub = _StubYTMusic([_raw_song(title=title)])
    service = SearchService(client=stub)

    mapped, _ = service.search("any query")

    expected_len = 1 if want_kept else 0
    assert len(mapped) == expected_len


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

    mapped, _ = service.search("anything", limit)

    assert len(mapped) == expected_len


@pytest.mark.parametrize(
    "limit,offset,raw_count,expected_first_id,expected_len",
    [
        # 20 raw items, page 1 of 10
        (10, 0, 20, "v0000000000", 10),
        # 20 raw items, page 2 of 10
        (10, 10, 20, "v0000000010", 10),
        # 20 raw items, page of 5 starting at 15
        (5, 15, 20, "v0000000015", 5),
        # 20 raw items, offset past end = empty page
        (10, 20, 20, None, 0),
        # 20 raw items, offset partially past end
        (10, 18, 20, "v0000000018", 2),
    ],
    ids=[
        "page-1-of-10",
        "page-2-of-10",
        "page-of-5-at-15",
        "offset-past-end-empty",
        "offset-partial-overlap",
    ],
)
def test_search_returns_offset_page(limit, offset, raw_count, expected_first_id, expected_len):
    raw = [_raw_song(video_id=f"v{i:010d}") for i in range(raw_count)]
    stub = _StubYTMusic(raw)
    service = SearchService(client=stub)

    items, _ = service.search("anything", limit, offset)

    assert len(items) == expected_len
    if expected_first_id is not None:
        assert items[0]["videoId"] == expected_first_id


@pytest.mark.parametrize(
    "raw_count,limit,offset,want_has_more",
    [
        # 20 raw, requesting first 10 -> 10 more remain
        (20, 10, 0, True),
        # 20 raw, requesting last 10 -> nothing more
        (20, 10, 10, False),
        # 20 raw, requesting first 20 -> exact cap, nothing more
        (20, 20, 0, False),
        # 10 raw, requesting 10 -> exhausted
        (10, 10, 0, False),
        # 5 raw, requesting 10 -> fewer than requested
        (5, 10, 0, False),
    ],
    ids=[
        "20-raw-page1-more",
        "20-raw-page2-done",
        "20-raw-exact-cap",
        "10-raw-exact",
        "5-raw-undercaught",
    ],
)
def test_search_has_more_signals_remaining(raw_count, limit, offset, want_has_more):
    raw = [_raw_song(video_id=f"v{i:010d}") for i in range(raw_count)]
    stub = _StubYTMusic(raw)
    service = SearchService(client=stub)

    _, has_more = service.search("anything", limit, offset)

    assert has_more is want_has_more


@pytest.mark.parametrize(
    "rounds",
    [(2,), (3,)],
    ids=["two-rounds", "three-rounds"],
)
def test_search_exhausted_query_does_not_refetch(rounds):
    (n_calls,) = rounds
    # Upstream has only 5 items even though we ask for 10.
    raw = [_raw_song(video_id=f"v{i:010d}") for i in range(5)]
    stub = _StubYTMusic(raw)
    service = SearchService(client=stub)

    # First call requests need=10 but upstream returns 5 -> is_exhausted=True
    service.search("anything", limit=10, offset=0)
    # Subsequent calls with offsets that would EXCEED the cached count must NOT refetch
    for _ in range(n_calls - 1):
        service.search("anything", limit=10, offset=10)  # offset+limit=20 > cached=5

    assert len(stub.calls) == 1


@pytest.mark.parametrize(
    "limit,offset,expected_upstream_limit",
    [
        (10, 0, 10),
        (10, 20, 30),
        (5, 15, 20),
    ],
    ids=["page1", "page-far-out", "smaller-page-mid"],
)
def test_search_request_upstream_limit_covers_need(limit, offset, expected_upstream_limit):
    raw = [_raw_song(video_id=f"v{i:010d}") for i in range(50)]
    stub = _StubYTMusic(raw)
    service = SearchService(client=stub)

    service.search("anything", limit, offset)

    # Stub records (query, filter, limit, ignore_spelling) tuples
    assert stub.calls == [("anything", "songs", expected_upstream_limit, True)]
