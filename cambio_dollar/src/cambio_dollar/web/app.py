# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import logging
import statistics
import io
import csv
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

from ..config import Settings, get_settings
from ..data_provider import MarketDataService
from ..forecast import ForecastService
from ..logging_utils import configure_logging
from ..models import (
    ConsensusSnapshot,
    DriftEvent,
    ForecastResult,
    RateSnapshot,
    StrategyRecommendation,
    Trade,
    TradeAction,
)
from ..analytics import PerformanceAnalyzer
from ..repository import MarketRepository
from ..scheduler import CaptureScheduler
from ..strategy import StrategyEngine

logger = logging.getLogger(__name__)


class SnapshotResponse(BaseModel):
    timestamp: datetime
    buy_rate: float
    sell_rate: float
    source: str
    confidence: float

    @classmethod
    def from_snapshot(cls, snapshot: RateSnapshot) -> "SnapshotResponse":
        return cls(**snapshot.model_dump())


class ProviderStatus(BaseModel):
    name: str
    enabled: bool
    endpoint: Optional[str]
    last_timestamp: Optional[datetime]
    buy_rate: Optional[float]
    sell_rate: Optional[float]
    confidence: Optional[float]
    aggregated: bool = Field(
        default=False,
        description="Indica si el proveedor proviene de una fuente agregada (por ejemplo InfoDolar).",
    )
    origin: Optional[str] = Field(
        default=None,
        description="Fuente primaria desde la cual se obtuvo la información del proveedor agregada.",
    )


class SchedulerStatus(BaseModel):
    enabled: bool
    running: bool
    interval_seconds: int
    last_run: Optional[str]
    last_success: Optional[str]
    last_error: Optional[str]


class RecommendationResponse(BaseModel):
    generated_at: datetime
    action: TradeAction
    score: float
    expected_profit: float
    suggested_buy_rate: Optional[float]
    suggested_sell_rate: Optional[float]
    spread_advantage: Optional[float]
    reason: str


class TradeResponse(BaseModel):
    timestamp: datetime
    action: TradeAction
    usd_amount: float
    rate: float
    fees: float
    profit_dop: float

    @classmethod
    def from_trade(cls, trade: Trade) -> "TradeResponse":
        return cls(
            timestamp=trade.timestamp,
            action=trade.action,
            usd_amount=trade.usd_amount,
            rate=trade.rate,
            fees=trade.fees,
            profit_dop=trade.profit_dop,
        )


class TradeRequest(BaseModel):
    action: TradeAction = Field(description="Tipo de operación: buy o sell")
    usd_amount: float = Field(gt=0, description="Monto en USD a operar")
    rate: Optional[float] = Field(default=None, gt=0, description="Tasa DOP/USD (opcional, usa consenso si no se provee)")
    fees: Optional[float] = Field(default=None, ge=0, description="Comisiones en DOP (opcional, usa configuración por defecto)")


