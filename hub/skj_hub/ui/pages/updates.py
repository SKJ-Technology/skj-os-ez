"""Updates: one button for everything, never restarts on its own (spec §4.4)."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from skj_hub.hub import new_kernels
from skj_hub.i18n import human_size, tr
from skj_hub.result import Problem, Result
from skj_hub.ui.widgets import ProblemBox, button, card, label
from skj_hub.updates.plan import UpdatePlan
from skj_hub.updates.rules import RestartState, restart_state


class UpdatesPage(QWidget):
    def __init__(self, hub, jobs, driver_probe, restart, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs
        self.driver_probe = driver_probe  # () -> DriverState | None
        self.restart = restart  # () -> Result
        self.plan = UpdatePlan()
        self.applied: UpdatePlan | None = None

        self.status = label(tr("updates.checking"), "status", wrap=True)
        self.why = label(tr("updates.why"), "muted", wrap=True)
        self.go = button(tr("updates.button"), "big", self._apply)
        self.go.hide()
        self.details_toggle = button(tr("updates.details"), "link", self._toggle_details)
        self.details_toggle.hide()
        self.details = QLabel()
        self.details.setObjectName("muted")
        self.details.setWordWrap(True)
        self.details.hide()
        self.progress = QProgressBar()
        self.progress.hide()
        self.problem = ProblemBox()

        self.restart_box = card()
        rb = QVBoxLayout(self.restart_box)
        rb.setContentsMargins(18, 16, 18, 16)
        self.restart_text = label("", wrap=True)
        rb.addWidget(self.restart_text)
        row = QHBoxLayout()
        self.restart_now = button(tr("updates.restart_now"), "primary", self._restart)
        self.later = button(tr("updates.later"), None, self.restart_box.hide)
        row.addWidget(self.restart_now)
        row.addWidget(self.later)
        row.addStretch()
        rb.addLayout(row)
        self.restart_box.hide()
        self._driver_timer = QTimer(self, interval=10_000)
        self._driver_timer.timeout.connect(self._check_restart)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(label(tr("nav.updates"), "pageTitle"))
        lay.addWidget(self.status)
        lay.addWidget(self.why)
        lay.addWidget(self.go)
        lay.addWidget(self.progress)
        lay.addWidget(self.problem)
        lay.addWidget(self.restart_box)
        lay.addWidget(self.details_toggle)
        lay.addWidget(self.details)
        lay.addStretch()

    # --- check ----------------------------------------------------------------------

    def check(self):
        self.status.setText(tr("updates.checking"))
        self.go.hide()
        self.details_toggle.hide()
        self.details.hide()
        self.problem.hide()
        self.jobs.query(self.hub.update_plan, self._show_plan)

    def _show_plan(self, plan: UpdatePlan):
        self.plan = plan
        if plan.empty:
            self.status.setText(tr("updates.none"))
            self.go.hide()
            self.details_toggle.hide()
            return
        self.status.setText(tr("updates.some", count=plan.count, size=_size(plan)))
        self.go.show()
        self.go.setEnabled(True)
        self.details_toggle.show()
        self.details.setText(
            "\n".join(
                f"• {i.name}" + (f"  {i.new_version}" if i.new_version else "") for i in plan.items
            )
        )

    def _toggle_details(self):
        self.details.setVisible(not self.details.isVisible())

    # --- apply ----------------------------------------------------------------------

    def _apply(self):
        plan = self.plan
        self.go.setEnabled(False)
        self.problem.hide()
        self.status.setText(tr("updates.running"))
        self.progress.setRange(0, 0)
        self.progress.show()

        def progress(pct, _status):
            if pct is None:
                self.progress.setRange(0, 0)
            else:
                self.progress.setRange(0, 100)
                self.progress.setValue(int(pct))

        def done(result: Result):
            self.progress.hide()
            if not result.ok:
                self.problem.show_result(result)
                self.check()
                return
            self.applied = plan
            self.status.setText(tr("updates.done"))
            self.go.hide()
            self.details_toggle.hide()
            self.details.hide()
            self._check_restart()

        self.jobs.change(
            lambda p, cancel: self.hub.apply(plan, p, cancel),
            progress,
            done,
            lambda err: done(Result(Problem.UNKNOWN, err)),
        )

    # --- restart (offered, never automatic) -------------------------------------------

    def _check_restart(self):
        plan = self.applied
        if plan is None:
            return
        state = restart_state(plan.needs_restart, new_kernels(plan.items), self.driver_probe())
        if state is RestartState.NOT_NEEDED:
            self._driver_timer.stop()
            self.restart_box.hide()
        elif state is RestartState.WAIT_FOR_DRIVER:
            self.restart_text.setText(tr("updates.wait_driver"))
            self.restart_now.setEnabled(False)
            self.restart_box.show()
            self._driver_timer.start()
        else:
            self._driver_timer.stop()
            self.restart_text.setText(tr("updates.restart_needed"))
            self.restart_now.setEnabled(True)
            self.restart_box.show()

    def _restart(self):
        result = self.restart()
        self.problem.show_result(result)


def _size(plan: UpdatePlan) -> str:
    return human_size(plan.download_size) if plan.download_size else "…"
