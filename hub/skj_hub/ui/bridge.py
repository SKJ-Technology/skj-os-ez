"""What the Kirigami (QML) UI sees of the hub.

QML never touches backends: it binds to these objects' properties and calls
their slots; work runs on worker threads through ui/jobs.py and results come
back as property changes.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QObject,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QIcon

from skj_hub.catalog.categories import GROUPS
from skj_hub.catalog.model import App, Offer
from skj_hub.hub import new_kernels
from skj_hub.i18n import STRINGS, human_size, language, problem_text, tr
from skj_hub.result import Problem, Result
from skj_hub.ui.jobs import Jobs
from skj_hub.updates.plan import UpdatePlan
from skj_hub.updates.rules import RestartState, restart_state


def source_text(offer: Offer) -> str:
    text = tr("apps.from", source=tr(f"source.{offer.source.value}"))
    if offer.developer_verified:
        text += " · " + tr("apps.verified")
    return text


def icon_source(offer: Offer) -> str:
    """A file path or theme icon name for Kirigami.Icon; "" = draw a letter tile."""
    if offer.icon and (offer.icon.startswith("/") or QIcon.hasThemeIcon(offer.icon)):
        return offer.icon
    for name in (offer.app_id or "", offer.ref):
        if name and QIcon.hasThemeIcon(name):
            return name
    return ""


class AppsModel(QAbstractListModel):
    """A list of apps with per-row install state."""

    ROLES = (
        "name",
        "summary",
        "source",
        "iconName",
        "installed",
        "busy",
        "progress",  # 0-100, or -1 for "busy, no number"
        "status",
        "problem",
        "details",
        "others",  # other sources, as texts
    )
    countChanged = Signal()

    def __init__(self, hub, jobs: Jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self._apps: list[App] = []
        self._state: dict[str, dict] = {}  # app.key -> busy/progress/status/problem/details

    # --- model plumbing -----------------------------------------------------------

    def roleNames(self):
        return {Qt.UserRole + i: name.encode() for i, name in enumerate(self.ROLES)}

    def rowCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self._apps)

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._apps)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._apps):
            return None
        app = self._apps[index.row()]
        name = self.ROLES[role - Qt.UserRole] if role >= Qt.UserRole else "name"
        st = self._state.get(app.key, {})
        offer = app.default
        match name:
            case "name":
                return app.name
            case "summary":
                return offer.summary
            case "source":
                return source_text(offer)
            case "iconName":
                return icon_source(offer)
            case "installed":
                return app.installed
            case "busy":
                return st.get("busy", False)
            case "progress":
                return st.get("progress", -1)
            case "status":
                return st.get("status", "")
            case "problem":
                return st.get("problem", "")
            case "details":
                return st.get("details", "")
            case "others":
                if app.installed:
                    return []
                return [source_text(o) for o in app.offers if o is not offer]
        return None

    def set_apps(self, apps: list[App]):
        self.beginResetModel()
        self._apps = list(apps)
        self.endResetModel()
        self.countChanged.emit()

    def apps(self) -> list[App]:
        return self._apps

    def _changed(self, app: App, **state):
        self._state.setdefault(app.key, {}).update(state)
        for row, a in enumerate(self._apps):
            if a is app:
                i = self.index(row)
                self.dataChanged.emit(i, i)
                return

    # --- actions ------------------------------------------------------------------

    def _run(self, app: App, call, busy_text: str, done_text: str, on_ok):
        self._changed(app, busy=True, progress=-1, status=busy_text, problem="", details="")

        def done(result: Result):
            if result.ok:
                on_ok()
                self._changed(app, busy=False, status=done_text)
            else:
                self._changed(
                    app,
                    busy=False,
                    status="",
                    problem=problem_text(result.problem),
                    details=result.details,
                )

        self.jobs.change(
            call,
            lambda pct, _s: self._changed(app, progress=-1 if pct is None else int(pct)),
            done,
            lambda err: done(Result(Problem.UNKNOWN, err)),
        )

    def _install(self, app: App, offer: Offer | None):
        chosen = offer or app.default

        def ok():
            app.offers[:] = [replace(o, installed=o is chosen) for o in app.offers]

        self._run(
            app,
            lambda progress, cancel: self.hub.install(app, progress, cancel, offer),
            tr("apps.installing", name=app.name),
            tr("apps.done_install", name=app.name),
            ok,
        )

    @Slot(int)
    def install(self, row: int):
        if 0 <= row < len(self._apps):
            self._install(self._apps[row], None)

    @Slot(int, int)
    def installFrom(self, row: int, other: int):
        """Install from the other-th entry of the row's `others` list."""
        if not 0 <= row < len(self._apps):
            return
        app = self._apps[row]
        others = [o for o in app.offers if o is not app.default]
        if 0 <= other < len(others):
            self._install(app, others[other])

    @Slot(int)
    def remove(self, row: int):
        if not 0 <= row < len(self._apps):
            return
        app = self._apps[row]

        def ok():
            app.offers[:] = [replace(o, installed=False) for o in app.offers]

        self._run(
            app,
            lambda progress, cancel: self.hub.remove(app, progress, cancel),
            tr("apps.removing", name=app.name),
            tr("apps.done_remove", name=app.name),
            ok,
        )


