from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, blend_color

TABS = [
    ("home",     "⌂",  "Home"),
    ("search",   "🔍", "Search"),
    ("download", "⬇",  "Download"),
    ("music",    "♪",  "Music"),
    ("video",    "▶",  "Video"),
    ("settings", "⚙",  "Settings"),
]

TAB_COLORS = {
    "home":     "#e63946",
    "search":   "#f72585",
    "download": "#ff9f1c",
    "music":    "#06d6a0",
    "video":    "#4361ee",
    "settings": "#7b2fbe",
}


class NavBarWidget(QWidget):
    tab_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = "home"
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btns = {}
        for key, icon, label in TABS:
            btn = self._make_tab(key, icon, label)
            self._btns[key] = btn
            layout.addWidget(btn)

        self.set_active("home")

    def _make_tab(self, key, icon, label):
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(69)
        btn.clicked.connect(lambda _, k=key: self._click(k))

        inner = QVBoxLayout(btn)
        inner.setContentsMargins(0, 10, 0, 8)
        inner.setSpacing(2)

        ic_lbl = QLabel(icon)
        ic_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic_lbl.setFont(QFont("Segoe UI Symbol", 15))

        lb_lbl = QLabel(label)
        lb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))

        inner.addWidget(ic_lbl)
        inner.addWidget(lb_lbl)

        btn._icon_lbl  = ic_lbl
        btn._label_lbl = lb_lbl
        return btn

    def _click(self, key):
        self.set_active(key)
        self.tab_changed.emit(key)

    def set_active(self, key):
        self._active = key
        for k, btn in self._btns.items():
            active = k == key
            color  = TAB_COLORS.get(k, TH.accent)
            bg     = blend_color(QColor(color), QColor(TH.surface), 0.82).name() if active else TH.surface
            ic_c   = color if active else TH.text3
            lb_c   = color if active else TH.text3
            top_border = f"border-top: 2.5px solid {color};" if active else f"border-top: 1px solid {TH.border};"
            btn.setStyleSheet(
                f"QPushButton {{ background: {bg}; border: none; {top_border} }}"
            )
            btn._icon_lbl.setStyleSheet(f"color: {ic_c}; background: transparent;")
            btn._label_lbl.setStyleSheet(f"color: {lb_c}; background: transparent;")

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(0, 0, self.width(), 1, QColor(TH.border))
