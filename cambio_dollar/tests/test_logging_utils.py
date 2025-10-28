from __future__ import annotations

import logging

import pytest

from cambio_dollar.logging_utils import configure_logging, current_level


@pytest.mark.parametrize(
    "level,expected",
    [
        ("DEBUG", logging.DEBUG),
        ("info", logging.INFO),
        ("WaRnInG", logging.WARNING),
        ("invalid", logging.INFO),
        ("", logging.INFO),
    ],
)
def test_configure_logging_sets_level(level: str, expected: int) -> None:
    configure_logging(level, force=True)
    assert current_level() == expected


def test_configure_logging_updates_existing_handlers() -> None:
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    logger.handlers = [handler]
    handler.setLevel(logging.ERROR)

    configure_logging("WARNING", force=True)

    assert handler.level == logging.WARNING
    assert logger.level == logging.WARNING
    logger.handlers.clear()
    configure_logging("INFO", force=True)