class AppsController(QObject):
    """The Apps page: browse a group, or search by name."""

    changed = Signal()

    def __init__(self, hub, jobs: Jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self._model = AppsModel(hub, jobs, self)
        self._loading = False
        self._message = tr("apps.hint")
        self._query = 0

    @Property(QObject, constant=True)
    def model(self):
        return self._model

    @Property(bool, notify=changed)
    def loading(self):
        return self._loading

    @Property(str, notify=changed)
    def message(self):
        return self._message

    def _set(self, loading: bool, message: str):
        self._loading, self._message = loading, message
        self.changed.emit()

    @Slot(str, str)
    def refresh(self, text: str, group: str):
        """Search when there's text, otherwise list the group."""
        text = text.strip()
        self._query += 1
        query = self._query
        searching = len(text) >= 2
        self._set(True, tr("apps.searching") if searching else tr("apps.loading"))

        def done(apps):
            if query != self._query:  # an older request finished late
                return
            self._model.set_apps(apps)
            if not apps:
                self._set(False, tr("apps.none"))
            elif searching:
                self._set(False, "")
            else:
                self._set(False, tr("apps.hint") + " " + tr("apps.count", count=len(apps)))

        if searching:
            self.jobs.query(lambda: self.hub.search(text), done)
        else:
            self.jobs.query(lambda: self.hub.browse(group or "all"), done)


class InstalledController(QObject):
    changed = Signal()

    def __init__(self, hub, jobs: Jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self._model = AppsModel(hub, jobs, self)
        self._loading = False
        self._message = ""

    @Property(QObject, constant=True)
    def model(self):
        return self._model

    @Property(bool, notify=changed)
    def loading(self):
        return self._loading

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Slot()
    def reload(self):
        self._loading, self._message = True, tr("apps.loading")
        self.changed.emit()

        def done(apps):
            self._model.set_apps(apps)
            self._loading = False
            self._message = "" if apps else tr("installed.empty")
            self.changed.emit()

        self.jobs.query(self.hub.installed_apps, done)


class UpdatesController(QObject):
    """One button for everything; a restart is only ever offered (spec §4.4)."""

    changed = Signal()

    def __init__(self, hub, jobs: Jobs, driver_probe, restart, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self.driver_probe, self._restart_fn = driver_probe, restart
        self.plan = UpdatePlan()
        self.applied: UpdatePlan | None = None
        self._state = "checking"  # checking | none | ready | running | done
        self._summary = tr("updates.checking")
        self._details = ""
        self._progress = -1
        self._problem = ""
        self._problem_details = ""
        self._restart = "none"  # none | ready | wait
        self._timer = QTimer(self, interval=10_000)
        self._timer.timeout.connect(self._check_restart)

    @Property(str, notify=changed)
    def state(self):
        return self._state

    @Property(str, notify=changed)
    def summary(self):
        return self._summary

    @Property(str, notify=changed)
    def details(self):
        return self._details

    @Property(int, notify=changed)
    def progress(self):
        return self._progress

    @Property(str, notify=changed)
    def problem(self):
        return self._problem

    @Property(str, notify=changed)
    def problemDetails(self):
        return self._problem_details

    @Property(str, notify=changed)
    def restartState(self):
        return self._restart

    @Slot()
    def check(self):
        self._state, self._summary = "checking", tr("updates.checking")
        self.changed.emit()
        self.jobs.query(self.hub.update_plan, self._show_plan)

    def _show_plan(self, plan: UpdatePlan):
        self.plan = plan
        if plan.empty:
            self._state, self._summary, self._details = "none", tr("updates.none"), ""
        else:
            size = human_size(plan.download_size) if plan.download_size else "…"
            self._state = "ready"
            self._summary = tr("updates.some", count=plan.count, size=size)
            self._details = "\n".join(
                f"• {i.name}" + (f"  {i.new_version}" if i.new_version else "") for i in plan.items
            )
        self.changed.emit()

    @Slot()
    def apply(self):
        if self._state != "ready":
            return
        plan = self.plan
        self._state, self._summary = "running", tr("updates.running")
        self._progress, self._problem, self._problem_details = -1, "", ""
        self.changed.emit()

        def progress(pct, _status):
            self._progress = -1 if pct is None else int(pct)
            self.changed.emit()

        def done(result: Result):
            if not result.ok:
                self._problem = problem_text(result.problem)
                self._problem_details = result.details
                self.check()
                return
            self.applied = plan
            self._state, self._summary, self._details = "done", tr("updates.done"), ""
            self.changed.emit()
            self._check_restart()

        self.jobs.change(
            lambda p, cancel: self.hub.apply(plan, p, cancel),
            progress,
            done,
            lambda err: done(Result(Problem.UNKNOWN, err)),
        )

    def _check_restart(self):
        plan = self.applied
        if plan is None:
            return
        state = restart_state(plan.needs_restart, new_kernels(plan.items), self.driver_probe())
        if state is RestartState.WAIT_FOR_DRIVER:
            self._restart = "wait"
            self._timer.start()
        else:
            self._timer.stop()
            self._restart = "ready" if state is RestartState.READY else "none"
        self.changed.emit()

    @Slot()
    def restartNow(self):
        """Only ever called from the 'Restart now' button."""
        if self._restart != "ready":
            return
        result = self._restart_fn()
        if not result.ok:
            self._problem = problem_text(result.problem)
            self._problem_details = result.details
            self.changed.emit()

    @Slot()
    def later(self):
        self._timer.stop()
        self._restart = "none"
        self.changed.emit()


class Bridge(QObject):
    """Root object given to QML as `hub`."""

    def __init__(self, hub, driver_probe, restart, parent=None):
        super().__init__(parent)
        self.hub = hub
        self.jobs = Jobs(self)
        self._apps = AppsController(hub, self.jobs, self)
        self._installed = InstalledController(hub, self.jobs, self)
        self._updates = UpdatesController(hub, self.jobs, driver_probe, restart, self)

    @Property("QVariantMap", constant=True)
    def strings(self):
        lang = language() if _lang() is None else _lang()
        return {key: entry.get(lang, entry["en"]) for key, entry in STRINGS.items()}

    @Property("QVariantList", constant=True)
    def groups(self):
        return [{"key": key, "label": tr(f"group.{key}")} for key in GROUPS]

    @Property(bool, constant=True)
    def demo(self):
        return bool(getattr(self.hub, "demo", False))

    @Property(bool, constant=True)
    def supported(self):
        return self.hub.platform.supported

    @Property(QObject, constant=True)
    def apps(self):
        return self._apps

    @Property(QObject, constant=True)
    def installed(self):
        return self._installed

    @Property(QObject, constant=True)
    def updates(self):
        return self._updates


def _lang() -> str | None:
    from skj_hub import i18n

    return getattr(i18n, "_lang", None)
