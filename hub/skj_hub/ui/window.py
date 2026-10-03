"""Main window: sidebar + pages (ClamGuard layout, SKJ colours)."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from skj_hub.i18n import tr
from skj_hub.ui.jobs import Jobs
from skj_hub.ui.pages.apps import AppsPage, InstalledPage
from skj_hub.ui.pages.help import HelpPage
from skj_hub.ui.pages.start import StartPage
from skj_hub.ui.pages.updates import UpdatesPage
from skj_hub.ui.widgets import label

PAGES = ("start", "apps", "installed", "updates", "help")
ICONS = {
    "start": "go-home",
    "apps": "system-software-install",
    "installed": "view-list-icons",
    "updates": "system-software-update",
    "help": "help-about",
}


class MainWindow(QMainWindow):
    def __init__(self, hub, driver_probe, restart, parent=None):
        super().__init__(parent)
        self.hub = hub
        self.jobs = Jobs(self)
        self.setWindowTitle(tr("app.title"))
        self.setWindowIcon(QIcon.fromTheme("skj-logo-icon"))
        self.resize(1100, 740)

        self.start = StartPage(hub, self.jobs)
        self.apps = AppsPage(hub, self.jobs)
        self.installed = InstalledPage(hub, self.jobs)
        self.updates = UpdatesPage(hub, self.jobs, driver_probe, restart)
        self.help = HelpPage()
        self.start.go_apps.connect(lambda: self.show_page("apps"))
        self.start.go_updates.connect(lambda: self.show_page("updates"))

        self.stack = QStackedWidget()
        for page in (self.start, self.apps, self.installed, self.updates, self.help):
            self.stack.addWidget(page)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(22, 22))
        self.nav.setFrameShape(QFrame.NoFrame)
        self.nav.setSpacing(2)
        # long names wrap instead of adding a scroll bar under the list
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setWordWrap(True)
        self.nav.setTextElideMode(Qt.ElideNone)
        for key in PAGES:
            QListWidgetItem(QIcon.fromTheme(ICONS[key]), tr(f"nav.{key}"), self.nav)
        self.nav.currentRowChanged.connect(self._on_nav)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(14, 20, 14, 14)
        sl.addWidget(label(tr("app.title"), "brand"))
        sl.addSpacing(14)
        sl.addWidget(self.nav, 1)

        root = QWidget()
        root.setObjectName("root")
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        rl.addWidget(sidebar)
        rl.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self._loaded: set[str] = set()
        self.nav.setCurrentRow(0)

    def show_page(self, key: str):
        self.nav.setCurrentRow(PAGES.index(key))

    def _on_nav(self, row: int):
        key = PAGES[row]
        self.stack.setCurrentIndex(row)
        if key == "apps":
            self.apps.focus_search()
        elif key == "installed":
            self.installed.reload()
        elif key == "updates" and "updates" not in self._loaded:
            self.updates.check()
        elif key == "start" and "start" not in self._loaded:
            self.start.refresh()
        self._loaded.add(key)

    def closeEvent(self, event):
        self.jobs.wait(2000)
        super().closeEvent(event)
