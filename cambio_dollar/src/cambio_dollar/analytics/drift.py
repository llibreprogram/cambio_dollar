from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from ..config import Settings, get_settings


@dataclass(slots=True)
class DriftSignal:
    """Representa la salida de un monitor de drift."""

    timestamp: datetime
    ewma: float
    cusum_pos: float
    cusum_neg: float
    threshold: float
    drift_detected: bool
    direction: str | None = None
    severity: str | None = None
    intensity: float | None = None
    details: dict[str, float | int | str] | None = None


class DriftMonitor:
    """Detector de drift basado en EWMA + CUSUM."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._ewma: Optional[float] = None
        self._cusum_pos = 0.0
        self._cusum_neg = 0.0
        self._cooldown_remaining = 0

    def reset(self) -> None:
        """Reinicia el estado interno del monitor."""

        self._ewma = None
        self._cusum_pos = 0.0
        self._cusum_neg = 0.0
        self._cooldown_remaining = 0

    def process(self, series: Iterable[tuple[datetime, float]]) -> list[DriftSignal]:
        """Evalúa una serie temporal (timestamp, mid_rate)."""

        signals: list[DriftSignal] = []
        for timestamp, value in sorted(series, key=lambda row: row[0]):
            signal = self._update(timestamp, value)
            signals.append(signal)
        return signals

    def update(self, timestamp: datetime, value: float) -> DriftSignal:
        """Procesa un único punto de datos y retorna el estado actual."""

        return self._update(timestamp, value)

    def _update(self, timestamp: datetime, value: float) -> DriftSignal:
        lambda_ = self.settings.drift_ewma_lambda
        threshold = self.settings.drift_cusum_threshold
        drift_cooldown = max(self.settings.drift_cooldown_captures, 0)

        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1

        if self._ewma is None:
            self._ewma = value
            self._cusum_pos = 0.0
            self._cusum_neg = 0.0
            return DriftSignal(
                timestamp=timestamp,
                ewma=value,
                cusum_pos=0.0,
                cusum_neg=0.0,
                threshold=threshold,
                drift_detected=False,
                details={"cooldown_remaining": self._cooldown_remaining},
            )

        prev_ewma = self._ewma
        ewma = lambda_ * value + (1 - lambda_) * prev_ewma
        diff = value - ewma

        self._cusum_pos = max(0.0, self._cusum_pos + diff - self.settings.drift_cusum_drift)
        self._cusum_neg = max(0.0, self._cusum_neg - diff - self.settings.drift_cusum_drift)

        direction: str | None = None
        drift_detected = False
        severity: str | None = None
        intensity: float | None = None

        if self._cusum_pos > threshold and self._cooldown_remaining == 0:
            drift_detected = True
            direction = "up"
            magnitude = self._cusum_pos
            if drift_cooldown > 0:
                self._cooldown_remaining = drift_cooldown
                self._cusum_pos /= 2
        elif self._cusum_neg > threshold and self._cooldown_remaining == 0:
            drift_detected = True
            direction = "down"
            magnitude = self._cusum_neg
            if drift_cooldown > 0:
                self._cooldown_remaining = drift_cooldown
                self._cusum_neg /= 2
        else:
            magnitude = 0.0

        self._ewma = ewma

        if drift_detected:
            safe_threshold = threshold if threshold > 0 else 1.0
            intensity = max(magnitude, 0.0) / safe_threshold
            if intensity >= 3:
                severity = "HIGH"
            elif intensity >= 1.75:
                severity = "MEDIUM"
            else:
                severity = "LOW"

        details: dict[str, float | int | str] = {
            "value": value,
            "ewma": ewma,
            "diff": diff,
            "threshold": threshold,
            "cusum_pos": self._cusum_pos,
            "cusum_neg": self._cusum_neg,
            "cooldown_remaining": self._cooldown_remaining,
        }
        if intensity is not None:
            details["intensity"] = intensity
        if severity is not None:
            details["severity"] = severity

        return DriftSignal(
            timestamp=timestamp,
            ewma=ewma,
            cusum_pos=self._cusum_pos,
            cusum_neg=self._cusum_neg,
            threshold=threshold,
            drift_detected=drift_detected,
            direction=direction,
            severity=severity,
            intensity=intensity,
            details=details,
        )
