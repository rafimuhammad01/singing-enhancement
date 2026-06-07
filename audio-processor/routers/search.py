from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from ytmusicapi import YTMusic

from services.ytmusic_service import SearchService


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=10, ge=1, le=20)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_offset_plus_limit(self) -> "SearchRequest":
        if self.offset + self.limit > 100:
            raise ValueError("offset + limit must be <= 100")
        return self


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Singleton SearchService backed by a real ytmusicapi client.
    Tests override this via app.dependency_overrides."""
    return SearchService(client=YTMusic())


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]

router = APIRouter()


@router.post("/search")
def search(req: SearchRequest, service: SearchServiceDep) -> dict[str, Any]:
    items, has_more = service.search(req.query, req.limit, req.offset)
    return {"items": items, "has_more": has_more}
