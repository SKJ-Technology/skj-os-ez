"""Apps: search, install, remove (spec §4.2). Also "My apps" (installed)."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from skj_hub.catalog.categories import GROUPS
from skj_hub.catalog.model import App
from skj_hub.i18n import tr
from skj_hub.result import Problem, Result
from skj_hub.ui.widgets import AppCard, button, label


class _AppList(QWidget):
    """A scrolling list of AppCards with install/remove wired to the hub."""

    def __init__(self, hub, jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self.cards: list[AppCard] = []
        self.inner = QWidget()
        self.list = QVBoxLayout(self.inner)
        self.list.setContentsMargins(0, 0, 8, 0)
        self.list.setSpacing(10)
        self._pending: list[App] = []
        self.more = button(tr("apps.show_more"), None, self._show_more)
        self.more.hide()
        self.list.addWidget(self.more, alignment=Qt.AlignHCenter)
        self.list.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.inner)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

    PAGE = 40

    def show_apps(self, apps: list[App]):
        for c in self.cards:
            c.deleteLater()
        self.cards = []
        self._pending = list(apps)
        self._show_more()

    def _show_more(self):
        batch, self._pending = self._pending[: self.PAGE], self._pending[self.PAGE :]
        for app in batch:
            c = AppCard(app)
            c.install_requested.connect(self._install)
            c.remove_requested.connect(self._remove)
            self.list.insertWidget(self.list.count() - 2, c)
            self.cards.append(c)
        self.more.setVisible(bool(self._pending))

    def _card(self, app: App) -> AppCard | None:
        return next((c for c in self.cards if c.app is app), None)

    def _install(self, app: App, offer):
        card = self._card(app)
        card.busy(tr("apps.installing", name=app.name))
        chosen = offer or app.default

        def done(result: Result):
            if result.ok:
                app.offers[:] = [replace(o, installed=o is chosen) for o in app.offers]
            card.finished(result, tr("apps.done_install", name=app.name))

        self.jobs.change(
            lambda progress, cancel: self.hub.install(app, progress, cancel, offer),
            card.set_progress,
            done,
            lambda err: card.finished(Result(Problem.UNKNOWN, err), ""),
        )

    def _remove(self, app: App):
        answer = QMessageBox.question(
            self, tr("apps.remove"), tr("apps.confirm_remove", name=app.name)
        )
        if answer != QMessageBox.Yes:
            return
        card = self._card(app)
        card.busy(tr("apps.removing", name=app.name))

        def done(result: Result):
            if result.ok:
                app.offers[:] = [replace(o, installed=False) for o in app.offers]
            card.finished(result, tr("apps.done_remove", name=app.name))

        self.jobs.change(
            lambda progress, cancel: self.hub.remove(app, progress, cancel),
            card.set_progress,
            done,
            lambda err: card.finished(Result(Problem.UNKNOWN, err), ""),
        )


class AppsPage(QWidget):
    """Browse every app by group, or search by name."""

    def __init__(self, hub, jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText(tr("apps.search"))
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(40)
        self.search.addAction(QIcon.fromTheme("search"), QLineEdit.LeadingPosition)
        self.group = QComboBox()
        self.group.setMinimumHeight(40)
        for key in GROUPS:
            self.group.addItem(tr(f"group.{key}"), key)
        self.state = label(tr("apps.hint"), "muted", wrap=True)
        self.results = _AppList(hub, jobs)
        self._query = 0
        self._loaded = False
        self._timer = QTimer(self, singleShot=True, interval=400)
        self._timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda _: self._timer.start())
        self.search.returnPressed.connect(self.refresh)
        self.group.currentIndexChanged.connect(lambda _: self.refresh())

        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.group)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(label(tr("nav.apps"), "pageTitle"))
        lay.addLayout(top)
        lay.addWidget(self.state)
        lay.addWidget(self.results, 1)

    def focus_search(self):
        self.search.setFocus(Qt.OtherFocusReason)
        if not self._loaded:
            self.refresh()

    def refresh(self):
        """Search when there's text, otherwise list the chosen group."""
        self._loaded = True
        text = self.search.text().strip()
        group = self.group.currentData()
        self._timer.stop()
        self._query += 1
        query = self._query
        searching = len(text) >= 2
        self.state.setText(tr("apps.searching") if searching else tr("apps.loading"))
        self.state.show()

        def done(apps):
            if query != self._query:  # an older request finished late
                return
            self.results.show_apps(apps)
            if not apps:
                self.state.setText(tr("apps.none"))
            elif searching:
                self.state.hide()
            else:
                self.state.setText(tr("apps.hint") + " " + tr("apps.count", count=len(apps)))

        if searching:
            self.jobs.query(lambda: self.hub.search(text), done)
        else:
            self.jobs.query(lambda: self.hub.browse(group), done)


class InstalledPage(QWidget):
    def __init__(self, hub, jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self.state = label(tr("apps.searching"), "muted", wrap=True)
        self.list = _AppList(hub, jobs)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(label(tr("nav.installed"), "pageTitle"))
        lay.addWidget(self.state)
        lay.addWidget(self.list, 1)

    def reload(self):
        self.state.setText(tr("apps.searching"))
        self.state.show()

        def done(apps):
            self.list.show_apps(apps)
            self.state.setVisible(not apps)
            self.state.setText(tr("installed.empty"))

        self.jobs.query(self.hub.installed_apps, done)
