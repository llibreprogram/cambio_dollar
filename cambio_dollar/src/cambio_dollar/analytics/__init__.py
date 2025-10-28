from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import math
from statistics import fmean, median, pstdev
from typing import Iterable, Optional

from zoneinfo import ZoneInfo

from ..config import Settings, get_settings
from ..models import (
    AnomalyEvent,
    AnomalySeverity,
    ConsensusSnapshot,
    ProviderReliabilityMetrics,
    RateSnapshot,
    Trade,
)
from ..repository import MarketRepository
from .drift import DriftMonitor, DriftSignal
from .technical_analysis import (
    CorrelationAnalysis,
    RiskMetrics,
    TechnicalAnalyzer,
    TechnicalIndicators,
)

__all__ = [
    "ProfitSnapshot",
    "PerformanceAnalyzer",
    "ProviderReliabilityAggregator",
    "ProviderWeightCalculator",
    "ZScoreAnomalyDetector",
    "DriftMonitor",
    "DriftSignal",
    "TechnicalAnalyzer",
    "TechnicalIndicators",
    "RiskMetrics",
    "CorrelationAnalysis",
]


@dataclass
class ProfitSnapshot:
    generated_at: datetime
    realized_profit: float
    open_rate: Optional[RateSnapshot]
    total_trades: int


