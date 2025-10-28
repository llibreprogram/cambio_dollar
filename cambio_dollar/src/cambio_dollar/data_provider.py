# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import logging
import os
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable, List, Optional

import httpx
from selectolax.parser import HTMLParser, Node
from zoneinfo import ZoneInfo

from .analytics import ProviderWeightCalculator, ZScoreAnomalyDetector
from .analytics.drift import DriftMonitor
from .config import ProviderSettings, Settings, get_settings
from .models import (
    ConsensusSnapshot,
    ConsensusSnapshotRecord,
    DriftDirection,
    DriftEvent,
    DriftSeverity,
    ProviderErrorSample,
    ProviderFetchMetric,
    ProviderValidation,
    RateSnapshot,
)

logger = logging.getLogger(__name__)


_SELECTOR_PATTERN = re.compile(r"^(?P<key>[^\[]+)?(?:\[(?P<selector>[^\]]*)\])?$")


def _extract_from_path(data: dict[str, Any], path: Optional[str]) -> Optional[float]:
    if path is None:
        return None
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict):
            match = _SELECTOR_PATTERN.match(part)
            if not match:
                return None
            key = match.group("key") or ""
            selector = match.group("selector")
            if key:
                current = current.get(key)
            if selector:
                current = _apply_selector(current, selector)
        elif isinstance(current, list):
            current = _select_from_sequence(current, part)
        else:
            return None
    if isinstance(current, (int, float)):
        return float(current)
    if isinstance(current, str):
        try:
            return float(current)
        except ValueError:
            return None
    return None


def _apply_selector(current: Any, selector: str) -> Any:
    if current is None:
        return None
    if isinstance(current, list):
        selector = selector.strip()
        if selector.isdigit() or (selector.startswith("-") and selector[1:].isdigit()):
            index = int(selector)
            if index < 0:
                index += len(current)
            if 0 <= index < len(current):
                return current[index]
            return None
        key, _, value = selector.partition("=")
        key = key.strip()
        value = value.strip()
        for item in current:
            if isinstance(item, dict) and str(item.get(key)) == value:
                return item
        return None
    if isinstance(current, dict):
        return current.get(selector)
    return None


def _select_from_sequence(sequence: list[Any], token: str) -> Any:
    token = token.strip()
    if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
        index = int(token)
        if index < 0:
            index += len(sequence)
        if 0 <= index < len(sequence):
            return sequence[index]
    return None


def _safe_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    return {"value": metadata}


@dataclass(slots=True)
class ProviderFetchResult:
    provider: ProviderSettings
    snapshots: list[RateSnapshot]
    raw_payload: Any

    @property
    def snapshot(self) -> RateSnapshot:
        if not self.snapshots:
            raise ValueError("El proveedor no devolvió snapshots válidos.")
        return self.snapshots[0]


