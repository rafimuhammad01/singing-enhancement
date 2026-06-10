from __future__ import annotations

import os
from collections.abc import Callable

import librosa
import numpy as np

from services.melody_service import _KRUMHANSL_MAJOR, _KRUMHANSL_MINOR, _NOTE_NAMES


class PreviewKeyService:
    """Estimate a song's key from a raw audio file via chroma + Krumhansl-Schmuckler.

    Unlike the melody-extraction path, this one doesn't need Demucs — it runs on
    the polyphonic preview MP3 directly. Target latency: 2-5s for a 30s clip.
    """

    def __init__(
        self,
        loader: Callable[..., tuple] = librosa.load,
        chroma_fn: Callable[..., np.ndarray] = librosa.feature.chroma_cqt,
    ) -> None:
        self._load = loader
        self._chroma = chroma_fn

    def estimate(self, input_path: str) -> str:
        """Return a key string like 'A major' / 'C minor', or '' if input is silent/missing."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"input_path not found: {input_path!r}")

        y, sr = self._load(input_path, sr=22050, mono=True)

        chroma = self._chroma(y=y, sr=sr)

        # Collapse time axis → 12-bin pitch-class energy profile
        profile = chroma.sum(axis=1)

        total = profile.sum()
        if total == 0:
            return ""

        profile = profile / total

        # Normalize K-S profiles for meaningful Pearson correlation
        major = np.asarray(_KRUMHANSL_MAJOR, dtype=float)
        minor = np.asarray(_KRUMHANSL_MINOR, dtype=float)
        major = major / major.sum()
        minor = minor / minor.sum()

        best_corr = float("-inf")
        best_root = 0
        best_mode = "major"

        for root in range(12):
            rotated = np.roll(profile, -root)

            corr_major = float(np.corrcoef(rotated, major)[0, 1])
            if np.isnan(corr_major):
                corr_major = float("-inf")

            corr_minor = float(np.corrcoef(rotated, minor)[0, 1])
            if np.isnan(corr_minor):
                corr_minor = float("-inf")

            if corr_major > best_corr:
                best_corr = corr_major
                best_root = root
                best_mode = "major"

            if corr_minor > best_corr:
                best_corr = corr_minor
                best_root = root
                best_mode = "minor"

        return f"{_NOTE_NAMES[best_root]} {best_mode}"
