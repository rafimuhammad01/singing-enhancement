import re
from typing import Any

from cachetools import TTLCache

_NON_STUDIO_KEYWORDS = (
    "live|session|acoustic|unplugged|karaoke|demo|bootleg|remix|cover|instrumental"
)
_NON_STUDIO_RE = re.compile(
    rf"[\(\[][^)\]]*\b({_NON_STUDIO_KEYWORDS})\b[^)\]]*[\)\]]",
    re.IGNORECASE,
)


class SearchService:
    """Wraps a YTMusic-like client with song-filter search + TTL cache.

    Cache key: query string alone.
    Cache value: (mapped_list, is_exhausted) tuple.
    - mapped_list: all items fetched so far (full upstream response, filtered).
    - is_exhausted=True means upstream returned fewer items than we asked for
      on the last fetch, so asking again won't produce more results.

    Cache hit when len(mapped_list) >= offset+limit OR is_exhausted. We key
    the decision on the actual cached length, NOT what we requested upstream
    — ytmusicapi over-fetches (returns 20 per batch even when we ask for 5),
    so refetching with a slightly larger limit can return items in a
    different order, producing duplicates across pages.

    Returned page is a slice of the cache — safe for callers to mutate.
    """

    def __init__(self, client, ttl_seconds: int = 600, maxsize: int = 256) -> None:
        self._client = client
        self._cache: TTLCache[str, tuple[list[dict[str, Any]], bool]] = TTLCache(
            maxsize=maxsize, ttl=ttl_seconds
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Return (page_items, has_more).

        page_items is a new list slice — callers may mutate it safely.
        has_more indicates whether more items exist beyond offset+limit.
        """
        need = offset + limit

        cached_entry = self._cache.get(query)
        if cached_entry is not None:
            cached_list, is_exhausted = cached_entry
            if len(cached_list) >= need or is_exhausted:
                page = cached_list[offset : offset + limit]
                has_more = len(cached_list) > offset + limit
                return page, has_more

        raw = self._client.search(query, filter="songs", limit=need, ignore_spelling=True)
        is_exhausted = len(raw) < need
        mapped = [
            self._map_item(item)
            for item in raw
            if "videoId" in item and self._is_studio(item.get("title", ""))
        ]
        self._cache[query] = (mapped, is_exhausted)

        page = mapped[offset : offset + limit]
        has_more = len(mapped) > offset + limit
        return page, has_more

    @staticmethod
    def _is_studio(title: str) -> bool:
        return _NON_STUDIO_RE.search(title) is None

    @staticmethod
    def _map_item(raw: dict[str, Any]) -> dict[str, Any]:
        album = raw.get("album")
        album_name = album["name"] if album else None
        return {
            "videoId": raw["videoId"],
            "title": raw["title"],
            "artist": ", ".join(a["name"] for a in raw["artists"]),
            "album": album_name,
            "duration_sec": raw["duration_seconds"],
            "thumbnail_url": raw["thumbnails"][-1]["url"],
        }
