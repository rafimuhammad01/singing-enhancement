from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from services.preview_key_service import PreviewKeyService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# C major scale pitch-class indices (0-based, C=0): C D E F G A B
_C_MAJOR_PCS: list[int] = [0, 2, 4, 5, 7, 9, 11]
# A minor scale pitch-class indices: A B C D E F G
_A_MINOR_PCS: list[int] = [9, 11, 0, 2, 4, 5, 7]


def _make_chroma(bright_pcs: list[int], n_frames: int = 10) -> np.ndarray:
    """Return a 12 x n_frames chroma matrix with bright rows at *bright_pcs*.

    Bright rows get energy 1.0; all others get 0.1.
    """
    mat = np.full((12, n_frames), 0.1)
    for pc in bright_pcs:
        mat[pc, :] = 1.0
    return mat


def _make_loader(audio: np.ndarray, sr: int = 22050) -> Any:
    """Return a fake loader that returns (audio, sr) for any path."""

    def fake(path: str, **kwargs: object) -> tuple[np.ndarray, int]:
        return audio, sr

    return fake


def _make_chroma_fn(chroma: np.ndarray) -> Any:
    """Return a fake chroma_cqt that returns *chroma* regardless of input."""
    recorded: list[dict] = []

    def fake(y: np.ndarray, sr: int, **kwargs: object) -> np.ndarray:
        recorded.append({"sr": sr})
        return chroma

    fake._recorded = recorded  # type: ignore[attr-defined]
    return fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_estimate_pure_c_major_chroma_returns_c_major(tmp_path: Path) -> None:
    """Bright C-major pitch classes in chroma → 'C major'."""
    input_file = tmp_path / "input.mp3"
    input_file.write_bytes(b"fake")
    audio = np.ones(100)
    chroma = _make_chroma(_C_MAJOR_PCS)
    service = PreviewKeyService(
        loader=_make_loader(audio),
        chroma_fn=_make_chroma_fn(chroma),
    )

    result = service.estimate(str(input_file))

    assert result == "C major"


def test_estimate_pure_a_minor_chroma_returns_a_minor(tmp_path: Path) -> None:
    """A-minor tonic-stressed chroma pattern → 'A minor' (not relative C major).

    Double-weight A (index 9) and E (index 4) to stress the tonic/dominant and
    break the A-minor / C-major tie the same way test_melody_service does it.
    """
    input_file = tmp_path / "input.mp3"
    input_file.write_bytes(b"fake")
    chroma = _make_chroma(_A_MINOR_PCS)
    # Double the tonic (A=9) and dominant (E=4) rows to tip K-S toward A minor
    chroma[9, :] = 2.0
    chroma[4, :] = 1.5
    service = PreviewKeyService(
        loader=_make_loader(np.ones(100)),
        chroma_fn=_make_chroma_fn(chroma),
    )

    result = service.estimate(str(input_file))

    assert result == "A minor"


def test_estimate_silent_audio_returns_empty(tmp_path: Path) -> None:
    """All-zero chroma matrix → '' (silent/no tonal content)."""
    input_file = tmp_path / "silent.mp3"
    input_file.write_bytes(b"fake")
    chroma = np.zeros((12, 10))
    service = PreviewKeyService(
        loader=_make_loader(np.ones(100)),
        chroma_fn=_make_chroma_fn(chroma),
    )

    result = service.estimate(str(input_file))

    assert result == ""


def test_estimate_missing_input_raises_file_not_found() -> None:
    """Non-existent input_path → FileNotFoundError; neither loader nor chroma_fn called."""
    called: list[str] = []

    def should_not_run(*args: object, **kwargs: object) -> Any:
        called.append("called")
        raise AssertionError("should not be called")

    service = PreviewKeyService(loader=should_not_run, chroma_fn=should_not_run)

    with pytest.raises(FileNotFoundError):
        service.estimate("/nonexistent/path/audio.mp3")

    assert called == []


def test_estimate_chroma_function_called_with_sr_from_loader(tmp_path: Path) -> None:
    """chroma_fn must be called with the sr value returned by loader."""
    input_file = tmp_path / "input.mp3"
    input_file.write_bytes(b"fake")
    audio = np.ones(100)
    chroma = _make_chroma(_C_MAJOR_PCS)
    spy_chroma_fn = _make_chroma_fn(chroma)

    service = PreviewKeyService(
        loader=_make_loader(audio, sr=22050),
        chroma_fn=spy_chroma_fn,
    )
    service.estimate(str(input_file))

    assert spy_chroma_fn._recorded, "chroma_fn must have been called"  # type: ignore[attr-defined]
    assert spy_chroma_fn._recorded[0]["sr"] == 22050  # type: ignore[attr-defined]
