import math
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, blend_color
class AlbumArtWidget(QWidget):
    def __init__(self, size=180, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap = None
        self.setFixedSize(size, size)
    def set_pixmap(self, pm):
        self._pixmap = pm
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size
        path = QPainterPath()
        path.addRoundedRect(0, 0, s, s, 18, 18)
        p.setClipPath(path)
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            ox = (scaled.width() - s) // 2
            oy = (scaled.height() - s) // 2
            p.drawPixmap(0, 0, scaled, ox, oy, s, s)
            vig = QRadialGradient(s / 2, s / 2, s / 2 * 1.2)
            vig.setColorAt(0, QColor(0, 0, 0, 0))
            vig.setColorAt(1, QColor(0, 0, 0, 120))
            p.fillRect(0, 0, s, s, vig)
        else:
            accent = QColor(TH.accent)
            bg = QColor(TH.bg)
            grad = QLinearGradient(0, 0, s, s)
            grad.setColorAt(0, blend_color(accent, bg, 0.35))
            grad.setColorAt(1, blend_color(accent, bg, 0.75))
            p.fillRect(0, 0, s, s, grad)
            p.setPen(QColor(255, 255, 255, 120))
            p.setFont(QFont("Segoe UI Symbol", s // 5))
            p.drawText(QRect(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "♪")
class WaveformWidget(QWidget):
    def __init__(self, w=80, h=32, parent=None):
        super().__init__(parent)
        self._bars = [4.0] * 12
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self.setFixedSize(w, h)
    def start(self):
        self._timer.start(30)
    def stop(self):
        self._timer.stop()
        self._bars = [4.0] * 12
        self.update()
    def _step(self):
        self._tick += 1
        for i in range(12):
            tgt = 4 + 20 * abs(math.sin(self._tick * 0.07 + i * 0.7))
            self._bars[i] = self._bars[i] * 0.7 + tgt * 0.3
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        bw, gap = 4, 2
        ox = (W - 12 * (bw + gap) + gap) // 2
        accent = QColor(TH.accent)
        orange = QColor(TH.orange)
        for i, h in enumerate(self._bars):
            x = ox + i * (bw + gap)
            c = blend_color(accent, orange, i / 11)
            path = QPainterPath()
            path.addRoundedRect(x, H - h, bw, h, 2, 2)
            p.fillPath(path, c)
class VisualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars = [4.0] * 32
        self._tick = 0
        self._energy = 0.4
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(30)
        self.setFixedHeight(56)
    def set_energy(self, e: float):
        self._energy = e
    def _step(self):
        self._tick += 1
        for i in range(32):
            tgt = self._energy * (5 + 22 * abs(math.sin(self._tick * 0.055 + i * 0.52)))
            self._bars[i] = self._bars[i] * 0.75 + tgt * 0.25
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        n, bw, gap = 32, 9, 3
        ox = (W - n * (bw + gap) + gap) // 2
        accent = QColor(TH.accent)
        orange = QColor(TH.orange)
        bg = QColor(TH.bg)
        for i, h in enumerate(self._bars):
            x = ox + i * (bw + gap)
            c = blend_color(accent, orange, i / n)
            path = QPainterPath()
            path.addRoundedRect(x, H - h - 4, bw, h, 2, 2)
            p.fillPath(path, c)
            rh = max(1, h * 0.18)
            p.fillRect(int(x), H - 2, bw, int(rh), blend_color(c, bg, 0.72))
class RoundedCard(QFrame):
    def __init__(self, radius=14, parent=None):
        super().__init__(parent)
        self._radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width() - 1, rect.height() - 1, self._radius, self._radius)
        p.fillPath(path, QColor(TH.surface))
        p.setPen(QPen(QColor(TH.border), 1))
        p.drawPath(path)
class GlowButton(QPushButton):
    def __init__(self, text, color_hex=None, parent=None):
        super().__init__(text, parent)
        self._color_hex = color_hex or TH.accent
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        self._update_style()
    def set_color(self, color_hex: str):
        self._color_hex = color_hex
        self._update_style()
    def _update_style(self):
        c = self._color_hex
        c2 = blend_color(QColor(c), QColor("#ffffff"), 0.15).name()
        self.setStyleSheet(f"""
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {c},stop:1 {c2});
    color: #ffffff; border: none; border-radius: 12px;
    font-family: 'Segoe UI'; font-size: 13px; font-weight: 700; padding: 0 24px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {c2},stop:1 {c});
}}
QPushButton:pressed {{ opacity: 0.8; }}
QPushButton:disabled {{ background: {TH.border}; color: {TH.text3}; }}
""")
class IconButton(QPushButton):
    def __init__(self, icon_text, size=40, tooltip="", parent=None):
        super().__init__(icon_text, parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        self.setStyleSheet(f"""
QPushButton {{
    background: {TH.card}; color: {TH.text2};
    border: 1px solid {TH.border}; border-radius: {size // 2}px; font-size: 14px;
}}
QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}
QPushButton:pressed {{ background: {TH.bg}; }}
""")
class SeekSlider(QSlider):
    seek_requested = pyqtSignal(int)
    def __init__(self, color_hex=None, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._color = color_hex or TH.accent
        self.setRange(0, 1000)
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()
    def _apply_style(self):
        self.setStyleSheet(f"""
QSlider::groove:horizontal {{
    height: 5px; background: {TH.border}; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {self._color},stop:1 {TH.orange});
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 16px; height: 16px; margin: -6px 0;
    background: {self._color}; border-radius: 8px; border: 2px solid #ffffff;
}}
""")
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = int(event.position().x() / self.width() * self.maximum())
            val = max(0, min(val, self.maximum()))
            self.setValue(val)
            self.seek_requested.emit(val)
        super().mousePressEvent(event)
class VolumeSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(0, 100)
        self.setValue(100)
        self.setFixedWidth(100)
        self.setFixedHeight(16)
        self.setStyleSheet(f"""
QSlider::groove:horizontal {{
    height: 3px; background: {TH.border}; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{ background: {TH.text2}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 10px; height: 10px; margin: -4px 0;
    background: {TH.text}; border-radius: 5px;
}}
""")
class ElideLabel(QLabel):
    def __init__(self, text="", mode=Qt.TextElideMode.ElideMiddle, parent=None):
        super().__init__(text, parent)
        self._elide_mode = mode
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    def setText(self, text: str):
        self._full_text = text
        super().setText(text)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full_text, self._elide_mode, self.width())
        QLabel.setText(self, elided)
class FolderSidebarItem(QWidget):
    clicked = pyqtSignal(str)
    def __init__(self, folder: str, count: int, active: bool = False, parent=None):
        super().__init__(parent)
        self._folder = folder
        self._active = active
        self._hovered = False
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(8)
        icon = QLabel("📁")
        icon.setFixedWidth(20)
        icon.setStyleSheet("background: transparent; font-size: 14px;")
        name = os.path.basename(folder) or folder
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        name_lbl = QLabel(name if len(name) <= 22 else name[:19] + "…")
        name_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if active else QFont.Weight.Normal))
        name_lbl.setStyleSheet(f"color: {TH.text if active else TH.text2}; background: transparent;")
        cnt_lbl = QLabel(f"{count} files")
        cnt_lbl.setFont(QFont("Segoe UI", 8))
        cnt_lbl.setStyleSheet(f"color: {TH.accent if active else TH.text3}; background: transparent;")
        text_col.addWidget(name_lbl)
        text_col.addWidget(cnt_lbl)
        lay.addWidget(icon)
        lay.addLayout(text_col)
        lay.addStretch()
    def mousePressEvent(self, _):
        self.clicked.emit(self._folder)
    def enterEvent(self, _):
        self._hovered = True
        self.update()
    def leaveEvent(self, _):
        self._hovered = False
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._active:
            bg = blend_color(QColor(TH.accent), QColor(TH.surface), 0.15)
        elif self._hovered:
            bg = QColor(TH.card)
        else:
            bg = QColor(TH.surface)
        path = QPainterPath()
        path.addRoundedRect(2, 2, self.width() - 4, self.height() - 4, 8, 8)
        p.fillPath(path, bg)
        if self._active:
            p.fillRect(0, 8, 3, self.height() - 16, QColor(TH.accent))
class _VideoThumbLoader(QThread):
    loaded = pyqtSignal(QPixmap)
    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self._filepath = filepath
    def run(self):
        from utils.media import get_video_thumbnail
        pm = get_video_thumbnail(self._filepath)
        if pm and not pm.isNull():
            self.loaded.emit(pm)
class TrackRowWidget(QWidget):
    clicked = pyqtSignal(int)
    dbl_clicked = pyqtSignal(int)
    info_requested = pyqtSignal(int)
    fav_toggled = pyqtSignal(int)
    def __init__(self, idx: int, filepath: str, active: bool, playing: bool, parent=None):
        super().__init__(parent)
        self._idx = idx
        self._active = active
        self._hovered = False
        self._filepath = filepath
        from core.favorites import FavoritesManager
        self._fav_mgr = FavoritesManager.get()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(10)
        self._thumb = QLabel()
        self._thumb.setFixedSize(48, 48)
        self._thumb.setStyleSheet(f"border-radius: 8px; background: {TH.border};")
        layout.addWidget(self._thumb)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name = os.path.splitext(os.path.basename(filepath))[0]
        short = name if len(name) <= 40 else name[:37] + "…"
        self._title_lbl = QLabel(short)
        self._title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if active else QFont.Weight.Normal))
        self._title_lbl.setStyleSheet(f"color: {TH.text if active else TH.text2}; background: transparent;")
        self._sub_lbl = QLabel(f"Track {idx + 1:02d}")
        self._sub_lbl.setFont(QFont("Segoe UI", 8))
        self._sub_lbl.setStyleSheet(f"color: {TH.accent if active else TH.text3}; background: transparent;")
        text_col.addWidget(self._title_lbl)
        text_col.addWidget(self._sub_lbl)
        layout.addLayout(text_col)
        layout.addStretch()
        if active and playing:
            ind = QLabel("▶")
            ind.setStyleSheet(f"color: {TH.accent}; background: transparent; font-size: 12px;")
            layout.addWidget(ind)
        self._fav_btn = QPushButton("★" if self._fav_mgr.is_fav(filepath) else "☆")
        self._fav_btn.setFixedSize(28, 28)
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn.setToolTip("Toggle Favorite")
        self._update_fav_style()
        self._fav_btn.clicked.connect(self._on_fav_click)
        layout.addWidget(self._fav_btn)
        info_btn = QPushButton("ℹ")
        info_btn.setFixedSize(28, 28)
        info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        info_btn.setToolTip("Track Info")
        info_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border}; border-radius: 14px; font-size: 13px; font-weight: bold; }}
QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}
""")
        info_btn.clicked.connect(lambda: self.info_requested.emit(self._idx))
        layout.addWidget(info_btn)
        self._draw_placeholder_track()
        QTimer.singleShot(0, self._load_thumb)
    def _draw_placeholder_track(self):
        img = QPixmap(48, 48)
        img.fill(Qt.GlobalColor.transparent)
        ptr = QPainter(img)
        ptr.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, 48, 48)
        g.setColorAt(0, blend_color(QColor(TH.accent), QColor(TH.bg), 0.4))
        g.setColorAt(1, blend_color(QColor(TH.accent), QColor(TH.bg), 0.75))
        path = QPainterPath()
        path.addRoundedRect(0, 0, 48, 48, 8, 8)
        ptr.fillPath(path, g)
        ptr.setPen(QColor(255, 255, 255, 80))
        ptr.setFont(QFont("Segoe UI Symbol", 18))
        ptr.drawText(QRect(0, 0, 48, 48), Qt.AlignmentFlag.AlignCenter, "♪")
        ptr.end()
        self._thumb.setPixmap(img)
    def _update_fav_style(self):
        is_fav = self._fav_mgr.is_fav(self._filepath)
        color = "#ffd60a" if is_fav else TH.text3
        self._fav_btn.setText("★" if is_fav else "☆")
        self._fav_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {color}; border: 1px solid {TH.border}; border-radius: 14px; font-size: 14px; }}
QPushButton:hover {{ background: {TH.border}; color: #ffd60a; }}
""")
    def _on_fav_click(self):
        self._fav_mgr.toggle(self._filepath)
        self._update_fav_style()
        self.fav_toggled.emit(self._idx)
    def _load_thumb(self):
        from utils.media import get_album_art
        pm = get_album_art(self._filepath)
        if pm and not pm.isNull():
            scaled = pm.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self._thumb.setPixmap(scaled)
    def mousePressEvent(self, _):
        self.clicked.emit(self._idx)
    def enterEvent(self, _):
        self._hovered = True
        self.update()
    def leaveEvent(self, _):
        self._hovered = False
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._active:
            bg = blend_color(QColor(TH.accent), QColor(TH.card), 0.2)
        elif self._hovered:
            bg = blend_color(QColor(TH.border), QColor(TH.card), 0.5)
        else:
            bg = QColor(TH.card)
        path = QPainterPath()
        path.addRoundedRect(4, 2, self.width() - 8, self.height() - 4, 10, 10)
        p.fillPath(path, bg)
