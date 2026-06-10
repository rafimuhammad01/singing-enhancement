from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.preview_key_service import PreviewKeyService


class PreviewKeyRequest(BaseModel):
    input_path: str = Field(min_length=1)


class PreviewKeyResponse(BaseModel):
    key: str


@lru_cache(maxsize=1)
def get_preview_key_service() -> PreviewKeyService:
    """Singleton PreviewKeyService. Tests override via app.dependency_overrides."""
    return PreviewKeyService()


PreviewKeyServiceDep = Annotated[PreviewKeyService, Depends(get_preview_key_service)]
router = APIRouter()


@router.post("/preview-key", response_model=PreviewKeyResponse)
def preview_key(req: PreviewKeyRequest, service: PreviewKeyServiceDep) -> PreviewKeyResponse:
    """Estimate the musical key of a preview audio file."""
    try:
        key = service.estimate(req.input_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="input_path not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return PreviewKeyResponse(key=key)
