# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional

from .db_migrations import upgrade_database
from .models import (
    ExternalMacroMetric,
    FeatureVectorRecord,
    ModelEvaluationRecord,
    PerformanceLabel,
    AnomalyEvent,
    AnomalySeverity,
    ProviderReliabilityMetrics,
    RateSnapshot,
    StrategyRecommendationRecord,
    Trade,
    TradeAction,
    ProviderFetchMetric,
    ProviderErrorSample,
    ConsensusSnapshotRecord,
    DriftEvent,
    DriftDirection,
    DriftSeverity,
)


class MarketRepository:
    """Repositorio SQLite para snapshots y operaciones."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        upgrade_database(self._db_path)

    @staticmethod
    def _dump_json(data: Optional[dict[str, Any]]) -> Optional[str]:
        if data is None:
            return None
        return json.dumps(data)

    @staticmethod
    def _load_json(raw: Optional[str]) -> Optional[dict[str, Any]]:
        if raw is None or raw == "":
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    # --- Rate snapshots -------------------------------------------------
    def save_snapshot(self, snapshot: RateSnapshot) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO rate_snapshots (timestamp, buy_rate, sell_rate, source, confidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot.timestamp.isoformat(),
                    snapshot.buy_rate,
                    snapshot.sell_rate,
                    snapshot.source,
                    snapshot.confidence,
                ),
            )
            conn.commit()

    def get_latest_snapshot(self) -> Optional[RateSnapshot]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT timestamp, buy_rate, sell_rate, source, confidence
                FROM rate_snapshots
                ORDER BY timestamp DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return RateSnapshot(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            buy_rate=row["buy_rate"],
            sell_rate=row["sell_rate"],
            source=row["source"],
            confidence=row["confidence"],
        )

    def iter_snapshots(
        self,
        *,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[RateSnapshot]:
        query = (
            "SELECT timestamp, buy_rate, sell_rate, source, confidence "
            "FROM rate_snapshots"
        )
        clauses: list[str] = []
        params: list[object] = []
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if until is not None:
            clauses.append("timestamp <= ?")
            params.append(until.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            RateSnapshot(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                buy_rate=row["buy_rate"],
                sell_rate=row["sell_rate"],
                source=row["source"],
                confidence=row["confidence"],
            )
            for row in rows
        ]

    def latest_by_provider(self) -> dict[str, RateSnapshot]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT timestamp, buy_rate, sell_rate, source, confidence
                FROM rate_snapshots
                ORDER BY timestamp DESC
                """
            ).fetchall()

        snapshot_map: dict[str, RateSnapshot] = {}
        for row in rows:
            source = row["source"]
            if source in snapshot_map:
                continue
            snapshot_map[source] = RateSnapshot(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                buy_rate=row["buy_rate"],
                sell_rate=row["sell_rate"],
                source=source,
                confidence=row["confidence"],
            )
        return snapshot_map

    # --- Consensus snapshots ---------------------------------------------
    def save_consensus_snapshot(self, record: ConsensusSnapshotRecord) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO consensus_snapshots (
                    timestamp,
                    buy_rate,
                    sell_rate,
                    mid_rate,
                    weighted_buy_rate,
                    weighted_sell_rate,
                    weighted_mid_rate,
                    divergence_range,
                    provider_count,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.timestamp.isoformat(),
                    record.buy_rate,
                    record.sell_rate,
                    record.mid_rate,
                    record.weighted_buy_rate,
                    record.weighted_sell_rate,
                    record.weighted_mid_rate,
                    record.divergence_range,
                    record.provider_count,
                    self._dump_json(record.metadata),
                ),
            )
            conn.commit()

    def list_consensus_snapshots(
        self,
        *,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
        desc: bool = True,
    ) -> List[ConsensusSnapshotRecord]:
        query = (
            "SELECT id, timestamp, buy_rate, sell_rate, mid_rate, weighted_buy_rate, weighted_sell_rate, "
            "weighted_mid_rate, divergence_range, provider_count, metadata FROM consensus_snapshots"
        )
        clauses: list[str] = []
        params: list[object] = []
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        order = "DESC" if desc else "ASC"
        query += f" ORDER BY timestamp {order}"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ConsensusSnapshotRecord(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                buy_rate=row["buy_rate"],
                sell_rate=row["sell_rate"],
                mid_rate=row["mid_rate"],
                weighted_buy_rate=row["weighted_buy_rate"],
                weighted_sell_rate=row["weighted_sell_rate"],
                weighted_mid_rate=row["weighted_mid_rate"],
                divergence_range=row["divergence_range"],
                provider_count=row["provider_count"],
                metadata=self._load_json(row["metadata"]),
            )
            for row in rows
        ]

    # --- Trades ---------------------------------------------------------
    def save_trade(self, trade: Trade) -> Trade:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO trades (timestamp, action, usd_amount, rate, fees, dop_amount, profit_dop)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.timestamp.isoformat(),
                    trade.action.value,
                    trade.usd_amount,
                    trade.rate,
                    trade.fees,
                    trade.dop_amount,
                    trade.profit_dop,
                ),
            )
            conn.commit()
            trade.id = cursor.lastrowid
        return trade

    def list_trades(self, limit: Optional[int] = None) -> List[Trade]:
        query = (
            "SELECT id, timestamp, action, usd_amount, rate, fees, dop_amount, profit_dop "
            "FROM trades ORDER BY timestamp DESC"
        )
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query).fetchall()
        return [self._row_to_trade(row) for row in rows]

    def get_profit_summary(
        self,
        *,
        since: Optional[datetime] = None,
    ) -> float:
        query = "SELECT SUM(profit_dop) FROM trades"
        params: list[object] = []
        if since is not None:
            query += " WHERE timestamp >= ?"
            params.append(since.isoformat())
        with self._connection() as conn:
            row = conn.execute(query, params).fetchone()
        return float(row[0] or 0.0)

    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        return Trade(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            action=TradeAction(row["action"]),
            usd_amount=row["usd_amount"],
            rate=row["rate"],
            fees=row["fees"],
            dop_amount=row["dop_amount"],
            profit_dop=row["profit_dop"],
        )

    def update_trade(self, trade: Trade) -> Optional[Trade]:
        if trade.id is None:
            raise ValueError("Trade ID must be provided for update.")
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE trades
                SET timestamp = ?, action = ?, usd_amount = ?, rate = ?, fees = ?, dop_amount = ?, profit_dop = ?
                WHERE id = ?
                """,
                (
                    trade.timestamp.isoformat(),
                    trade.action.value,
                    trade.usd_amount,
                    trade.rate,
                    trade.fees,
                    trade.dop_amount,
                    trade.profit_dop,
                    trade.id,
                ),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None  # No trade found with the given ID
            return trade

    def delete_trade(self, trade_id: int) -> bool:
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
            conn.commit()
            return cursor.rowcount > 0

    # --- Strategy recommendations ---------------------------------------
    def save_recommendation(self, record: StrategyRecommendationRecord) -> StrategyRecommendationRecord:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO strategy_recommendations (
                    generated_at,
                    action,
                    score,
                    expected_profit,
                    reason,
                    suggested_buy_rate,
                    suggested_sell_rate,
                    spread_advantage
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.generated_at.isoformat(),
                    record.action.value,
                    record.score,
                    record.expected_profit,
                    record.reason,
                    record.suggested_buy_rate,
                    record.suggested_sell_rate,
                    record.spread_advantage,
                ),
            )
            conn.commit()
            record.id = cursor.lastrowid
        return record

    def latest_recommendation(self) -> Optional[StrategyRecommendationRecord]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, generated_at, action, score, expected_profit, reason,
                       suggested_buy_rate, suggested_sell_rate, spread_advantage
                FROM strategy_recommendations
                ORDER BY generated_at DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return self._row_to_recommendation(row)

    def list_recommendations(self, limit: Optional[int] = None) -> List[StrategyRecommendationRecord]:
        query = (
            "SELECT id, generated_at, action, score, expected_profit, reason, "
            "suggested_buy_rate, suggested_sell_rate, spread_advantage "
            "FROM strategy_recommendations ORDER BY generated_at DESC"
        )
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query).fetchall()
        return [self._row_to_recommendation(row) for row in rows]

    def _row_to_recommendation(self, row: sqlite3.Row) -> StrategyRecommendationRecord:
        return StrategyRecommendationRecord(
            id=row["id"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            action=TradeAction(row["action"]),
            score=row["score"],
            expected_profit=row["expected_profit"],
            reason=row["reason"],
            suggested_buy_rate=row["suggested_buy_rate"],
            suggested_sell_rate=row["suggested_sell_rate"],
            spread_advantage=row["spread_advantage"],
        )

    # --- Feature store -------------------------------------------------
    def save_feature_vector(self, record: FeatureVectorRecord) -> FeatureVectorRecord:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO feature_store (
                    snapshot_timestamp,
                    feature_version,
                    scope,
                    payload,
                    metadata
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.timestamp.isoformat(),
                    record.feature_version,
                    record.scope,
                    json.dumps(record.payload),
                    self._dump_json(record.metadata),
                ),
            )
            conn.commit()
            record.id = cursor.lastrowid
        return record

    def list_feature_vectors(
        self,
        *,
        scope: Optional[str] = None,
        feature_version: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[FeatureVectorRecord]:
        query = (
            "SELECT id, snapshot_timestamp, feature_version, scope, payload, metadata "
            "FROM feature_store"
        )
        clauses: list[str] = []
        params: list[object] = []
        if scope is not None:
            clauses.append("scope = ?")
            params.append(scope)
        if feature_version is not None:
            clauses.append("feature_version = ?")
            params.append(feature_version)
        if since is not None:
            clauses.append("snapshot_timestamp >= ?")
            params.append(since.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY snapshot_timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            FeatureVectorRecord(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["snapshot_timestamp"]),
                feature_version=row["feature_version"],
                scope=row["scope"],
                payload=json.loads(row["payload"]),
                metadata=self._load_json(row["metadata"]),
            )
            for row in rows
        ]

    # --- Performance labels --------------------------------------------
    def save_performance_label(self, label: PerformanceLabel) -> PerformanceLabel:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO labels_performance (
                    snapshot_timestamp,
                    horizon_minutes,
                    label,
                    realized_profit,
                    metadata,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    label.snapshot_timestamp.isoformat(),
                    label.horizon_minutes,
                    label.label,
                    label.realized_profit,
                    self._dump_json(label.metadata),
                    label.created_at.isoformat(),
                ),
            )
            conn.commit()
            label.id = cursor.lastrowid
        return label

    def list_performance_labels(
        self,
        *,
        since: Optional[datetime] = None,
        horizon_minutes: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[PerformanceLabel]:
        query = (
            "SELECT id, snapshot_timestamp, horizon_minutes, label, realized_profit, metadata, created_at "
            "FROM labels_performance"
        )
        clauses: list[str] = []
        params: list[object] = []
        if since is not None:
            clauses.append("snapshot_timestamp >= ?")
            params.append(since.isoformat())
        if horizon_minutes is not None:
            clauses.append("horizon_minutes = ?")
            params.append(horizon_minutes)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY snapshot_timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            PerformanceLabel(
                id=row["id"],
                snapshot_timestamp=datetime.fromisoformat(row["snapshot_timestamp"]),
                horizon_minutes=row["horizon_minutes"],
                label=row["label"],
                realized_profit=row["realized_profit"],
                metadata=self._load_json(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    # --- External macro metrics ----------------------------------------
    def upsert_macro_metric(self, metric: ExternalMacroMetric) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO external_macro (timestamp, source, metric, value, metadata)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(timestamp, source, metric) DO UPDATE SET
                    value = excluded.value,
                    metadata = excluded.metadata
                """,
                (
                    metric.timestamp.isoformat(),
                    metric.source,
                    metric.metric,
                    metric.value,
                    self._dump_json(metric.metadata),
                ),
            )
            conn.commit()

    def get_macro_series(
        self,
        *,
        source: Optional[str] = None,
        metric: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ExternalMacroMetric]:
        query = "SELECT id, timestamp, source, metric, value, metadata FROM external_macro"
        clauses: list[str] = []
        params: list[object] = []
        if source is not None:
            clauses.append("source = ?")
            params.append(source)
        if metric is not None:
            clauses.append("metric = ?")
            params.append(metric)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ExternalMacroMetric(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                source=row["source"],
                metric=row["metric"],
                value=row["value"],
                metadata=self._load_json(row["metadata"]),
            )
            for row in rows
        ]

    # --- Model evaluations ---------------------------------------------
    def save_model_evaluation(self, record: ModelEvaluationRecord) -> ModelEvaluationRecord:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO model_evaluations (
                    model_name,
                    model_version,
                    dataset_version,
                    metric_name,
                    metric_value,
                    recorded_at,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.model_name,
                    record.model_version,
                    record.dataset_version,
                    record.metric_name,
                    record.metric_value,
                    record.recorded_at.isoformat(),
                    self._dump_json(record.metadata),
                ),
            )
            conn.commit()
            record.id = cursor.lastrowid
        return record

    def list_model_evaluations(
        self,
        *,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        metric_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ModelEvaluationRecord]:
        query = (
            "SELECT id, model_name, model_version, dataset_version, metric_name, metric_value, recorded_at, metadata "
            "FROM model_evaluations"
        )
        clauses: list[str] = []
        params: list[object] = []
        if model_name is not None:
            clauses.append("model_name = ?")
            params.append(model_name)
        if model_version is not None:
            clauses.append("model_version = ?")
            params.append(model_version)
        if metric_name is not None:
            clauses.append("metric_name = ?")
            params.append(metric_name)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY recorded_at DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ModelEvaluationRecord(
                id=row["id"],
                model_name=row["model_name"],
                model_version=row["model_version"],
                dataset_version=row["dataset_version"],
                metric_name=row["metric_name"],
                metric_value=row["metric_value"],
                recorded_at=datetime.fromisoformat(row["recorded_at"]),
                metadata=self._load_json(row["metadata"]),
            )
            for row in rows
        ]

    # --- Provider metrics -----------------------------------------------
    def save_provider_metrics(self, metrics: Iterable[ProviderFetchMetric]) -> None:
        payload = list(metrics)
        if not payload:
            return
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO provider_fetch_metrics (
                    timestamp,
                    provider,
                    latency_ms,
                    status_code,
                    success,
                    attempts,
                    retries,
                    error,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        metric.timestamp.isoformat(),
                        metric.provider,
                        metric.latency_ms,
                        metric.status_code,
                        int(metric.success),
                        metric.attempts,
                        metric.retries,
                        metric.error,
                        self._dump_json(metric.metadata),
                    )
                    for metric in payload
                ],
            )
            conn.commit()

    def list_provider_metrics(
        self,
        *,
        provider: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ProviderFetchMetric]:
        query = (
            "SELECT id, timestamp, provider, latency_ms, status_code, success, attempts, retries, error, metadata "
            "FROM provider_fetch_metrics"
        )
        clauses: list[str] = []
        params: list[object] = []
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if until is not None:
            clauses.append("timestamp <= ?")
            params.append(until.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ProviderFetchMetric(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                provider=row["provider"],
                latency_ms=row["latency_ms"],
                status_code=row["status_code"],
                success=bool(row["success"]),
                attempts=row["attempts"],
                retries=row["retries"],
                error=row["error"],
                metadata=self._load_json(row["metadata"]),
            )
            for row in rows
        ]

    def save_provider_reliability_metrics(
        self,
        rollups: Iterable[ProviderReliabilityMetrics],
    ) -> None:
        payload = list(rollups)
        if not payload:
            return
        now_utc = datetime.now(timezone.utc)
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO provider_metrics (
                    provider,
                    window_start,
                    window_end,
                    captures,
                    attempts,
                    expected_captures,
                    coverage_ratio,
                    success_ratio,
                    mean_latency_ms,
                    latency_p50_ms,
                    latency_p95_ms,
                    mean_error,
                    std_error,
                    failure_count,
                    metadata,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, window_start, window_end) DO UPDATE SET
                    captures=excluded.captures,
                    attempts=excluded.attempts,
                    expected_captures=excluded.expected_captures,
                    coverage_ratio=excluded.coverage_ratio,
                    success_ratio=excluded.success_ratio,
                    mean_latency_ms=excluded.mean_latency_ms,
                    latency_p50_ms=excluded.latency_p50_ms,
                    latency_p95_ms=excluded.latency_p95_ms,
                    mean_error=excluded.mean_error,
                    std_error=excluded.std_error,
                    failure_count=excluded.failure_count,
                    metadata=excluded.metadata,
                    created_at=excluded.created_at
                """,
                [
                    (
                        rollup.provider,
                        rollup.window_start.isoformat(),
                        rollup.window_end.isoformat(),
                        rollup.captures,
                        rollup.attempts,
                        rollup.expected_captures,
                        rollup.coverage_ratio,
                        rollup.success_ratio,
                        rollup.mean_latency_ms,
                        rollup.latency_p50_ms,
                        rollup.latency_p95_ms,
                        rollup.mean_error,
                        rollup.std_error,
                        rollup.failure_count,
                        self._dump_json(rollup.metadata),
                        (rollup.created_at or now_utc).isoformat(),
                    )
                    for rollup in payload
                ],
            )
            conn.commit()

    def list_provider_reliability_metrics(
        self,
        *,
        provider: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ProviderReliabilityMetrics]:
        query = (
            "SELECT id, provider, window_start, window_end, captures, attempts, expected_captures, "
            "coverage_ratio, success_ratio, mean_latency_ms, latency_p50_ms, latency_p95_ms, "
            "mean_error, std_error, failure_count, metadata, created_at FROM provider_metrics"
        )
        clauses: list[str] = []
        params: list[object] = []
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        if since is not None:
            clauses.append("window_end >= ?")
            params.append(since.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY window_end DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ProviderReliabilityMetrics(
                id=row["id"],
                provider=row["provider"],
                window_start=datetime.fromisoformat(row["window_start"]),
                window_end=datetime.fromisoformat(row["window_end"]),
                captures=row["captures"],
                attempts=row["attempts"],
                expected_captures=row["expected_captures"],
                coverage_ratio=row["coverage_ratio"],
                success_ratio=row["success_ratio"],
                mean_latency_ms=row["mean_latency_ms"],
                latency_p50_ms=row["latency_p50_ms"],
                latency_p95_ms=row["latency_p95_ms"],
                mean_error=row["mean_error"],
                std_error=row["std_error"],
                failure_count=row["failure_count"],
                metadata=self._load_json(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    # --- Provider error samples -----------------------------------------
    def record_provider_error_samples(self, samples: Iterable[ProviderErrorSample]) -> None:
        payload = list(samples)
        if not payload:
            return
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO provider_error_samples (
                    timestamp,
                    provider,
                    delta_vs_weighted,
                    delta_vs_consensus,
                    provider_mid,
                    weighted_mid,
                    consensus_mid,
                    weight,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sample.timestamp.isoformat(),
                        sample.provider,
                        sample.delta_vs_weighted,
                        sample.delta_vs_consensus,
                        sample.provider_mid,
                        sample.weighted_mid,
                        sample.consensus_mid,
                        sample.weight,
                        self._dump_json(sample.metadata),
                    )
                    for sample in payload
                ],
            )
            conn.commit()

    def list_provider_error_samples(
        self,
        *,
        provider: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ProviderErrorSample]:
        query = (
            "SELECT id, timestamp, provider, delta_vs_weighted, delta_vs_consensus, provider_mid,"
            " weighted_mid, consensus_mid, weight, metadata FROM provider_error_samples"
        )
        clauses: list[str] = []
        params: list[object] = []
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if until is not None:
            clauses.append("timestamp <= ?")
            params.append(until.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            ProviderErrorSample(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                provider=row["provider"],
                delta_vs_weighted=row["delta_vs_weighted"],
                delta_vs_consensus=row["delta_vs_consensus"],
                provider_mid=row["provider_mid"],
                weighted_mid=row["weighted_mid"],
                consensus_mid=row["consensus_mid"],
                weight=row["weight"],
                metadata=self._load_json(row["metadata"]),
            )
            for row in rows
        ]

    # --- Drift events ----------------------------------------------------
    def record_drift_events(self, events: Iterable[DriftEvent]) -> None:
        payload = list(events)
        if not payload:
            return
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO drift_events (
                    timestamp,
                    direction,
                    metric,
                    value,
                    ewma,
                    threshold,
                    cusum_pos,
                    cusum_neg,
                    severity,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.timestamp.isoformat(),
                        event.direction.value,
                        event.metric,
                        event.value,
                        event.ewma,
                        event.threshold,
                        event.cusum_pos,
                        event.cusum_neg,
                        event.severity.value,
                        self._dump_json(event.metadata),
                    )
                    for event in payload
                ],
            )
            conn.commit()

    def list_drift_events(
        self,
        *,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[DriftEvent]:
        query = (
            "SELECT id, timestamp, direction, metric, value, ewma, threshold, cusum_pos, cusum_neg, severity, metadata "
            "FROM drift_events"
        )
        clauses: list[str] = []
        params: list[object] = []
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            DriftEvent(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                direction=DriftDirection(row["direction"]),
                metric=row["metric"],
                value=row["value"],
                ewma=row["ewma"],
                threshold=row["threshold"],
                cusum_pos=row["cusum_pos"],
                cusum_neg=row["cusum_neg"],
                severity=DriftSeverity(row["severity"]),
                metadata=self._load_json(row["metadata"]),
            )
            for row in rows
        ]

    def latest_drift_event(self) -> Optional[DriftEvent]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, timestamp, direction, metric, value, ewma, threshold, cusum_pos, cusum_neg, severity, metadata
                FROM drift_events
                ORDER BY timestamp DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return DriftEvent(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            direction=DriftDirection(row["direction"]),
            metric=row["metric"],
            value=row["value"],
            ewma=row["ewma"],
            threshold=row["threshold"],
            cusum_pos=row["cusum_pos"],
            cusum_neg=row["cusum_neg"],
            severity=DriftSeverity(row["severity"]),
            metadata=self._load_json(row["metadata"]),
        )

    # --- Anomaly events -------------------------------------------------
    def record_anomaly_events(self, events: Iterable[AnomalyEvent]) -> None:
        payload = list(events)
        if not payload:
            return
        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO anomaly_events (
                    timestamp,
                    provider,
                    metric,
                    detector,
                    score,
                    severity,
                    context
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.timestamp.isoformat(),
                        event.provider,
                        event.metric,
                        event.detector,
                        event.score,
                        event.severity.value,
                        self._dump_json(event.context),
                    )
                    for event in payload
                ],
            )
            conn.commit()

    def list_anomalies(
        self,
        *,
        provider: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[AnomalyEvent]:
        query = (
            "SELECT id, timestamp, provider, metric, detector, score, severity, context "
            "FROM anomaly_events"
        )
        clauses: list[str] = []
        params: list[object] = []
        if provider is not None:
            clauses.append("provider = ?")
            params.append(provider)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            AnomalyEvent(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                provider=row["provider"],
                metric=row["metric"],
                detector=row["detector"],
                score=row["score"],
                severity=AnomalySeverity(row["severity"]),
                context=self._load_json(row["context"]),
            )
            for row in rows
        ]
