# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import logging
from typing import Optional

_CONFIGURED = False


def _resolve_level(level_name: str) -> int:
    if not level_name:
        return logging.INFO
    candidate = logging.getLevelName(level_name.upper())
    if isinstance(candidate, str):
        return logging.INFO
    return int(candidate)


def configure_logging(level_name: str, *, force: bool = False) -> None:
    """Configura el logging raíz respetando el nivel indicado.

    Reutiliza handlers existentes si ya fueron configurados previamente, evitando
    duplicar emisores en stdout.
    """

    global _CONFIGURED

    level = _resolve_level(level_name)
    root = logging.getLogger()

    if not root.handlers:
        logging.basicConfig(level=level)
    elif force:
        for handler in root.handlers:
            handler.setLevel(level)
    elif not _CONFIGURED:
        logging.basicConfig(level=level)
    else:
        for handler in root.handlers:
            handler.setLevel(level)

    root.setLevel(level)
    _CONFIGURED = True


def current_level() -> Optional[int]:
    root = logging.getLogger()
    return root.level
