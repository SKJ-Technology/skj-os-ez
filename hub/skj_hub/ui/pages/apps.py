"""Apps: search, install, remove (spec §4.2). Also "My apps" (installed)."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLineEdit, QMessageBox, QScrollArea, QVBoxLayout, QWidget

from skj_hub.catalog.model import App
from skj_hub.i18n import tr
from skj_hub.result import Problem, Result
from skj_hub.ui.widgets import AppCard, label


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
        self.list.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.inner)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

    def show_apps(self, apps: list[App]):
        for c in self.cards:
            c.deleteLater()
        self.cards = []
        for app in apps[:60]:
            c = AppCard(app)
            c.install_requested.connect(self._install)
            c.remove_requested.connect(self._remove)
            self.list.insertWidget(self.list.count() - 1, c)
            self.cards.append(c)

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
    def __init__(self, hub, jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText(tr("apps.search"))
        self.search.setClearButtonEnabled(True)
        self.state = label(tr("apps.hint"), "muted", wrap=True)
        self.results = _AppList(hub, jobs)
        self._query = 0
        self._timer = QTimer(self, singleShot=True, interval=400)
        self._timer.timeout.connect(self._run_search)
        self.search.textChanged.connect(lambda _: self._timer.start())
        self.search.returnPressed.connect(self._run_search)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(label(tr("nav.apps"), "pageTitle"))
        lay.addWidget(self.search)
        lay.addWidget(self.state)
        lay.addWidget(self.results, 1)

    def focus_search(self):
        self.search.setFocus(Qt.OtherFocusReason)

    def _run_search(self):
        text = self.search.text().strip()
        self._timer.stop()
        self._query += 1
        query = self._query
        if len(text) < 2:
            self.state.setText(tr("apps.hint"))
            self.state.show()
            self.results.show_apps([])
            return
        self.state.setText(tr("apps.searching"))
        self.state.show()

        def done(apps):
            if query != self._query:  # an older search finished late
                return
            self.results.show_apps(apps)
            self.state.setVisible(not apps)
            self.state.setText(tr("apps.none"))

        self.jobs.query(lambda: self.hub.search(text), done)


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
