# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import logging
import time
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analytics import PerformanceAnalyzer, ProviderReliabilityAggregator
from .config import Settings, get_settings
from .data_provider import MarketDataService
from .forecast import ForecastService
from .logging_utils import configure_logging
from .models import ConsensusSnapshot, DriftEvent, DriftDirection, TradeAction
from .repository import MarketRepository
from .strategy import StrategyEngine

app = typer.Typer(help="Asistente para el cambio USD/DOP con analítica y pronósticos.")
console = Console()


def _get_repository() -> MarketRepository:
    settings = _get_settings()
    return MarketRepository(settings.db_path)


def _get_settings() -> Settings:
    settings = get_settings()
    configure_logging(settings.log_level)
    return settings


def _print_consensus(consensus: ConsensusSnapshot) -> None:
    console.rule(
        f"Consenso {consensus.timestamp:%Y-%m-%d %H:%M:%S}"
    )
    console.print(
        f"Compra (mediana): [bold]{consensus.buy_rate:.2f}[/] | "
        f"Venta (mediana): [bold]{consensus.sell_rate:.2f}[/] | "
        f"Compra ponderada: [bold]{(consensus.weighted_buy_rate or consensus.buy_rate):.2f}[/] | "
        f"Venta ponderada: [bold]{(consensus.weighted_sell_rate or consensus.sell_rate):.2f}[/] | "
        f"Rango divergencia: {consensus.divergence_range:.2f}"
    )
    table = Table(
        title="Validación cruzada por proveedor",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Proveedor")
    table.add_column("Compra", justify="right")
    table.add_column("Venta", justify="right")
    table.add_column("Δ vs consenso", justify="right")
    table.add_column("Δ ponderado", justify="right")
    table.add_column("Peso", justify="right")
    table.add_column("Estado", justify="center")

    for validation in consensus.validations:
        status = "[green]OK[/]"
        if validation.flagged:
            status = "[red]⚠ Fuera de rango[/]"
        weight = consensus.provider_weights.get(validation.provider, validation.weight or 0.0)
        table.add_row(
            validation.provider,
            f"{validation.buy_rate:.2f}",
            f"{validation.sell_rate:.2f}",
            f"{validation.difference_vs_consensus:.2f}",
            f"{(validation.difference_vs_weighted or 0.0):.2f}",
            f"{weight:.2%}",
            status,
        )

    console.print(table)
    if consensus.anomalies:
        anomaly_table = Table(
            title="Anomalías detectadas",
            box=box.MINIMAL_DOUBLE_HEAD,
            show_lines=False,
        )
        anomaly_table.add_column("Proveedor")
        anomaly_table.add_column("Severidad", justify="center")
        anomaly_table.add_column("Z-score", justify="right")
        anomaly_table.add_column("Δ ponderado", justify="right")

        for event in consensus.anomalies:
            delta_weighted = None
            if event.context and "delta" in event.context:
                try:
                    delta_weighted = float(event.context["delta"])
                except (TypeError, ValueError):
                    delta_weighted = None
            anomaly_table.add_row(
                event.provider,
                event.severity.value,
                f"{event.score:.2f}",
                f"{delta_weighted:.2f}" if delta_weighted is not None else "-",
            )

        console.print(anomaly_table)

    if consensus.drift:
        drift = consensus.drift
        arrow = "↑" if drift.direction == DriftDirection.UP else "↓"
        intensity = None
        if drift.metadata:
            raw_intensity = drift.metadata.get("intensity")
            try:
                intensity = float(raw_intensity) if raw_intensity is not None else None
            except (TypeError, ValueError):
                intensity = None
        details = [
            f"Dirección: {arrow} ({drift.direction.value})",
            f"Valor observado: {drift.value:.3f} DOP",
            f"EWMA: {drift.ewma:.3f} · Umbral: {drift.threshold:.3f}",
            f"CUSUM+: {drift.cusum_pos:.3f} · CUSUM-: {drift.cusum_neg:.3f}",
            f"Severidad: {drift.severity.value}",
        ]
        if intensity is not None:
            details.append(f"Intensidad: {intensity:.2f}× umbral")
        if drift.metadata and "cooldown_remaining" in drift.metadata:
            details.append(f"Cooldown restante: {drift.metadata['cooldown_remaining']}")
        console.print(
            Panel(
                "\n".join(details),
                title="Drift monitor",
                border_style="yellow",
            )
        )


@app.command()
def fetch(
    repetitions: int = typer.Option(1, help="Cantidad de capturas consecutivas"),
    interval: int = typer.Option(0, help="Pausa en segundos entre capturas"),
) -> None:
    """Descarga y almacena nuevas cotizaciones."""

    settings = get_settings()
    repository = _get_repository()
    service = MarketDataService(repository, settings)
    try:
        for i in range(repetitions):
            consensus = service.capture_market()
            console.print(f"[green]Captura #{i + 1}[/]")
            _print_consensus(consensus)
            if i < repetitions - 1 and interval > 0:
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print("[yellow]Captura interrumpida por el usuario.[/]")
    finally:
        service.close()


@app.command()
def analyze() -> None:
    """Genera una recomendación de compra/venta basada en los datos recientes."""

    repository = _get_repository()
    engine = StrategyEngine(repository)
    recommendation = engine.generate_recommendation()
    record = repository.latest_recommendation()
    latest_snapshot = repository.get_latest_snapshot()
    generated_at = record.generated_at if record else (latest_snapshot.timestamp if latest_snapshot else None)

    header = "Recomendación de estrategia"
    if generated_at is not None:
        header += f" · {generated_at:%Y-%m-%d %H:%M}"

    table = Table(title=header, box=box.SIMPLE_HEAVY)
    table.add_column("Acción", justify="center")
    table.add_column("Confianza", justify="center")
    table.add_column("Ganancia esperada (DOP)", justify="right")
    table.add_column("Compra sugerida", justify="right")
    table.add_column("Venta sugerida", justify="right")
    table.add_column("Ventaja vs mercado", justify="right")

    table.add_row(
        recommendation.action.value.upper(),
        f"{recommendation.score * 100:.1f}%",
        f"{recommendation.expected_profit:.2f}",
        f"{recommendation.suggested_buy_rate:.2f}" if recommendation.suggested_buy_rate is not None else "-",
        f"{recommendation.suggested_sell_rate:.2f}" if recommendation.suggested_sell_rate is not None else "-",
        f"{recommendation.spread_advantage:.3f}" if recommendation.spread_advantage is not None else "-",
    )
    console.print(table)
    console.print(Panel(recommendation.reason, title="Justificación", border_style="cyan"))

    forecast_service = ForecastService(repository)
    try:
        forecast = forecast_service.project_end_of_day_profit()
    except RuntimeError as exc:
        console.print(f"[yellow]{exc}[/]")
    else:
        forecast_table = Table(title="Pronóstico de beneficio diario", box=box.MINIMAL_DOUBLE_HEAD)
        forecast_table.add_column("Esperado", justify="right")
        forecast_table.add_column("Mejor caso", justify="right")
        forecast_table.add_column("Peor caso", justify="right")
        forecast_table.add_column("Confianza (±DOP)", justify="right")
        forecast_table.add_row(
            f"{forecast.expected_profit_end_day:.2f}",
            f"{forecast.best_case:.2f}",
            f"{forecast.worst_case:.2f}",
            f"{forecast.confidence_interval:.2f}",
        )
        console.print(forecast_table)
        console.print(Panel(forecast.details, title="Método", border_style="magenta"))


@app.command()
def forecast() -> None:
    """Proyecta la ganancia acumulada al cierre del día."""

    repository = _get_repository()
    forecast_service = ForecastService(repository)
    analyzer = PerformanceAnalyzer(repository)
    data_service = MarketDataService(repository)

    try:
        consensus = data_service.consensus_from_repository()
        _print_consensus(consensus)
    except RuntimeError:
        console.print("[yellow]No hay datos suficientes para mostrar consenso.[/]")
    finally:
        data_service.close()

    result = forecast_service.project_end_of_day_profit()
    summary = analyzer.summarize_day()

    table = Table(title="Pronóstico de beneficio diario")
    table.add_column("Generado")
    table.add_column("Ganancia esperada")
    table.add_column("Mejor caso")
    table.add_column("Peor caso")
    table.add_column("Detalles")

    table.add_row(
        result.generated_at.strftime("%H:%M"),
        f"{result.expected_profit_end_day:.2f}",
        f"{result.best_case:.2f}",
        f"{result.worst_case:.2f}",
        result.details,
    )

    console.print(table)
    console.print(
        f"[cyan]Operaciones hoy:[/] {summary.total_trades} | "
        f"Ganancia realizada: [bold]{summary.realized_profit:.2f} DOP[/bold]"
    )


@app.command()
def trade(
    action: TradeAction = typer.Argument(..., help="Tipo de operación: buy o sell"),
    usd_amount: float = typer.Argument(..., help="Monto en USD a operar"),
    rate: Optional[float] = typer.Option(None, help="Tasa aplicada en la operación"),
    fees: Optional[float] = typer.Option(None, help="Costos totales en DOP"),
) -> None:
    """Registra una operación realizada manualmente."""

    repository = _get_repository()
    engine = StrategyEngine(repository)
    trade = engine.record_trade(action=action, usd_amount=usd_amount, rate_override=rate, fees=fees)

    console.print(
        f"[green]Operación registrada:[/] {trade.action.value.upper()} | "
        f"USD {trade.usd_amount:.2f} a {trade.rate:.2f} | "
        f"Ganancia estimada: {trade.profit_dop:.2f} DOP"
    )


@app.command()
def history(limit: int = typer.Option(10, help="Número de operaciones a mostrar")) -> None:
    """Muestra el historial reciente de operaciones."""

    repository = _get_repository()
    trades = repository.list_trades(limit=limit)
    table = Table(title="Historial de operaciones")
    table.add_column("Fecha")
    table.add_column("Acción")
    table.add_column("USD")
    table.add_column("Tasa")
    table.add_column("Ganancia (DOP)")

    for trade in trades:
        table.add_row(
            trade.timestamp.strftime("%Y-%m-%d %H:%M"),
            trade.action.value,
            f"{trade.usd_amount:.2f}",
            f"{trade.rate:.2f}",
            f"{trade.profit_dop:.2f}",
        )
    if trades:
        console.print(table)
    else:
        console.print("[yellow]No hay operaciones registradas todavía.[/]")


@app.command()
def drift(limit: int = typer.Option(15, help="Número máximo de eventos a mostrar")) -> None:
    """Lista los eventos de drift detectados recientemente."""

    repository = _get_repository()
    events = repository.list_drift_events(limit=limit)
    if not events:
        console.print("[yellow]Aún no se han detectado eventos de drift.[/]")
        return

    table = Table(title="Eventos de drift", box=box.SIMPLE_HEAVY)
    table.add_column("Fecha", justify="center")
    table.add_column("Dirección", justify="center")
    table.add_column("Métrica", justify="left")
    table.add_column("Valor", justify="right")
    table.add_column("EWMA", justify="right")
    table.add_column("Umbral", justify="right")
    table.add_column("CUSUM+", justify="right")
    table.add_column("CUSUM-", justify="right")
    table.add_column("Severidad", justify="center")
    table.add_column("Intensidad", justify="right")

    for event in events:
        arrow = "↑" if event.direction == DriftDirection.UP else "↓"
        intensity = None
        if event.metadata:
            raw_intensity = event.metadata.get("intensity")
            try:
                intensity = float(raw_intensity) if raw_intensity is not None else None
            except (TypeError, ValueError):
                intensity = None
        table.add_row(
            event.timestamp.strftime("%Y-%m-%d %H:%M"),
            f"{arrow} {event.direction.value}",
            event.metric,
            f"{event.value:.3f}",
            f"{event.ewma:.3f}",
            f"{event.threshold:.3f}",
            f"{event.cusum_pos:.3f}",
            f"{event.cusum_neg:.3f}",
            event.severity.value,
            f"{intensity:.2f}" if intensity is not None else "-",
        )

    console.print(table)


@app.command()
def compare() -> None:
    """Muestra la comparación más reciente entre proveedores registrados."""

    repository = _get_repository()
    service = MarketDataService(repository)
    try:
        consensus = service.consensus_from_repository()
    except RuntimeError as exc:
        console.print(f"[yellow]{exc}[/]")
    else:
        _print_consensus(consensus)
    finally:
        service.close()


@app.command()
def providers(
    show_disabled: bool = typer.Option(False, "--show-disabled", help="Incluir proveedores deshabilitados."),
    include_derived: bool = typer.Option(
        False,
        "--include-derived",
        help="Agregar a la tabla los proveedores derivados de fuentes agregadas (ej. InfoDolar).",
    ),
) -> None:
    """Lista los proveedores configurados con su origen y estado."""

    settings = _get_settings()
    repository = _get_repository()
    table = Table(title="Proveedores configurados", box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("Proveedor")
    table.add_column("Habilitado", justify="center")
    table.add_column("Endpoint")
    table.add_column("Ruta compra")
    table.add_column("Ruta venta")
    table.add_column("Ruta media")
    table.add_column("Spread ajustado")

    configured_names: set[str] = set()
    for provider in settings.providers:
        if not provider.enabled and not show_disabled:
            continue
        table.add_row(
            provider.name,
            "Sí" if provider.enabled else "No",
            provider.endpoint,
            provider.buy_path or "-",
            provider.sell_path or "-",
            provider.mid_path or "-",
            f"{provider.spread_adjust:.2f}",
        )
        configured_names.add(provider.name)

    if include_derived:
        latest = repository.latest_by_provider()
        derived_rows = [snapshot for name, snapshot in latest.items() if name not in configured_names]
        origin_label = next((provider.name for provider in settings.providers if provider.format == "html"), "Agregado")
        if derived_rows:
            table.add_section()
            for snapshot in derived_rows:
                table.add_row(
                    snapshot.source,
                    "Sí*",
                    f"via {origin_label}",
                    "-",
                    "-",
                    "-",
                    "-",
                )

    if table.row_count == 0:
        console.print("[yellow]No hay proveedores visibles con los filtros actuales.[/]")
    else:
        console.print(table)
        if include_derived and table.row_count > len(configured_names):
            note_origin = next((provider.name for provider in settings.providers if provider.format == "html"), "fuente agregada")
            console.print(
                f"[dim]* Datos agregados automáticamente desde {note_origin} u otras fuentes secundarias.[/]")


@app.command(name="provider-metrics")
def provider_metrics(
    window_minutes: int = typer.Option(180, help="Ventana a evaluar en minutos."),
    include_disabled: bool = typer.Option(False, "--include-disabled", help="Incluir proveedores deshabilitados."),
    dry_run: bool = typer.Option(False, help="Calcula sin persistir los resultados."),
) -> None:
    """Calcula métricas agregadas de confiabilidad por proveedor."""

    settings = _get_settings()
    repository = MarketRepository(settings.db_path)
    aggregator = ProviderReliabilityAggregator(repository, settings)

    if dry_run:
        records = aggregator.compute(window_minutes=window_minutes, include_disabled=include_disabled)
    else:
        records = aggregator.compute_and_store(
            window_minutes=window_minutes,
            include_disabled=include_disabled,
        )

    table = Table(title=f"Confiabilidad por proveedor · últimos {window_minutes} min", box=box.SIMPLE_HEAVY)
    table.add_column("Proveedor")
    table.add_column("Cobertura", justify="right")
    table.add_column("Éxito", justify="right")
    table.add_column("Capturas", justify="center")
    table.add_column("Latencia p50 (ms)", justify="right")
    table.add_column("Latencia p95 (ms)", justify="right")
    table.add_column("Fallos", justify="center")

    for record in records:
        table.add_row(
            record.provider,
            f"{record.coverage_ratio * 100:.1f}%",
            f"{record.success_ratio * 100:.1f}%",
            f"{record.captures}/{record.expected_captures}",
            f"{record.latency_p50_ms:.1f}" if record.latency_p50_ms is not None else "-",
            f"{record.latency_p95_ms:.1f}" if record.latency_p95_ms is not None else "-",
            str(record.failure_count),
        )

    console.print(table)
    action = "calculadas" if dry_run else "calculadas y persistidas"
    console.print(f"[green]Métricas {action} correctamente.[/]")


@app.command()
def serve(
    host: Optional[str] = typer.Option(None, help="Host donde expondré la API/web."),
    port: Optional[int] = typer.Option(None, help="Puerto TCP del servidor."),
    reload: bool = typer.Option(False, help="Recargar automáticamente al detectar cambios (solo desarrollo)."),
) -> None:
    """Inicia la API REST y el dashboard web."""

    settings = _get_settings()
    resolved_host = host or settings.server_host
    resolved_port = port or settings.server_port
    console.print(
        "[cyan]Levantando servicio web en[/] [bold]{host}:{port}[/] (reload={reload})".format(
            host=resolved_host, port=resolved_port, reload=reload
        )
    )
    import uvicorn

    uvicorn.run(
        "cambio_dollar.web.app:app",
        host=resolved_host,
        port=resolved_port,
        reload=reload,
    )
