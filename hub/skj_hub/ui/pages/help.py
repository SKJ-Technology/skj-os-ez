"""Help & safety: the Notion "don't be scared of commands" message + red flags."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QVBoxLayout, QWidget

from skj_hub.i18n import tr
from skj_hub.ui.widgets import button, card, label

REPORT_URL = "https://github.com/SKJ-Technology/skj-os-ez/issues"


class HelpPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(label(tr("help.title"), "pageTitle"))
        for title, body in (
            ("help.commands_title", "help.commands"),
            ("help.flags_title", "help.flags"),
        ):
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(18, 16, 18, 16)
            cl.addWidget(label(tr(title), "appName"))
            cl.addWidget(label(tr(body), wrap=True))
            lay.addWidget(c)
        lay.addWidget(
            button(tr("help.report"), "primary", lambda: QDesktopServices.openUrl(QUrl(REPORT_URL)))
        )
        lay.addStretch()