class PerformanceAnalyzer:
    """Calcula indicadores clave de las operaciones realizadas."""

    def __init__(self, repository: MarketRepository, settings: Optional[Settings] = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self._timezone = ZoneInfo(self.settings.timezone)

    def summarize_day(self, *, reference: Optional[datetime] = None) -> ProfitSnapshot:
        now = (reference or datetime.now(tz=self._timezone)).astimezone(self._timezone)
        start_of_day = datetime.combine(now.date(), time.min, tzinfo=self._timezone)
        realized = self.repository.get_profit_summary(since=start_of_day)
        latest = self.repository.get_latest_snapshot()
        trades = self.repository.list_trades()
        return ProfitSnapshot(
            generated_at=now,
            realized_profit=realized,
            open_rate=latest,
            total_trades=len(trades),
        )


class ProviderReliabilityAggregator:
    """Calcula métricas agregadas de confiabilidad por proveedor."""

    def __init__(
        self,
        repository: MarketRepository,
        settings: Optional[Settings] = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self._timezone = ZoneInfo(self.settings.timezone)

    def compute(
        self,
        *,
        window_minutes: int = 180,
        reference: Optional[datetime] = None,
        include_disabled: bool = False,
    ) -> list[ProviderReliabilityMetrics]:
        window_end = (reference or datetime.now(tz=self._timezone)).astimezone(self._timezone)
        window_start = window_end - timedelta(minutes=window_minutes)
        duration_seconds = max((window_end - window_start).total_seconds(), 1.0)
        scheduler_interval = max(self.settings.scheduler_interval_seconds, 1)
        expected_captures = max(1, math.ceil(duration_seconds / scheduler_interval))

        records: list[ProviderReliabilityMetrics] = []
        providers = self.settings.providers if include_disabled else [p for p in self.settings.providers if p.enabled]

        for provider in providers:
            metrics = self.repository.list_provider_metrics(
                provider=provider.name,
                since=window_start,
                until=window_end,
            )
            attempts = len(metrics)
            captures = sum(1 for metric in metrics if metric.success)
            failure_count = attempts - captures

            latencies = [metric.latency_ms for metric in metrics if metric.latency_ms is not None]
            retries = sum(metric.retries for metric in metrics)
            avg_attempts = fmean([metric.attempts for metric in metrics]) if metrics else 0.0

            status_counter = Counter()
            error_counter = Counter()
            for metric in metrics:
                status_key = str(metric.status_code) if metric.status_code is not None else "none"
                status_counter[status_key] += 1
                if metric.error:
                    error_counter[metric.error] += 1

            mean_latency = fmean(latencies) if latencies else None
            latency_p50 = median(latencies) if latencies else None
            latency_p95 = self._percentile(latencies, 0.95)

            success_ratio = captures / attempts if attempts else 0.0
            coverage_ratio = captures / expected_captures if expected_captures else 0.0
            coverage_ratio = min(coverage_ratio, 1.0)

            error_samples = self.repository.list_provider_error_samples(
                provider=provider.name,
                since=window_start,
                until=window_end,
            )
            deltas = [
                sample.delta_vs_weighted
                if sample.delta_vs_weighted is not None
                else sample.delta_vs_consensus
                for sample in error_samples
                if sample.delta_vs_weighted is not None or sample.delta_vs_consensus is not None
            ]
            mean_error = fmean(deltas) if deltas else None
            std_error = pstdev(deltas) if len(deltas) > 1 else (0.0 if deltas else None)

            metadata: dict[str, object] = {
                "status_codes": dict(status_counter),
                "error_samples": [error for error, _count in error_counter.most_common(5)],
                "total_retries": retries,
                "average_attempts": avg_attempts,
                "window_minutes": window_minutes,
                "pricing_error_sample_count": len(deltas),
            }
            if not metrics:
                metadata.setdefault("notes", []).append("sin datos en la ventana")

            record = ProviderReliabilityMetrics(
                provider=provider.name,
                window_start=window_start,
                window_end=window_end,
                captures=captures,
                attempts=attempts,
                expected_captures=expected_captures,
                coverage_ratio=coverage_ratio,
                success_ratio=success_ratio,
                mean_latency_ms=mean_latency,
                latency_p50_ms=latency_p50,
                latency_p95_ms=latency_p95,
                mean_error=mean_error,
                std_error=std_error,
                failure_count=failure_count,
                metadata=metadata,
                created_at=datetime.now(tz=timezone.utc),
            )
            records.append(record)

        return records

    def compute_and_store(
        self,
        *,
        window_minutes: int = 180,
        reference: Optional[datetime] = None,
        include_disabled: bool = False,
    ) -> list[ProviderReliabilityMetrics]:
        records = self.compute(
            window_minutes=window_minutes,
            reference=reference,
            include_disabled=include_disabled,
        )
        self.repository.save_provider_reliability_metrics(records)
        return records

    @staticmethod
    def _percentile(values: list[float], quantile: float) -> Optional[float]:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        index = (len(ordered) - 1) * quantile
        lower = math.floor(index)
        upper = math.ceil(index)
        if lower == upper:
            return ordered[int(index)]
        lower_value = ordered[lower]
        upper_value = ordered[upper]
        return lower_value + (upper_value - lower_value) * (index - lower)


class ProviderWeightCalculator:
    """Deriva pesos dinámicos para cada proveedor en función de sus métricas recientes."""

    def __init__(
        self,
        repository: MarketRepository,
        settings: Optional[Settings] = None,
    ) -> None:
        self.repository = repository
        self.settings = settings or get_settings()
        self._aggregator = ProviderReliabilityAggregator(repository, self.settings)

    def compute(
        self,
        providers: Iterable[str],
        *,
        reference: Optional[datetime] = None,
    ) -> dict[str, float]:
        provider_list = list(dict.fromkeys(providers))
        if not provider_list:
            return {}

        window = max(self.settings.weight_window_minutes, 30)
        records = self._aggregator.compute(
            window_minutes=window,
            reference=reference,
            include_disabled=True,
        )
        record_map = {record.provider: record for record in records}

        scores = {
            provider: self._score(record_map.get(provider))
            for provider in provider_list
        }
        max_score = max(scores.values()) if scores else 0.0
        exp_scores = {provider: math.exp(score - max_score) for provider, score in scores.items()}
        total = sum(exp_scores.values())
        if total <= 0:
            equal_weight = 1.0 / len(provider_list)
            return {provider: equal_weight for provider in provider_list}

        normalized = {provider: score / total for provider, score in exp_scores.items()}
        floor = self.settings.weight_floor
        if floor <= 0:
            return normalized

        floor = min(max(floor, 0.0), 0.5)
        base_allocation = floor * len(provider_list)
        if base_allocation >= 1.0:
            equal_weight = 1.0 / len(provider_list)
            return {provider: equal_weight for provider in provider_list}

        residual = 1.0 - base_allocation
        floored = {provider: floor for provider in provider_list}
        for provider, weight in normalized.items():
            floored[provider] += weight * residual
        # Normaliza por precaución para contrarrestar errores numéricos.
        total_floored = sum(floored.values())
        return {provider: weight / total_floored for provider, weight in floored.items()}

    def _score(self, record: Optional[ProviderReliabilityMetrics]) -> float:
        baseline = self.settings.weight_baseline_score
        if record is None:
            return baseline

        coverage = self._clamp(record.coverage_ratio)
        success = self._clamp(record.success_ratio)
        latency_score = self._latency_score(record)
        error_penalty = self._error_penalty(record)

        return (
            self.settings.weight_alpha * coverage
            + self.settings.weight_beta * success
            + self.settings.weight_gamma * latency_score
            - self.settings.weight_delta * error_penalty
        )

    @staticmethod
    def _clamp(value: Optional[float]) -> float:
        if value is None:
            return 0.0
        return max(0.0, min(1.0, value))

    def _latency_score(self, record: ProviderReliabilityMetrics) -> float:
        cap = max(self.settings.weight_latency_cap_ms, 1.0)
        latency = record.latency_p95_ms or record.mean_latency_ms
        if latency is None:
            return 1.0
        ratio = min(latency, cap) / cap
        return max(0.0, 1.0 - ratio)

    def _error_penalty(self, record: ProviderReliabilityMetrics) -> float:
        cap = max(self.settings.weight_error_cap, 1e-3)
        error = abs(record.mean_error or 0.0)
        return min(error, cap) / cap


class ZScoreAnomalyDetector:
    """Detector robusto basado en z-score utilizando mediana y MAD."""

    _MAD_SCALE = 1.4826  # Factor para aproximar la desviación estándar
    _MIN_SCALE = 1e-6

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def detect(self, consensus: ConsensusSnapshot) -> list[AnomalyEvent]:
        if len(consensus.validations) < self.settings.anomaly_min_providers:
            return []

        deltas = [
            validation.delta_vs_weighted
            if validation.delta_vs_weighted is not None
            else validation.delta_vs_consensus
            for validation in consensus.validations
        ]
        filtered = [delta for delta in deltas if delta is not None]
        if not filtered:
            return []

        median_delta = median(filtered)
        deviations = [abs(delta - median_delta) for delta in filtered]
        mad = median(deviations)
        mad_scaled = mad * self._MAD_SCALE
        scale = max(mad_scaled, self._MIN_SCALE)

        events: list[AnomalyEvent] = []
        threshold = self.settings.anomaly_z_threshold
        critical_delta = self.settings.anomaly_critical_deviation
        timestamp = consensus.timestamp

        for validation in consensus.validations:
            delta = validation.delta_vs_weighted
            if delta is None:
                delta = validation.delta_vs_consensus
            if delta is None:
                continue
            diff = delta - median_delta
            if mad_scaled < self._MIN_SCALE and abs(delta) < critical_delta:
                # Sin variabilidad suficiente y la desviación es pequeña: ignora.
                continue
            z_score = diff / scale
            score = abs(z_score)
            if score < threshold:
                continue

            severity = AnomalySeverity.WARN
            if abs(delta) >= critical_delta:
                severity = AnomalySeverity.CRITICAL

            context: dict[str, float | str | None] = {
                "delta": float(delta),
                "median_delta": float(median_delta),
                "z_score": float(z_score),
                "weight": validation.weight,
                "difference_abs": validation.difference_vs_weighted or validation.difference_vs_consensus,
            }

            events.append(
                AnomalyEvent(
                    timestamp=timestamp,
                    provider=validation.provider,
                    metric="mid_rate",
                    detector="zscore_mad",
                    score=score,
                    severity=severity,
                    context=context,
                )
            )

        return events
