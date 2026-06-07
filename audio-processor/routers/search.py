from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ytmusicapi import YTMusic

from services.ytmusic_service import SearchService


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=20)


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Singleton SearchService backed by a real ytmusicapi client.
    Tests override this via app.dependency_overrides."""
    return SearchService(client=YTMusic())


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]

router = APIRouter()


@router.post("/search")
def search(req: SearchRequest, service: SearchServiceDep) -> list[dict[str, Any]]:
    return service.search(req.query, req.limit)
