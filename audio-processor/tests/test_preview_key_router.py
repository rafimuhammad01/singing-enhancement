from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.preview_key import get_preview_key_service

# ---------------------------------------------------------------------------
# Stub service
# ---------------------------------------------------------------------------


class _StubPreviewKeyService:
    """Records calls and optionally raises on estimate()."""

    def __init__(self, return_key: str = "A major", raise_exc: Exception | None = None) -> None:
        self.calls: list[str] = []
        self._return_key = return_key
        self._raise = raise_exc

    def estimate(self, input_path: str) -> str:
        self.calls.append(input_path)
        if self._raise is not None:
            raise self._raise
        return self._return_key


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_stub():
    """Yields (client, stub). Default stub returns 'A major'."""
    stub = _StubPreviewKeyService()
    app.dependency_overrides[get_preview_key_service] = lambda: stub
    try:
        yield TestClient(app), stub
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client_with_raising_stub():
    """Factory fixture — caller passes the exception to raise."""

    def _make(exc: Exception):
        stub = _StubPreviewKeyService(raise_exc=exc)
        app.dependency_overrides[get_preview_key_service] = lambda: stub
        return TestClient(app), stub

    try:
        yield _make
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_preview_key_happy_path(client_with_stub) -> None:
    """POST /preview-key with valid body → 200 with key 'A major'."""
    client, stub = client_with_stub

    response = client.post("/preview-key", json={"input_path": "/whatever"})

    assert response.status_code == 200
    assert response.json() == {"key": "A major"}
    assert stub.calls == ["/whatever"]


def test_preview_key_missing_required_fields_returns_422(client_with_stub) -> None:
    """Missing input_path → 422 (pydantic validation)."""
    client, stub = client_with_stub

    response = client.post("/preview-key", json={})

    assert response.status_code == 422
    assert stub.calls == []


def test_preview_key_empty_input_path_returns_422(client_with_stub) -> None:
    """Empty string input_path → 422 (min_length=1 constraint)."""
    client, stub = client_with_stub

    response = client.post("/preview-key", json={"input_path": ""})

    assert response.status_code == 422
    assert stub.calls == []


def test_preview_key_service_file_not_found_returns_404(client_with_raising_stub) -> None:
    """Service raises FileNotFoundError → 404 with 'input_path' in detail."""
    client, stub = client_with_raising_stub(FileNotFoundError("nope"))

    response = client.post("/preview-key", json={"input_path": "/missing.mp3"})

    assert response.status_code == 404
    assert "input_path" in response.json()["detail"].lower()


def test_preview_key_service_runtime_error_returns_500(client_with_raising_stub) -> None:
    """Service raises generic Exception → 500 with the error message in detail."""
    client, stub = client_with_raising_stub(Exception("librosa crashed"))

    response = client.post("/preview-key", json={"input_path": "/audio.mp3"})

    assert response.status_code == 500
    assert "librosa crashed" in response.json()["detail"]
