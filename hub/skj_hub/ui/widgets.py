"""Building blocks shared by the pages."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from skj_hub.catalog.model import App, Offer
from skj_hub.i18n import problem_text, tr
from skj_hub.result import Result


def label(text: str = "", name: str | None = None, wrap: bool = False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def button(text: str, name: str | None = None, slot=None) -> QPushButton:
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    b.setCursor(Qt.PointingHandCursor)
    if slot:
        b.clicked.connect(slot)
    return b


def card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    return f


def source_text(offer: Offer) -> str:
    text = tr("apps.from", source=tr(f"source.{offer.source.value}"))
    if offer.developer_verified:
        text += " · " + tr("apps.verified")
    return text


def letter_tile(name: str, size: int = 56) -> QPixmap:
    """Rounded SKJ-gradient tile with the app's first letter (no icon found)."""
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#2563eb"))
    g.setColorAt(1, QColor("#14b8a6"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
    f = QFont()
    f.setPixelSize(int(size * 0.5))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(pm.rect(), Qt.AlignCenter, (name[:1] or "?").upper())
    p.end()
    return pm


def app_icon(offer: Offer) -> QIcon:
    if offer.icon:
        icon = QIcon(offer.icon) if offer.icon.startswith("/") else QIcon.fromTheme(offer.icon)
        if not icon.isNull():
            return icon
    for name in (offer.app_id or "", offer.ref, "application-x-executable"):
        icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    return QIcon()


class ProblemBox(QWidget):
    """One plain sentence, plus the technical text behind 'Details'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.text = label(wrap=True)
        self.text.setStyleSheet("color: #f0616d;")
        self.toggle = button(tr("common.details"), "link", self._toggle)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(120)
        self.details.hide()
        lay.addWidget(self.text)
        lay.addWidget(self.toggle, alignment=Qt.AlignLeft)
        lay.addWidget(self.details)
        self.hide()

    def show_result(self, result: Result):
        if result.ok:
            self.hide()
            return
        self.text.setText(problem_text(result.problem))
        self.details.setPlainText(result.details)
        self.toggle.setVisible(bool(result.details))
        self.details.hide()
        self.show()

    def _toggle(self):
        self.details.setVisible(not self.details.isVisible())


class AppCard(QFrame):
    """One app: icon, name, what it is, where it comes from, one main button."""

    install_requested = Signal(object, object)  # App, Offer (None = default)
    remove_requested = Signal(object)  # App

    def __init__(self, app: App, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.app = app
        offer = app.default

        icon = QLabel()
        qicon = app_icon(offer)
        icon.setPixmap(qicon.pixmap(QSize(56, 56)) if not qicon.isNull() else letter_tile(app.name))
        icon.setFixedSize(64, 64)
        # natural height only: word-wrapped labels in a scroll area otherwise
        # get stretched into a tall card
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        text = QVBoxLayout()
        text.addWidget(label(app.name, "appName"))
        text.addWidget(label(offer.summary, wrap=True))
        self.source = label(source_text(offer), "muted")
        text.addWidget(self.source)
        self.status = label("", "muted", wrap=True)
        self.status.hide()
        text.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.hide()
        text.addWidget(self.progress)
        self.problem = ProblemBox()
        text.addWidget(self.problem)
        text.setSpacing(4)
        text.addStretch()

        self.main_button = button("", "primary", self._main_clicked)
        self.others = button(tr("apps.other_versions"), "link")
        self.others.setVisible(len(app.offers) > 1 and not app.installed)
        menu = QMenu(self.others)
        for o in app.offers:
            if o is not offer:
                act = menu.addAction(source_text(o))
                act.triggered.connect(lambda _=False, o=o: self.install_requested.emit(self.app, o))
        self.others.setMenu(menu)

        right = QVBoxLayout()
        right.addWidget(self.main_button)
        right.addWidget(self.others)
        right.addStretch()

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)
        row.addWidget(icon, alignment=Qt.AlignTop)
        row.addLayout(text, 1)
        row.addLayout(right)
        self.refresh()

    def refresh(self):
        installed = self.app.installed
        self.main_button.setText(tr("apps.remove") if installed else tr("apps.install"))
        self.main_button.setObjectName("danger" if installed else "primary")
        self.main_button.style().unpolish(self.main_button)
        self.main_button.style().polish(self.main_button)

    def _main_clicked(self):
        if self.app.installed:
            self.remove_requested.emit(self.app)
        else:
            self.install_requested.emit(self.app, None)

    def busy(self, status: str):
        self.problem.hide()
        self.status.setText(status)
        self.status.show()
        self.progress.setRange(0, 0)
        self.progress.show()
        self.main_button.setEnabled(False)
        self.others.setEnabled(False)

    def set_progress(self, pct, status: str):
        if pct is None:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(int(pct))

    def finished(self, result: Result, done_text: str):
        self.progress.hide()
        self.main_button.setEnabled(True)
        self.others.setEnabled(True)
        if result.ok:
            self.status.setText(done_text)
        else:
            self.status.hide()
            self.problem.show_result(result)
        self.refresh()
