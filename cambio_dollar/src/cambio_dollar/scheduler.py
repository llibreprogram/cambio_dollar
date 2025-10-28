# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import logging
from datetime import datetime
from threading import Lock
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from zoneinfo import ZoneInfo

from .config import Settings
from .data_provider import MarketDataService
from .repository import MarketRepository

logger = logging.getLogger(__name__)


class CaptureScheduler:
    """Gestiona las capturas automáticas de mercado."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._timezone = ZoneInfo(settings.timezone)
        self._scheduler = BackgroundScheduler(timezone=self._timezone)
        self._job_id = "market-capture"
        self._lock = Lock()
        self._last_run: Optional[datetime] = None
        self._last_success: Optional[datetime] = None
        self._last_error: Optional[str] = None

    def start(self) -> None:
        if not self.settings.scheduler_enabled:
            logger.info("Scheduler deshabilitado por configuración.")
            return
        if self._scheduler.running:
            return

        trigger = IntervalTrigger(seconds=self.settings.scheduler_interval_seconds)
        self._scheduler.add_job(
            self._run_capture,
            trigger,
            id=self._job_id,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=self.settings.scheduler_interval_seconds,
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "Scheduler iniciado: intervalo=%ss",
            self.settings.scheduler_interval_seconds,
        )

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler detenido")

    def run_once(self, *, force: bool = False) -> None:
        if not force and not self.settings.scheduler_enabled:
            logger.info("Scheduler deshabilitado: ejecución manual omitida")
            return
        self._run_capture()

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "enabled": self.settings.scheduler_enabled,
                "running": self._scheduler.running,
                "interval_seconds": self.settings.scheduler_interval_seconds,
                "last_run": self._format_dt(self._last_run),
                "last_success": self._format_dt(self._last_success),
                "last_error": self._last_error,
            }

    def _run_capture(self) -> None:
        with self._lock:
            self._last_run = datetime.now(tz=self._timezone)
        repository = MarketRepository(self.settings.db_path)
        service = MarketDataService(repository, self.settings)
        try:
            service.capture_market()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error en captura programada")
            with self._lock:
                self._last_error = str(exc)
        else:
            with self._lock:
                self._last_success = datetime.now(tz=self._timezone)
                self._last_error = None
        finally:
            service.close()

    def _format_dt(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.astimezone(self._timezone).isoformat()
