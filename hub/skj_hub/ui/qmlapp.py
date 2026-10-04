"""Load the Kirigami UI (qml/Main.qml) and hand it the Bridge."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401 - registers the window type

from skj_hub.ui.bridge import Bridge

log = logging.getLogger(__name__)

QML_DIR = Path(__file__).resolve().parent.parent / "qml"
PAGES = ("start", "apps", "installed", "updates", "help")


def use_kde_style() -> None:
    """KDE's own Qt Quick Controls style, as Kirigami apps use. Before QApplication."""
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "org.kde.desktop")


# Kirigami's page stack creates a page before parenting it; Qt warns each time.
_NOISE = "Created graphical object was not placed in the graphics scene"


def _log_warnings(warnings) -> None:
    for w in warnings:
        text = w.toString()
        if _NOISE not in text:
            log.warning("QML: %s", text)


def load(hub, driver_probe, restart, page: str = "start"):
    """Returns (engine, bridge, window); window is None when the QML failed to load."""
    bridge = Bridge(hub, driver_probe, restart)
    engine = QQmlApplicationEngine()
    engine.warnings.connect(_log_warnings)
    ctx = engine.rootContext()
    ctx.setContextProperty("hub", bridge)
    ctx.setContextProperty("startPage", page if page in PAGES else "start")
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    roots = engine.rootObjects()
    return engine, bridge, (roots[0] if roots else None)


def shutdown(engine) -> None:
    """Destroy the QML window now, while the Bridge its bindings read still exists."""
    from shiboken6 import delete, isValid

    if isValid(engine):
        delete(engine)
