"""SKJ look: dark sidebar layout like ClamGuard, SKJ palette (spec §5)."""

C = {
    "BG": "#0f1724",
    "SURFACE": "#162133",
    "RAISED": "#1e2c43",
    "LINE": "#2a3a55",
    "TEXT": "#e8eef7",
    "MUTED": "#93a4bd",
    "BLUE": "#2563eb",  # SKJ blue
    "TEAL": "#14b8a6",  # SKJ teal
    "OK": "#3fcf8e",
    "WARN": "#f2b544",
    "BAD": "#f0616d",
}

QSS = """
QWidget { color: @TEXT; font-size: 11pt; }
QWidget#root { background: @BG; }
QLabel { background: transparent; }
QWidget#sidebar { background: @SURFACE; border-right: 1px solid @LINE; }
QLabel#brand { font-size: 16pt; font-weight: 800; }
QLabel#muted { color: @MUTED; }
QLabel#pageTitle { font-size: 20pt; font-weight: 800; }
QLabel#heroTitle { font-size: 24pt; font-weight: 800; }
QLabel#appName { font-size: 13pt; font-weight: 700; }
QLabel#status { font-size: 13pt; font-weight: 600; }
QListWidget#nav { background: transparent; border: none; outline: 0; font-size: 12pt; }
QListWidget#nav::item { padding: 12px 10px; border-radius: 10px; margin: 2px 0; color: @MUTED; }
QListWidget#nav::item:hover { background: @RAISED; color: @TEXT; }
QListWidget#nav::item:selected { background: @RAISED; color: @TEXT; border-left: 3px solid @TEAL; }
QFrame#card { background: @SURFACE; border: 1px solid @LINE; border-radius: 14px; }
QFrame#hero { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 @BLUE, stop:1 @TEAL);
              border-radius: 22px; }
QFrame#hero QLabel { color: white; }
QLineEdit#search { background: @SURFACE; border: 2px solid @LINE; border-radius: 14px;
                   padding: 12px 16px; font-size: 13pt; }
QLineEdit#search:focus { border-color: @BLUE; }
QPushButton { background: @RAISED; border: 1px solid @LINE; border-radius: 10px;
              padding: 9px 18px; font-weight: 600; }
QPushButton:hover { border-color: @TEAL; }
QPushButton:disabled { color: @MUTED; }
QPushButton#primary { background: @BLUE; border: none; color: white; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#big { background: @BLUE; border: none; color: white; font-size: 14pt;
                  padding: 16px 32px; border-radius: 14px; }
QPushButton#big:hover { background: #1d4ed8; }
QPushButton#danger { background: transparent; border: 1px solid @BAD; color: @BAD; }
QPushButton#link { background: transparent; border: none; color: @TEAL; padding: 4px;
                   text-align: left; }
QProgressBar { background: @RAISED; border: none; border-radius: 6px; height: 12px;
               text-align: center; color: transparent; }
QProgressBar::chunk { background: @TEAL; border-radius: 6px; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QPlainTextEdit { background: @SURFACE; border: 1px solid @LINE; border-radius: 10px;
                 font-family: monospace; font-size: 9pt; }
"""


def stylesheet() -> str:
    qss = QSS
    for key in sorted(C, key=len, reverse=True):
        qss = qss.replace("@" + key, C[key])
    return qss