class ExchangeRateClient:
    def __init__(self, settings: Settings, http_client: Optional[httpx.Client] = None) -> None:
        self.settings = settings
        self._timezone = ZoneInfo(settings.timezone)
        self._client = http_client or httpx.Client()
        self._owns_client = http_client is None
        self._oauth_cache: dict[tuple[str, Optional[str], Optional[str]], tuple[str, float]] = {}
        self._last_metrics: list[ProviderFetchMetric] = []

    def fetch_all(self) -> list[ProviderFetchResult]:
        results: list[ProviderFetchResult] = []
        metrics: list[ProviderFetchMetric] = []

        for provider in self.settings.providers:
            if not provider.enabled:
                continue

            metric = ProviderFetchMetric(
                timestamp=datetime.now(tz=self._timezone),
                provider=provider.name,
                latency_ms=None,
                status_code=None,
                success=False,
                attempts=1,
                retries=0,
                error=None,
                metadata={
                    "method": provider.method,
                    "timeout": provider.timeout,
                    "format": provider.format,
                },
            )
            capture_start = time.perf_counter()
            try:
                result = self._fetch_provider(provider, metric)
                results.append(result)
            except Exception as exc:  # noqa: BLE001 - se registra y se continúa
                metric.error = str(exc)
                logger.warning("Proveedor %s falló: %s", provider.name, exc)
            finally:
                if metric.latency_ms is None:
                    metric.latency_ms = (time.perf_counter() - capture_start) * 1000
                metric.timestamp = datetime.now(tz=self._timezone)
                metrics.append(metric)

        if not results:
            self._last_metrics = metrics
            raise RuntimeError("No se pudo obtener información de ningún proveedor.")

        self._last_metrics = metrics
        return results

    def consume_metrics(self) -> list[ProviderFetchMetric]:
        metrics, self._last_metrics = self._last_metrics, []
        return metrics

    def _fetch_provider(
        self,
        provider: ProviderSettings,
        metric: ProviderFetchMetric,
    ) -> ProviderFetchResult:
        if not provider.endpoint:
            metric.error = "Endpoint no configurado"
            metric.attempts = max(metric.attempts, 1)
            raise RuntimeError(f"El proveedor {provider.name} no tiene un endpoint configurado.")

        headers: dict[str, str] = {}
        for header_name, env_var in provider.auth_headers.items():
            headers[header_name] = self._require_env(env_var, f"header {header_name}")
        if provider.oauth_token_url:
            token = self._get_oauth_token(provider)
            headers["Authorization"] = f"Bearer {token}"
        if provider.auth_header and provider.auth_token_env:
            headers.setdefault(
                provider.auth_header,
                self._require_env(provider.auth_token_env, f"header {provider.auth_header}"),
            )

        metric.attempts = 0
        metric.retries = 0
        response: httpx.Response | None = None
        attempts = provider.max_retries + 1

        for attempt in range(attempts):
            metric.attempts += 1
            attempt_start = time.perf_counter()
            try:
                response = self._client.request(
                    provider.method,
                    provider.endpoint,
                    headers=headers or None,
                    timeout=provider.timeout,
                )
                metric.latency_ms = (time.perf_counter() - attempt_start) * 1000
                metric.status_code = response.status_code
            except httpx.RequestError as exc:
                metric.error = str(exc)
                if not provider.retry_on_timeout or attempt >= provider.max_retries:
                    raise
                logger.warning(
                    "Reintento %s/%s para %s debido a error de red: %s",
                    attempt + 1,
                    attempts,
                    provider.name,
                    exc,
                )
                metric.retries += 1
                self._sleep_backoff(provider, attempt)
                continue

            if response.status_code in provider.retry_status_codes and attempt < provider.max_retries:
                metric.error = f"HTTP {response.status_code}"
                metric.retries += 1
                logger.warning(
                    "Reintento %s/%s para %s por código HTTP %s",
                    attempt + 1,
                    attempts,
                    provider.name,
                    response.status_code,
                )
                self._sleep_backoff(provider, attempt)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                metric.error = str(exc)
                raise

            metric.success = True
            metric.error = None
            metric.retries = metric.attempts - 1
            break
        else:
            metric.error = metric.error or "Intentos agotados"
            raise RuntimeError(
                f"No se pudo obtener datos válidos de {provider.name} tras {attempts} intentos"
            )

        if response is None:
            metric.error = "Respuesta vacía"
            raise RuntimeError(f"No se obtuvo respuesta de {provider.name}")

        if provider.format == "html":
            payload = response.text
            snapshots = self._parse_html_table(provider, payload)
        else:
            payload = response.json()
            snapshots = self._parse_payload(provider, payload)

        metadata = _safe_metadata(metric.metadata)
        metadata["payload_type"] = "html" if provider.format == "html" else "json"
        metadata["snapshot_count"] = len(snapshots)
        metric.metadata = metadata

        return ProviderFetchResult(provider, snapshots, payload)

    def _parse_payload(self, provider: ProviderSettings, payload: dict[str, Any]) -> list[RateSnapshot]:
        buy_rate = _extract_from_path(payload, provider.buy_path)
        sell_rate = _extract_from_path(payload, provider.sell_path)
        mid_rate = _extract_from_path(payload, provider.mid_path)

        if mid_rate is not None:
            spread = max(provider.spread_adjust, 0.05)
            buy_rate = buy_rate or max(mid_rate - spread / 2, 0.0001)
            sell_rate = sell_rate or mid_rate + spread / 2

        if buy_rate is None or sell_rate is None:
            raise ValueError(
                f"El payload de {provider.name} no contiene tasas suficientes: {payload}"
            )

        timestamp = self._extract_timestamp(payload)
        confidence = 1.0
        return [
            RateSnapshot(
                timestamp=timestamp,
                buy_rate=float(buy_rate),
                sell_rate=float(sell_rate),
                source=provider.name,
                confidence=confidence,
            )
        ]

    def _parse_html_table(self, provider: ProviderSettings, html_content: str) -> list[RateSnapshot]:
        logger.debug("HTML content: %s", html_content)
        parser = HTMLParser(html_content)
        table = self._locate_rate_table(parser)
        if table is None:
            logger.warning("No se encontró tabla de tasas para %s", provider.name)
            return []

        snapshots: list[RateSnapshot] = []
        for row in table.css("tr"):
            cells = row.css("td")
            if len(cells) < 3:
                continue

            bank_name = cells[0].text(separator=" ", strip=True).strip()
            buy_text = cells[1].text(separator=" ", strip=True).strip()
            sell_text = cells[2].text(separator=" ", strip=True).strip()

            buy_rate = self._parse_price(buy_text)
            sell_rate = self._parse_price(sell_text)

            if not bank_name or buy_rate is None or sell_rate is None:
                continue

            snapshots.append(
                RateSnapshot(
                    timestamp=datetime.now(tz=self._timezone),
                    buy_rate=buy_rate,
                    sell_rate=sell_rate,
                    source=bank_name,
                    confidence=0.9,
                )
            )

        return snapshots

    def _locate_rate_table(self, parser: HTMLParser) -> Optional[Node]:
        candidates = ["table#Dolar", "table#dolar", "table[data-name='Dolar']", "table[data-name='dolar']"]
        for selector in candidates:
            node = parser.css_first(selector)
            if node is not None:
                return node
        return parser.css_first("table")

    @staticmethod
    def _parse_price(raw_text: str) -> Optional[float]:
        if not raw_text:
            return None
        # Eliminar símbolos de moneda
        cleaned = raw_text.replace("RD$", "").replace("US$", "").replace("$", "")
        # Extraer solo el primer número antes de cualquier símbolo '=' o variación
        # Ej: "$62.90 = $0.00" -> "62.90", "$63.10 $0.10" -> "63.10"
        if "=" in cleaned:
            cleaned = cleaned.split("=")[0].strip()
        # Buscar el primer número válido con regex
        match = re.search(r'(\d+[.,]\d+|\d+)', cleaned)
        if not match:
            return None
        cleaned = match.group(1)
        # Manejar formato con coma como decimal (ej: "62,90")
        if "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        # Eliminar comas como separadores de miles
        cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _require_env(self, var_name: Optional[str], description: str) -> str:
        if not var_name:
            raise RuntimeError(f"No se configuró la variable de entorno para {description}.")
        value = os.getenv(var_name)
        if not value:
            raise RuntimeError(
                f"La variable de entorno {var_name} requerida para {description} no está definida."
            )
        return value

    def _get_oauth_token(self, provider: ProviderSettings) -> str:
        if not provider.oauth_token_url:
            raise RuntimeError("El proveedor no tiene configurado un endpoint OAuth.")
        cache_key = (
            provider.oauth_token_url,
            provider.oauth_scope,
            provider.oauth_client_id_env,
        )
        now = time.time()
        cached = self._oauth_cache.get(cache_key)
        if cached:
            token, expires_at = cached
            if expires_at - now > 30:
                return token

        client_id = self._require_env(provider.oauth_client_id_env, "OAuth client_id")
        client_secret = self._require_env(provider.oauth_client_secret_env, "OAuth client_secret")
        data = {"grant_type": "client_credentials"}
        if provider.oauth_scope:
            data["scope"] = provider.oauth_scope
        if provider.oauth_audience:
            data["audience"] = provider.oauth_audience

        response = self._client.post(
            provider.oauth_token_url,
            data=data,
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=provider.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("El endpoint OAuth no devolvió un access_token válido.")
        expires_in = float(payload.get("expires_in", 300))
        expires_at = now + max(expires_in - 30, 0)
        self._oauth_cache[cache_key] = (token, expires_at)
        return token

    def _extract_timestamp(self, payload: dict[str, Any]) -> datetime:
        if "timestamp" in payload:
            try:
                return datetime.fromtimestamp(float(payload["timestamp"]), tz=self._timezone)
            except Exception:  # noqa: BLE001
                logger.debug("timestamp numérico inválido: %s", payload["timestamp"])
        for key in ("date", "time", "datetime"):
            value = payload.get(key)
            if value:
                try:
                    return datetime.fromisoformat(str(value)).astimezone(self._timezone)
                except Exception:  # noqa: BLE001
                    logger.debug("timestamp ISO inválido: %s", value)
        return datetime.now(tz=self._timezone)

    def build_consensus(
        self,
        snapshots: Iterable[RateSnapshot],
        *,
        provider_weights: Optional[dict[str, float]] = None,
    ) -> ConsensusSnapshot:
        snapshots_list = list(snapshots)
        if not snapshots_list:
            raise ValueError("Se requieren snapshots para generar consenso.")

        buy_values = [snap.buy_rate for snap in snapshots_list]
        sell_values = [snap.sell_rate for snap in snapshots_list]
        consensus_buy = statistics.median(buy_values)
        consensus_sell = statistics.median(sell_values)
        consensus_mid = (consensus_buy + consensus_sell) / 2

        weights = self._resolve_weights(snapshots_list, provider_weights)
        weighted_buy = self._weighted_median(
            [snap.buy_rate for snap in snapshots_list], weights, snapshots_list
        )
        weighted_sell = self._weighted_median(
            [snap.sell_rate for snap in snapshots_list], weights, snapshots_list
        )

        mid_by_provider: dict[str, list[float]] = {}
        for snap in snapshots_list:
            mid_by_provider.setdefault(snap.source, []).append(snap.mid_rate)
        weighted_mid = 0.0
        for provider, mids in mid_by_provider.items():
            provider_weight = weights.get(provider, 0.0)
            if provider_weight <= 0:
                continue
            weighted_mid += statistics.mean(mids) * provider_weight

        min_mid = min((snap.mid_rate for snap in snapshots_list), default=consensus_mid)
        max_mid = max((snap.mid_rate for snap in snapshots_list), default=consensus_mid)

        validations: List[ProviderValidation] = []
        for snap in snapshots_list:
            provider_mid = snap.mid_rate
            delta_unweighted = provider_mid - consensus_mid
            delta_weighted = provider_mid - weighted_mid
            difference_unweighted = abs(delta_unweighted)
            difference_weighted = abs(delta_weighted)
            flagged = difference_weighted >= self.settings.divergence_threshold
            validations.append(
                ProviderValidation(
                    provider=snap.source,
                    buy_rate=snap.buy_rate,
                    sell_rate=snap.sell_rate,
                    difference_vs_consensus=difference_unweighted,
                    flagged=flagged,
                    difference_vs_weighted=difference_weighted,
                    weight=weights.get(snap.source),
                    delta_vs_consensus=delta_unweighted,
                    delta_vs_weighted=delta_weighted,
                )
            )

        return ConsensusSnapshot(
            timestamp=max(snapshots_list, key=lambda s: s.timestamp).timestamp,
            buy_rate=consensus_buy,
            sell_rate=consensus_sell,
            mid_rate=consensus_mid,
            weighted_buy_rate=weighted_buy,
            weighted_sell_rate=weighted_sell,
            weighted_mid_rate=weighted_mid,
            providers_considered=[snap.source for snap in snapshots_list],
            validations=validations,
            divergence_range=max_mid - min_mid,
            provider_weights=weights,
            anomalies=[],
        )

    @staticmethod
    def _weighted_median(
        values: List[float],
        weights: dict[str, float],
        snapshots: List[RateSnapshot],
    ) -> float:
        if not values:
            raise ValueError("Se requieren valores para calcular la mediana ponderada.")

        total_weight = sum(weights.values())
        if total_weight <= 0:
            return statistics.median(values)

        occurrences: dict[str, int] = {}
        for snapshot in snapshots:
            occurrences[snapshot.source] = occurrences.get(snapshot.source, 0) + 1

        ordered_pairs: list[tuple[float, float]] = []
        for value, snapshot in zip(values, snapshots):
            provider = snapshot.source
            provider_weight = max(weights.get(provider, 0.0), 0.0)
            count = max(occurrences.get(provider, 1), 1)
            normalized = (provider_weight / total_weight) / count
            ordered_pairs.append((value, normalized))
        ordered_pairs.sort(key=lambda item: item[0])

        cumulative = 0.0
        for value, weight in ordered_pairs:
            cumulative += weight
            if cumulative >= 0.5:
                return value
        return ordered_pairs[-1][0]

    @staticmethod
    def _resolve_weights(
        snapshots: List[RateSnapshot],
        provider_weights: Optional[dict[str, float]],
    ) -> dict[str, float]:
        if not snapshots:
            return {}
        if not provider_weights:
            equal_weight = 1.0 / len(snapshots)
            return {snapshot.source: equal_weight for snapshot in snapshots}

        weights: dict[str, float] = {}
        total = 0.0
        for snapshot in snapshots:
            base = provider_weights.get(snapshot.source, 0.0)
            adjusted = max(base, 0.0) * max(snapshot.confidence, 0.0)
            weights[snapshot.source] = adjusted
            total += adjusted

        if total <= 0:
            equal_weight = 1.0 / len(snapshots)
            return {snapshot.source: equal_weight for snapshot in snapshots}

        return {provider: weight / total for provider, weight in weights.items()}

    @staticmethod
    def _sleep_backoff(provider: ProviderSettings, attempt: int) -> None:
        backoff = provider.backoff_seconds
        if backoff <= 0:
            return
        delay = backoff * (2**attempt)
        time.sleep(min(delay, backoff * (2**10)))

    def close(self) -> None:
        if getattr(self, "_owns_client", False):
            self._client.close()

    def __enter__(self) -> "ExchangeRateClient":  # pragma: no cover
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
        self.close()


class MarketDataService:
    """Orquesta la captura multi-fuente y el almacenamiento de snapshots."""

    def __init__(self, repository, settings: Optional[Settings] = None) -> None:
        from .repository import MarketRepository  # import diferido para evitar ciclos

        self.settings = settings or get_settings()
        if isinstance(repository, MarketRepository):
            self.repository = repository
        else:
            raise TypeError("repository debe ser una instancia de MarketRepository")
        self.client = ExchangeRateClient(self.settings)
        self.weight_calculator = ProviderWeightCalculator(self.repository, self.settings)
        self.anomaly_detector = ZScoreAnomalyDetector(self.settings)
        self.drift_monitor = DriftMonitor(self.settings)
        self._prime_drift_monitor()

    def capture_market(self) -> ConsensusSnapshot:
        fetch_results = self.client.fetch_all()
        metrics = self.client.consume_metrics()
        if metrics:
            self.repository.save_provider_metrics(metrics)
        all_snapshots: list[RateSnapshot] = []
        for result in fetch_results:
            for snapshot in result.snapshots:
                self.repository.save_snapshot(snapshot)
                logger.info(
                    "Snapshot guardado de %s (buy=%.4f, sell=%.4f)",
                    snapshot.source,
                    snapshot.buy_rate,
                    snapshot.sell_rate,
                )
                all_snapshots.append(snapshot)

        weights = self._compute_weights(all_snapshots)
        consensus = self.client.build_consensus(all_snapshots, provider_weights=weights)
        error_samples = self._build_error_samples(consensus)
        if error_samples:
            self.repository.record_provider_error_samples(error_samples)
        anomalies = self.anomaly_detector.detect(consensus)
        if anomalies:
            self.repository.record_anomaly_events(anomalies)
            logger.warning(
                "Detectadas %d anomalías: %s",
                len(anomalies),
                ", ".join(f"{event.provider} ({event.severity})" for event in anomalies),
            )
        consensus = consensus.model_copy(update={"anomalies": anomalies})
        drift_event = self._evaluate_drift(consensus)
        if drift_event is not None:
            consensus = consensus.model_copy(update={"drift": drift_event})
        self._persist_consensus(consensus)
        logger.info(
            "Consenso generado con %d proveedores. Divergencia: %.4f",
            len(consensus.providers_considered),
            consensus.divergence_range,
        )
        for validation in consensus.validations:
            if validation.difference_vs_consensus >= self.settings.validation_tolerance:
                logger.warning(
                    "Divergencia detectada en %s: %.4f DOP",
                    validation.provider,
                    validation.difference_vs_consensus,
                )
        return consensus

    def capture_snapshot(self) -> ConsensusSnapshot:
        """Compatibilidad con versiones anteriores."""

        return self.capture_market()

    def consensus_from_repository(self) -> ConsensusSnapshot:
        latest = self.repository.latest_by_provider()
        if not latest:
            raise RuntimeError("No hay datos almacenados todavía para construir consenso.")
        snapshots = list(latest.values())
        weights = self._compute_weights(snapshots)
        consensus = self.client.build_consensus(snapshots, provider_weights=weights)
        anomalies = self.anomaly_detector.detect(consensus)
        drift_event = self.repository.latest_drift_event()
        consensus = consensus.model_copy(update={"anomalies": anomalies})
        if drift_event is not None:
            consensus = consensus.model_copy(update={"drift": drift_event})
        return consensus

    def get_recent_snapshots(self, *, minutes: int = 180) -> list[RateSnapshot]:
        from datetime import timedelta

        cutoff = datetime.now(tz=ZoneInfo(self.settings.timezone)) - timedelta(minutes=minutes)
        return list(self.repository.iter_snapshots(since=cutoff, limit=None))

    def close(self) -> None:
        self.client.close()

    def _compute_weights(self, snapshots: Iterable[RateSnapshot]) -> dict[str, float]:
        snapshot_list = list(snapshots)
        if not snapshot_list:
            return {}
        providers = [snapshot.source for snapshot in snapshot_list]
        reference = max(snapshot.timestamp for snapshot in snapshot_list)
        return self.weight_calculator.compute(providers, reference=reference)

    def _build_error_samples(self, consensus: ConsensusSnapshot) -> list[ProviderErrorSample]:
        weighted_mid = consensus.weighted_mid_rate or consensus.mid_rate
        samples: list[ProviderErrorSample] = []
        for validation in consensus.validations:
            provider_mid = (validation.buy_rate + validation.sell_rate) / 2
            delta_weighted = validation.delta_vs_weighted
            delta_consensus = validation.delta_vs_consensus
            reference_delta = delta_weighted if delta_weighted is not None else delta_consensus
            if reference_delta is None:
                continue
            metadata: dict[str, float | None] = {
                "difference_vs_weighted": validation.difference_vs_weighted,
                "difference_vs_consensus": validation.difference_vs_consensus,
            }
            samples.append(
                ProviderErrorSample(
                    timestamp=consensus.timestamp,
                    provider=validation.provider,
                    delta_vs_weighted=delta_weighted,
                    delta_vs_consensus=delta_consensus,
                    provider_mid=provider_mid,
                    weighted_mid=weighted_mid,
                    consensus_mid=consensus.mid_rate,
                    weight=validation.weight,
                    metadata=metadata,
                )
            )
        return samples

    def _evaluate_drift(self, consensus: ConsensusSnapshot) -> Optional[DriftEvent]:
        value = consensus.weighted_mid_rate or consensus.mid_rate
        signal = self.drift_monitor.update(consensus.timestamp, value)
        if not signal.drift_detected or signal.direction is None:
            return None

        direction = DriftDirection.UP if signal.direction.lower() == "up" else DriftDirection.DOWN
        severity_label = signal.severity or "LOW"
        severity = DriftSeverity(severity_label)
        metadata = (signal.details or {}).copy() if signal.details else {}
        metadata.update({
            "providers": len(consensus.providers_considered),
            "divergence_range": consensus.divergence_range,
        })

        event = DriftEvent(
            timestamp=consensus.timestamp,
            direction=direction,
            metric="weighted_mid_rate" if consensus.weighted_mid_rate is not None else "mid_rate",
            value=value,
            ewma=signal.ewma,
            threshold=signal.threshold,
            cusum_pos=signal.cusum_pos,
            cusum_neg=signal.cusum_neg,
            severity=severity,
            metadata=metadata,
        )
        self.repository.record_drift_events([event])
        return event

    def _persist_consensus(self, consensus: ConsensusSnapshot) -> None:
        metadata: dict[str, Any] = {
            "providers": consensus.providers_considered,
            "provider_weights": consensus.provider_weights,
            "validations": [
                {
                    "provider": v.provider,
                    "delta_vs_consensus": v.delta_vs_consensus,
                    "delta_vs_weighted": v.delta_vs_weighted,
                    "flagged": v.flagged,
                }
                for v in consensus.validations
            ],
            "anomaly_count": len(consensus.anomalies),
        }
        if consensus.drift is not None:
            metadata["drift"] = {
                "direction": consensus.drift.direction.value,
                "metric": consensus.drift.metric,
                "value": consensus.drift.value,
            }

        record = ConsensusSnapshotRecord(
            timestamp=consensus.timestamp,
            buy_rate=consensus.buy_rate,
            sell_rate=consensus.sell_rate,
            mid_rate=consensus.mid_rate,
            weighted_buy_rate=consensus.weighted_buy_rate,
            weighted_sell_rate=consensus.weighted_sell_rate,
            weighted_mid_rate=consensus.weighted_mid_rate,
            divergence_range=consensus.divergence_range,
            provider_count=len(consensus.providers_considered),
            metadata=metadata,
        )
        self.repository.save_consensus_snapshot(record)

    def _prime_drift_monitor(self) -> None:
        try:
            reference = datetime.now(tz=ZoneInfo(self.settings.timezone)) - timedelta(
                minutes=self.settings.drift_window_minutes
            )
        except Exception:  # pragma: no cover - fallback por configuración inválida
            reference = None

        records = self.repository.list_consensus_snapshots(
            since=reference,
            desc=False,
        )
        for record in records:
            value = record.weighted_mid_rate or record.mid_rate
            if value is None:
                continue
            # Evita registrar eventos históricos nuevamente; solo calienta el estado interno
            _ = self.drift_monitor.update(record.timestamp, value)
