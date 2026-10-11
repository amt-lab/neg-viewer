"""Image processing for the negative viewer. Independent of Qt.

`process_image()` is the function to experiment with: plain NumPy on float32 RGB in [0, 1].
`NegativeProcessor` wraps it with the plumbing: downscaling, uint8 BGR <-> float RGB,
and measuring the levels on a small copy every `meter_every` seconds (with light smoothing).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import cv2
import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)  # Rec. 709 weights for RGB


@dataclass
class Settings:
    invert: bool = True
    mono: bool = False
    lock: bool = False        # stop re-metering, keep the current levels
    clip_pct: float = 0.5     # % of pixels clipped at each end, per channel
    gamma: float = 1.0
    roi: tuple[float, float, float, float] | None = None  # (x0, y0, x1, y1) in 0..1; None = whole frame
    process_width: int = 960  # downscale to this width before processing; 0 = full resolution
    meter_every: float = 0.1  # seconds between level measurements
    meter_width: int = 160    # width of the copy used for metering


def measure_levels(x: np.ndarray, s: Settings) -> tuple[np.ndarray, np.ndarray]:
    """Per-channel black/white points (percentiles) of a small float RGB image, or of its ROI."""
    if s.roi:
        h, w = x.shape[:2]
        x0, y0, x1, y1 = s.roi
        c0, r0 = int(x0 * w), int(y0 * h)
        x = x[r0:max(r0 + 1, math.ceil(y1 * h)), c0:max(c0 + 1, math.ceil(x1 * w))]
    lo, hi = np.percentile(x.reshape(-1, 3), [s.clip_pct, 100 - s.clip_pct], axis=0)
    return lo, np.maximum(hi, lo + 0.015)  # avoid blowing up noise on a flat frame


def process_image(x: np.ndarray, s: Settings, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """float32 RGB [0, 1] in, float32 RGB out. lo/hi are the per-channel black/white points."""
    x = (x - lo.astype(np.float32)) / (hi - lo).astype(np.float32)  # normalise each channel
    np.clip(x, 0, 1, out=x)
    if s.invert:
        x = 1 - x
    if s.gamma != 1:
        x = np.power(x, np.float32(1 / s.gamma))
    if s.mono:
        x = np.repeat((x @ LUMA)[..., None], 3, axis=2)
    return x


class NegativeProcessor:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.lo = np.zeros(3)
        self.hi = np.ones(3)
        self._last_meter = -math.inf
        self._have_levels = False

    def process(self, frame_bgr: np.ndarray, width: int | None = None, meter: bool = True) -> np.ndarray:
        """uint8 BGR frame (as OpenCV delivers it) in, uint8 RGB out.

        width: processing width, default settings.process_width (0 = full resolution).
        """
        s = self.settings
        width = s.process_width if width is None else width
        h, w = frame_bgr.shape[:2]
        if width and w > width:
            frame_bgr = cv2.resize(frame_bgr, (width, round(h * width / w)), interpolation=cv2.INTER_AREA)
        x = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255

        now = time.monotonic()
        if meter and not s.lock and now - self._last_meter >= s.meter_every:
            self._meter(x)
            self._last_meter = now

        y = process_image(x, s, self.lo, self.hi)
        return (np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8)

    def _meter(self, x: np.ndarray) -> None:
        s = self.settings
        h, w = x.shape[:2]
        mw = min(s.meter_width, w)
        small = cv2.resize(x, (mw, max(1, round(h * mw / w))), interpolation=cv2.INTER_AREA)
        lo, hi = measure_levels(small, s)
        k = 0.35 if self._have_levels else 1.0  # light smoothing so levels don't flicker
        self.lo += k * (lo - self.lo)
        self.hi += k * (hi - self.hi)
        self._have_levels = True
