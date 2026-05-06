import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, blend_color
from ui.widgets import RoundedCard
from ui.dialogs import show_shortcuts_dialog
from utils.resources import get_logo_path

CARD_ITEMS = [
    ("🔍", "Search",   "YouTube Music", "search",   "#f72585"),
    ("⬇",  "Download", "MP3 & MP4",     "download", "#e63946"),
    ("♪",  "Music",    "Player",        "music",    "#ff9f1c"),
    ("▶",  "Video",    "Player",        "video",    "#4361ee"),
]

TRENDING_TERMS = [
    "Top Hits 2024", "New Music", "Chill Vibes",
    "EDM Mix", "Hip Hop", "Pop Playlist",
]


class TrendingChip(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        fm = QFontMetrics(QFont("Segoe UI", 9))
        self.setFixedSize(fm.horizontalAdvance(text) + 28, 30)

    def mousePressEvent(self, _):
        self.clicked.emit(self._text)

    def enterEvent(self, _):
        self._hovered = True
        self.update()

    def leaveEvent(self, _):
        self._hovered = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 2.5, self.width() - 1, self.height() - 5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        if self._hovered:
            p.fillPath(path, QColor(TH.accent))
            p.setPen(QColor(TH.white))
        else:
            p.fillPath(path, QColor(TH.card))
            p.setPen(QPen(QColor(TH.border), 1))
            p.drawPath(path)
            p.setPen(QColor(TH.text2))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._text)


class HeroBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(190)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 20, 0, 12)
        lay.setSpacing(6)

        # real app logo
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent;")
        logo_path = get_logo_path()
        if os.path.isfile(logo_path):
            pm = QPixmap(logo_path).scaled(
                90, 90,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(pm)
        else:
            logo_lbl.setText("▶")
            logo_lbl.setFont(QFont("Segoe UI Symbol", 38))
            logo_lbl.setStyleSheet(f"color: {TH.accent}; background: transparent;")
        lay.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("MusicHub")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TH.text}; background: transparent;")
        lay.addWidget(title)

        sub = QLabel("Search  •  Stream  •  Download  •  Enjoy")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        lay.addWidget(sub)

    def start(self): pass
    def stop(self):  pass

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0, blend_color(QColor(TH.accent), QColor(TH.bg), 0.82))
        g.setColorAt(1, QColor(TH.bg))
        p.fillRect(0, 0, W, H, g)


class HomeScreen(QWidget):
    navigate     = pyqtSignal(str)
    search_query = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self._hero = HeroBanner()
        main.addWidget(self._hero)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        body = QWidget()
        body.setStyleSheet(f"background: {TH.bg};")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 16, 24, 16)
        body_lay.setSpacing(0)

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (icon, title, sub, dest, color) in enumerate(CARD_ITEMS):
            grid.addWidget(self._make_card(icon, title, sub, dest, color), i // 2, i % 2)
        body_lay.addLayout(grid)

        body_lay.addSpacing(18)
        tr_lbl = QLabel("TRENDING SEARCHES")
        tr_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        tr_lbl.setStyleSheet(f"color: {TH.text3}; background: transparent; letter-spacing: 2px;")
        body_lay.addWidget(tr_lbl)
        body_lay.addSpacing(6)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        chips_row.setContentsMargins(0, 0, 0, 0)
        for term in TRENDING_TERMS:
            chip = TrendingChip(term)
            chip.clicked.connect(self._on_chip)
            chips_row.addWidget(chip)
        chips_row.addStretch()
        body_lay.addLayout(chips_row)

        body_lay.addSpacing(18)
        qs_lbl = QLabel("QUICK START")
        qs_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        qs_lbl.setStyleSheet(f"color: {TH.text3}; background: transparent;")
        body_lay.addWidget(qs_lbl)
        body_lay.addSpacing(6)

        hint = RoundedCard(radius=12)
        hint.setFixedHeight(58)
        hint.setCursor(Qt.CursorShape.PointingHandCursor)
        hint.mousePressEvent = lambda _: self.navigate.emit("search")
        h_lay = QHBoxLayout(hint)
        h_lay.setContentsMargins(16, 0, 16, 0)
        h_lay.setSpacing(12)

        ic = QLabel("🔍")
        ic.setFont(QFont("Segoe UI Symbol", 20))
        ic.setStyleSheet(f"color: {TH.accent}; background: transparent;")

        txt = QVBoxLayout()
        txt.setSpacing(2)
        l1 = QLabel("Search YouTube & stream or download instantly")
        l1.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        l1.setStyleSheet(f"color: {TH.text}; background: transparent;")
        l2 = QLabel("Play directly · Download MP3 or MP4 · Save favorites")
        l2.setFont(QFont("Segoe UI", 9))
        l2.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        txt.addWidget(l1)
        txt.addWidget(l2)

        h_lay.addWidget(ic)
        h_lay.addLayout(txt)
        h_lay.addStretch()
        body_lay.addWidget(hint)

        body_lay.addSpacing(10)
        kb_btn = QPushButton("⌨  View Keyboard Shortcuts")
        kb_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kb_btn.setFixedHeight(36)
        kb_btn.setStyleSheet(f"""
QPushButton {{
    background: {TH.card}; color: {TH.text2};
    border: 1px solid {TH.border}; border-radius: 10px;
    font-family: 'Segoe UI'; font-size: 10px; font-weight: 700;
}}
QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}
""")
        kb_btn.clicked.connect(lambda: show_shortcuts_dialog(self))
        body_lay.addWidget(kb_btn)
        body_lay.addStretch()

        scroll.setWidget(body)
        main.addWidget(scroll, 1)

    def _on_chip(self, term: str):
        self.search_query.emit(term)
        self.navigate.emit("search")

    def _make_card(self, icon, title, sub, dest, color):
        card = RoundedCard(radius=14)
        card.setFixedHeight(82)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda _, d=dest: self.navigate.emit(d)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 10, 16, 10)
        ic = QLabel(icon)
        ic.setFont(QFont("Segoe UI Symbol", 20))
        ic.setStyleSheet(f"color: {color}; background: transparent;")
        tl = QLabel(title)
        tl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        tl.setStyleSheet(f"color: {TH.text}; background: transparent;")
        sl = QLabel(sub)
        sl.setFont(QFont("Segoe UI", 8))
        sl.setStyleSheet(f"color: {color}; background: transparent;")
        lay.addWidget(ic)
        lay.addWidget(tl)
        lay.addWidget(sl)
        return card

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(TH.bg))

    def on_show(self):  self._hero.start()
    def on_hide(self):  self._hero.stop()
    def showEvent(self, _): self._hero.start()
    def hideEvent(self, _): self._hero.stop()
