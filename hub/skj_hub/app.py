"""Entry point: `skj-hub [--page NAME] [--notify] [--fake]`."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from skj_hub import __version__


def setup_logging() -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "skj-hub"
    state.mkdir(parents=True, exist_ok=True)
    log = state / "hub.log"
    logging.basicConfig(
        filename=log,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return log


def make_hub(fake: bool):
    from skj_hub.hub import Hub

    if fake:
        from skj_hub.backends.fake import demo_backends

        hub = Hub(demo_backends())
        hub.demo = True
        return hub
    from skj_hub.hub import real_backends

    return Hub(real_backends())


def main(argv: list[str] | None = None) -> int:
    from skj_hub.ui.qmlapp import PAGES

    p = argparse.ArgumentParser(prog="skj-hub", description="SKJ Hub")
    p.add_argument("--page", choices=PAGES, default="start")
    p.add_argument("--notify", action="store_true", help="check for updates and notify, no window")
    p.add_argument("--fake", action="store_true", help="demo data instead of the real system")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)

    setup_logging()
    fake = args.fake or os.environ.get("SKJ_HUB_FAKE") == "1"
    hub = make_hub(fake)

    if args.notify:
        from skj_hub.updates import notifier

        return notifier.run(hub)

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from skj_hub import system
    from skj_hub.ui import qmlapp

    qmlapp.use_kde_style()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("skj-hub")
    app.setWindowIcon(QIcon.fromTheme("skj-logo-icon"))
    # only when installed: without the menu entry the desktop portal complains
    if Path("/usr/share/applications/skj-hub.desktop").exists():
        app.setDesktopFileName("skj-hub")
    driver_probe = (lambda: None) if fake else system.driver_state
    engine, bridge, window = qmlapp.load(hub, driver_probe, system.restart, args.page)
    if window is None:
        print(
            "SKJ Hub: could not load its window (see ~/.local/state/skj-hub/hub.log)",
            file=sys.stderr,
        )
        return 1
    code = app.exec()
    bridge.jobs.wait(2000)
    qmlapp.shutdown(engine)  # before the bridge its bindings read
    return code


if __name__ == "__main__":
    sys.exit(main())
