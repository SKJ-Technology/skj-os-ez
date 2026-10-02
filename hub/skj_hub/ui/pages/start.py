"""Start: hello, two big buttons, and whether updates are waiting."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from skj_hub.i18n import human_size, tr
from skj_hub.ui.widgets import button, label


class StartPage(QWidget):
    go_apps = Signal()
    go_updates = Signal()

    def __init__(self, hub, jobs, parent=None):
        super().__init__(parent)
        self.hub, self.jobs = hub, jobs

        hero = QFrame()
        hero.setObjectName("hero")
        h = QVBoxLayout(hero)
        h.setContentsMargins(32, 30, 32, 30)
        h.setSpacing(10)
        h.addWidget(label(tr("start.hello"), "heroTitle", wrap=True))
        h.addWidget(label(tr("start.sub"), wrap=True))

        row = QHBoxLayout()
        row.addWidget(button(tr("start.find_apps"), "big", self.go_apps.emit))
        row.addWidget(button(tr("start.check_updates"), "big", self.go_updates.emit))
        row.addStretch()

        self.updates = label("", "status", wrap=True)
        self.note = label(tr("start.unsupported"), "muted", wrap=True)
        self.note.setVisible(not hub.platform.supported)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)
        lay.addWidget(hero)
        lay.addLayout(row)
        lay.addWidget(self.updates)
        lay.addWidget(self.note)
        lay.addStretch()

    def refresh(self):
        self.updates.setText(tr("updates.checking"))

        def done(plan):
            if plan.empty:
                self.updates.setText(tr("updates.none"))
            else:
                size = human_size(plan.download_size) if plan.download_size else "…"
                self.updates.setText(tr("updates.some", count=plan.count, size=size))

        self.jobs.query(self.hub.update_plan, done)