def create_app(custom_settings: Optional[Settings] = None) -> FastAPI:
    settings = custom_settings or get_settings()
    configure_logging(settings.log_level)
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
    scheduler = CaptureScheduler(settings)
    timezone = ZoneInfo(settings.timezone)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        scheduler.start()
        try:
            yield
        finally:
            scheduler.shutdown()

    app = FastAPI(title="Cambio Dollar API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.templates = templates
    app.state.scheduler = scheduler
    app.state.timezone = timezone

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

    def get_repository() -> MarketRepository:
        return MarketRepository(settings.db_path)

    def _collect_provider_status(repository: MarketRepository) -> List[ProviderStatus]:
        latest = repository.latest_by_provider()
        statuses: List[ProviderStatus] = []
        seen: set[str] = set()
        aggregated_sources = [provider for provider in settings.providers if provider.format == "html"]
        aggregated_origin = aggregated_sources[0].name if aggregated_sources else None
        aggregated_endpoint = aggregated_sources[0].endpoint if aggregated_sources else None
        for provider in settings.providers:
            snapshot = latest.get(provider.name)
            statuses.append(
                ProviderStatus(
                    name=provider.name,
                    enabled=provider.enabled,
                    endpoint=provider.endpoint,
                    last_timestamp=snapshot.timestamp if snapshot else None,
                    buy_rate=snapshot.buy_rate if snapshot else None,
                    sell_rate=snapshot.sell_rate if snapshot else None,
                    confidence=snapshot.confidence if snapshot else None,
                    aggregated=provider.format == "html",
                    origin=None,
                )
            )
            seen.add(provider.name)

        for name, snapshot in latest.items():
            if name in seen:
                continue
            statuses.append(
                ProviderStatus(
                    name=name,
                    enabled=True,
                    endpoint=aggregated_endpoint,
                    last_timestamp=snapshot.timestamp,
                    buy_rate=snapshot.buy_rate,
                    sell_rate=snapshot.sell_rate,
                    confidence=snapshot.confidence,
                    aggregated=True,
                    origin=aggregated_origin or "Agregado",
                )
            )
        return statuses

    def get_strategy_engine(repository: MarketRepository = Depends(get_repository)) -> StrategyEngine:
        return StrategyEngine(repository, settings)

    def _build_recommendation_response(engine: StrategyEngine) -> RecommendationResponse:
        recommendation = engine.generate_recommendation()
        record = engine.repository.latest_recommendation()
        generated_at = record.generated_at if record else datetime.now(tz=timezone)
        return RecommendationResponse(
            generated_at=generated_at,
            action=recommendation.action,
            score=recommendation.score,
            expected_profit=recommendation.expected_profit,
            suggested_buy_rate=recommendation.suggested_buy_rate,
            suggested_sell_rate=recommendation.suggested_sell_rate,
            spread_advantage=recommendation.spread_advantage,
            reason=recommendation.reason,
        )

    def _project_forecast(repository: MarketRepository) -> ForecastResult:
        service = ForecastService(repository, settings)
        try:
            return service.project_end_of_day_profit()
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.post("/api/log")
    def log_message(message: str) -> dict[str, str]:
        logger.info(f"Client log: {message}")
        return {"status": "logged"}

    @app.get("/api/scheduler", response_model=SchedulerStatus)
    def scheduler_status() -> SchedulerStatus:
        raw = scheduler.status()
        interval_raw = raw.get("interval_seconds", settings.scheduler_interval_seconds)
        try:
            interval = int(interval_raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            interval = settings.scheduler_interval_seconds

        def _str_or_none(value: object | None) -> Optional[str]:
            return value if isinstance(value, str) else None

        last_run = _str_or_none(raw.get("last_run"))
        last_success = _str_or_none(raw.get("last_success"))
        last_error = _str_or_none(raw.get("last_error"))
        return SchedulerStatus(
            enabled=bool(raw.get("enabled", False)),
            running=bool(raw.get("running", False)),
            interval_seconds=interval,
            last_run=last_run,
            last_success=last_success,
            last_error=last_error,
        )

    @app.post("/api/capture", status_code=status.HTTP_202_ACCEPTED)
    def trigger_capture(background_tasks: BackgroundTasks) -> dict[str, str]:
        if not settings.scheduler_enabled:
            logger.info("Ejecutando captura manual con scheduler deshabilitado")
        background_tasks.add_task(scheduler.run_once, force=True)
        return {"detail": "Capture triggered"}

    @app.post("/api/analyze", response_model=RecommendationResponse)
    def trigger_analyze(engine: StrategyEngine = Depends(get_strategy_engine)) -> RecommendationResponse:
        return _build_recommendation_response(engine)

    @app.post("/api/forecast", response_model=ForecastResult)
    def trigger_forecast(repository: MarketRepository = Depends(get_repository)) -> ForecastResult:
        return _project_forecast(repository)

    @app.post("/api/compare", response_model=ConsensusSnapshot)
    def trigger_compare(repository: MarketRepository = Depends(get_repository)) -> ConsensusSnapshot:
        service = MarketDataService(repository, settings)
        try:
            return service.consensus_from_repository()
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        finally:
            service.close()

    @app.post("/api/providers/refresh", response_model=List[ProviderStatus])
    def refresh_providers(repository: MarketRepository = Depends(get_repository)) -> List[ProviderStatus]:
        return _collect_provider_status(repository)

    @app.post("/api/history", response_model=List[TradeResponse])
    def recent_history(
        limit: int = 10,
        repository: MarketRepository = Depends(get_repository),
    ) -> List[TradeResponse]:
        trades = repository.list_trades(limit=limit)
        return [TradeResponse.from_trade(trade) for trade in trades]

    @app.post("/api/trade", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
    def record_trade(
        trade_request: TradeRequest,
        engine: StrategyEngine = Depends(get_strategy_engine),
    ) -> TradeResponse:
        """Registra una operación de compra o venta."""
        try:
            trade = engine.record_trade(
                action=trade_request.action,
                usd_amount=trade_request.usd_amount,
                rate_override=trade_request.rate,
                fees=trade_request.fees,
            )
            return TradeResponse.from_trade(trade)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    @app.put("/api/trade/{trade_id}", response_model=TradeResponse)
    def update_trade(
        trade_id: int,
        trade_request: TradeRequest,
        repository: MarketRepository = Depends(get_repository),
        engine: StrategyEngine = Depends(get_strategy_engine),
    ) -> TradeResponse:
        """Actualiza una operación de compra o venta existente."""
        existing_trade = repository.list_trades(limit=None) # Fetch all to find by ID
        trade_to_update = next((t for t in existing_trade if t.id == trade_id), None)

        if not trade_to_update:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found")

        # Update fields from request
        trade_to_update.action = trade_request.action
        trade_to_update.usd_amount = trade_request.usd_amount
        trade_to_update.rate = trade_request.rate or trade_to_update.rate # Use existing if not provided
        trade_to_update.fees = trade_request.fees if trade_request.fees is not None else trade_to_update.fees

        # Recalculate dop_amount and profit_dop based on new values
        # Need to fetch a snapshot to calculate profit correctly
        snapshot = repository.get_latest_snapshot()
        if snapshot is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No market data available to recalculate profit.")

        trade_to_update.dop_amount = trade_to_update.usd_amount * trade_to_update.rate - trade_to_update.fees if trade_to_update.action is TradeAction.SELL else trade_to_update.usd_amount * trade_to_update.rate + trade_to_update.fees
        trade_to_update.profit_dop = engine._calculate_profit(trade_to_update.action, trade_to_update.usd_amount, trade_to_update.rate, snapshot)

        updated_trade = repository.update_trade(trade_to_update)
        if not updated_trade:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update trade.")
        return TradeResponse.from_trade(updated_trade)

    @app.delete("/api/trade/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_trade(
        trade_id: int,
        repository: MarketRepository = Depends(get_repository),
    ):
        """Elimina una operación de compra o venta por su ID."""
        deleted = repository.delete_trade(trade_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found.")
        return

    @app.get("/api/consensus", response_model=ConsensusSnapshot)
    def api_consensus(repository: MarketRepository = Depends(get_repository)) -> ConsensusSnapshot:
        service = MarketDataService(repository, settings)
        try:
            return service.consensus_from_repository()
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        finally:
            service.close()

    @app.get("/api/snapshots", response_model=List[SnapshotResponse])
    def api_snapshots(
        minutes: int = 180,
        repository: MarketRepository = Depends(get_repository),
    ) -> List[SnapshotResponse]:
        if minutes <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="minutes must be > 0")
        cutoff = datetime.now(tz=timezone) - timedelta(minutes=minutes)
        snapshots = repository.iter_snapshots(since=cutoff)
        return [SnapshotResponse.from_snapshot(s) for s in snapshots]

    @app.get("/api/providers", response_model=List[ProviderStatus])
    def api_providers(repository: MarketRepository = Depends(get_repository)) -> List[ProviderStatus]:
        return _collect_provider_status(repository)

    @app.get("/api/drift", response_model=List[DriftEvent])
    def api_drift(
        limit: int = 25,
        repository: MarketRepository = Depends(get_repository),
    ) -> List[DriftEvent]:
        if limit <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be > 0")
        return repository.list_drift_events(limit=limit)

    @app.get("/api/recommendation", response_model=RecommendationResponse)
    def api_recommendation(
        engine: StrategyEngine = Depends(get_strategy_engine),
    ) -> RecommendationResponse:
        return _build_recommendation_response(engine)

    @app.get("/api/forecast", response_model=ForecastResult)
    def api_forecast(repository: MarketRepository = Depends(get_repository)) -> ForecastResult:
        return _project_forecast(repository)

    @app.get("/api/export/trades.csv", response_class=StreamingResponse)
    def export_trades_csv(repository: MarketRepository = Depends(get_repository)):
        """Exporta el historial de trades a un archivo CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Escribir la cabecera
        writer.writerow(["ID", "Timestamp", "Action", "USD Amount", "Rate", "DOP Amount", "Fees", "Profit DOP"])

        trades = repository.list_trades(limit=None)  # Obtener todos los trades
        for trade in trades:
            writer.writerow([
                trade.id,
                trade.timestamp.isoformat(),
                trade.action.value,
                trade.usd_amount,
                trade.rate,
                trade.dop_amount,
                trade.fees,
                trade.profit_dop,
            ])

        output.seek(0)
        response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=historial_trades.csv"
        return response

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, repository: MarketRepository = Depends(get_repository)) -> HTMLResponse:
        service = MarketDataService(repository, settings)
        try:
            consensus: Optional[ConsensusSnapshot]
            try:
                consensus = service.consensus_from_repository()
            except RuntimeError:
                consensus = None
        finally:
            service.close()

        # --- Métricas para el Sidebar ---
        analyzer = PerformanceAnalyzer(repository)
        day_summary = analyzer.summarize_day()

        cutoff_24h = datetime.now(tz=timezone) - timedelta(hours=24)
        snapshots_24h = repository.iter_snapshots(since=cutoff_24h)
        
        trend_24h = None
        volatility = None
        if len(snapshots_24h) > 1:
            mid_rates_24h = [s.mid_rate for s in snapshots_24h]
            # Trend: diferencia entre el más reciente y el más antiguo
            trend_24h = snapshots_24h[0].mid_rate - snapshots_24h[-1].mid_rate
            # Volatility: desviación estándar de las tasas medias
            if len(mid_rates_24h) > 1:
                volatility = statistics.stdev(mid_rates_24h)

        best_buy_provider = None
        best_sell_provider = None
        if consensus and consensus.validations:
            # Mejor para comprar USD (tasa de venta más baja)
            best_sell_provider = min(consensus.validations, key=lambda v: v.sell_rate)
            # Mejor para vender USD (tasa de compra más alta)
            best_buy_provider = max(consensus.validations, key=lambda v: v.buy_rate)

        sidebar_metrics = {
            "trades_today": day_summary.total_trades,
            "realized_profit": day_summary.realized_profit,
            "trend_24h": trend_24h,
            "volatility": volatility,
            "best_buy_provider": best_buy_provider,
            "best_sell_provider": best_sell_provider,
        }
        # --- Fin Métricas Sidebar ---

        recent = repository.iter_snapshots(limit=20)
        statuses = _collect_provider_status(repository)
        provider_status_json = [s.model_dump(mode='json') for s in statuses]
        engine = StrategyEngine(repository, settings)
        recommendation = engine.generate_recommendation()
        recommendation_record = repository.latest_recommendation()
        recommendation_history = repository.list_recommendations(limit=8)
        trade_history = repository.list_trades(limit=8)
        forecast_service = ForecastService(repository, settings)
        try:
            forecast = forecast_service.project_end_of_day_profit()
        except RuntimeError:
            forecast = None
        drift_events = repository.list_drift_events(limit=6)
        template_context = {
            "request": request,
            "consensus": consensus,
            "recent_snapshots": recent,
            "provider_status": statuses,
            "provider_status_json": provider_status_json,
            "scheduler": scheduler.status(),
            "recommendation": recommendation,
            "recommendation_generated_at": recommendation_record.generated_at if recommendation_record else None,
            "recommendation_history": recommendation_history,
            "trade_history": trade_history,
            "forecast": forecast,
            "drift_events": drift_events,
            "sidebar_metrics": sidebar_metrics,
        }
        return templates.TemplateResponse(request, "dashboard.html", template_context)

    return app


app = create_app()
