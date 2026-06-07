from typing import Any

from cachetools import TTLCache


class SearchService:
    """Wraps a YTMusic-like client with song-filter search + TTL cache.

    The cached list object is returned by reference on hits — callers must
    not mutate the returned list (it's the same object the next caller sees).
    """

    def __init__(self, client, ttl_seconds: int = 600, maxsize: int = 256) -> None:
        self._client = client
        self._cache: TTLCache[tuple[str, int], list[dict[str, Any]]] = TTLCache(
            maxsize=maxsize, ttl=ttl_seconds
        )

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        key = (query, limit)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        raw = self._client.search(query, filter="songs", limit=limit)
        mapped = [self._map_item(item) for item in raw if "videoId" in item]
        # ytmusicapi v1.12.1 ignores `limit` and returns 20 regardless; trim defensively.
        # Remove this slice when upstream honors limit.
        mapped = mapped[:limit]
        self._cache[key] = mapped
        return mapped

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
