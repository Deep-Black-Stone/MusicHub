from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH
from utils.resources import get_logo_path
import os


class HeaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        logo_lbl = QLabel()
        logo_lbl.setFixedSize(38, 38)
        logo_path = get_logo_path()
        if os.path.isfile(logo_path):
            pm = QPixmap(logo_path).scaled(
                38, 38,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(pm)
        else:
            logo_lbl.setText("▶")
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_lbl.setStyleSheet(
                f"background: {TH.accent}; border-radius: 12px; color: white; font-size: 16px;"
            )

        title_col = QVBoxLayout()
        title_col.setSpacing(1)

        t1 = QLabel("MusicHub")
        t1.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t1.setStyleSheet(f"color: {TH.text}; background: transparent;")

        t2 = QLabel("YouTube Downloader & Media Player")
        t2.setFont(QFont("Segoe UI", 8))
        t2.setStyleSheet(f"color: {TH.text2}; background: transparent;")

        title_col.addWidget(t1)
        title_col.addWidget(t2)

        lay.addWidget(logo_lbl)
        lay.addLayout(title_col)
        lay.addStretch()

    def set_wave(self, on: bool):
        pass  # waveform removed

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(TH.surface))
        p.setPen(QColor(TH.border))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