class VideoRowWidget(QWidget):
    clicked = pyqtSignal(int)
    dbl_clicked = pyqtSignal(int)
    info_requested = pyqtSignal(int)
    fav_toggled = pyqtSignal(int)
    def __init__(self, idx, filepath, active, parent=None):
        super().__init__(parent)
        self._idx = idx
        self._active = active
        self._hovered = False
        self._filepath = filepath
        self._thumb_loader = None
        from core.favorites import FavoritesManager
        self._fav_mgr = FavoritesManager.get()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(10)
        self._thumb = QLabel()
        self._thumb.setFixedSize(96, 56)
        self._thumb.setStyleSheet(f"border-radius: 8px; background: {TH.border};")
        layout.addWidget(self._thumb)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name = os.path.splitext(os.path.basename(filepath))[0]
        short = name if len(name) <= 36 else name[:33] + "…"
        self._title = QLabel(short)
        self._title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold if active else QFont.Weight.Normal))
        self._title.setStyleSheet(f"color: {TH.text if active else TH.text2}; background: transparent;")
        self._sub = QLabel(f"Video {idx + 1:02d}  •  double-click to play")
        self._sub.setFont(QFont("Segoe UI", 8))
        self._sub.setStyleSheet(f"color: {TH.blue if active else TH.text3}; background: transparent;")
        text_col.addWidget(self._title)
        text_col.addWidget(self._sub)
        layout.addLayout(text_col)
        layout.addStretch()
        self._fav_btn = QPushButton("★" if self._fav_mgr.is_fav(filepath) else "☆")
        self._fav_btn.setFixedSize(28, 28)
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_btn.setToolTip("Toggle Favorite")
        self._update_fav_style()
        self._fav_btn.clicked.connect(self._on_fav_click)
        layout.addWidget(self._fav_btn)
        info_btn = QPushButton("ℹ")
        info_btn.setFixedSize(28, 28)
        info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        info_btn.setToolTip("Video Info")
        info_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border}; border-radius: 14px; font-size: 13px; font-weight: bold; }}
QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}
""")
        info_btn.clicked.connect(lambda: self.info_requested.emit(self._idx))
        layout.addWidget(info_btn)
        self._draw_placeholder_video()
        QTimer.singleShot(0, self._load_thumb)
    def _draw_placeholder_video(self):
        img = QPixmap(96, 56)
        img.fill(Qt.GlobalColor.transparent)
        ptr = QPainter(img)
        ptr.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, 96, 56)
        g.setColorAt(0, blend_color(QColor(TH.blue), QColor(TH.bg), 0.35))
        g.setColorAt(1, blend_color(QColor(TH.blue2), QColor(TH.bg), 0.65))
        path = QPainterPath()
        path.addRoundedRect(0, 0, 96, 56, 8, 8)
        ptr.fillPath(path, g)
        ptr.setPen(QColor(255, 255, 255, 100))
        ptr.setFont(QFont("Segoe UI Symbol", 22))
        ptr.drawText(QRect(0, 0, 96, 56), Qt.AlignmentFlag.AlignCenter, "▶")
        ptr.end()
        self._thumb.setPixmap(img)
    def _update_fav_style(self):
        is_fav = self._fav_mgr.is_fav(self._filepath)
        color = "#ffd60a" if is_fav else TH.text3
        self._fav_btn.setText("★" if is_fav else "☆")
        self._fav_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {color}; border: 1px solid {TH.border}; border-radius: 14px; font-size: 14px; }}
QPushButton:hover {{ background: {TH.border}; color: #ffd60a; }}
""")
    def _on_fav_click(self):
        self._fav_mgr.toggle(self._filepath)
        self._update_fav_style()
        self.fav_toggled.emit(self._idx)
    def _load_thumb(self):
        self._thumb_loader = _VideoThumbLoader(self._filepath, self)
        self._thumb_loader.loaded.connect(self._on_thumb_loaded)
        self._thumb_loader.start()
    def _on_thumb_loaded(self, pm: QPixmap):
        if not self.isVisible() and not pm.isNull():
            return
        scaled = pm.scaled(96, 56, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        ox = (scaled.width() - 96) // 2
        oy = (scaled.height() - 56) // 2
        cropped = scaled.copy(ox, oy, 96, 56)
        rounded = QPixmap(96, 56)
        rounded.fill(Qt.GlobalColor.transparent)
        ptr = QPainter(rounded)
        ptr.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 96, 56, 8, 8)
        ptr.setClipPath(path)
        ptr.drawPixmap(0, 0, cropped)
        ptr.end()
        self._thumb.setPixmap(rounded)
    def mousePressEvent(self, _):
        self.clicked.emit(self._idx)
    def mouseDoubleClickEvent(self, _):
        self.dbl_clicked.emit(self._idx)
    def enterEvent(self, _):
        self._hovered = True
        self.update()
    def leaveEvent(self, _):
        self._hovered = False
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._active:
            bg = blend_color(QColor(TH.blue), QColor(TH.card), 0.2)
        elif self._hovered:
            bg = blend_color(QColor(TH.border), QColor(TH.card), 0.5)
        else:
            bg = QColor(TH.card)
        path = QPainterPath()
        path.addRoundedRect(4, 2, self.width() - 8, self.height() - 4, 10, 10)
        p.fillPath(path, bg)
class ColorSwatch(QWidget):
    clicked = pyqtSignal(str)
    def __init__(self, hex_color, label="", active=False, parent=None):
        super().__init__(parent)
        self._hex = hex_color
        self._active = active
        self._hovered = False
        self.setFixedSize(52, 52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label or hex_color)
    def set_active(self, v):
        self._active = v
        self.update()
    def mousePressEvent(self, _):
        self.clicked.emit(self._hex)
    def enterEvent(self, _):
        self._hovered = True
        self.update()
    def leaveEvent(self, _):
        self._hovered = False
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._hex)
        path = QPainterPath()
        path.addRoundedRect(4, 4, 44, 44, 10, 10)
        p.fillPath(path, c)
        if self._active:
            p.setPen(QPen(QColor(TH.white), 2.5))
            p.drawPath(path)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 220))
            p.drawEllipse(18, 18, 16, 16)
            p.setPen(QPen(c, 2.5))
            p.drawLine(21, 26, 24, 29)
            p.drawLine(24, 29, 30, 23)
        elif self._hovered:
            p.setPen(QPen(QColor(255, 255, 255, 160), 2))
            p.drawPath(path)