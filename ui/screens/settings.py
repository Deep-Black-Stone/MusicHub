import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, ThemeEngine, THEME_MODES, ACCENT_PRESETS, blend_color
from ui.widgets import RoundedCard, GlowButton, ElideLabel, ColorSwatch
from utils.config import load_config, save_config, CONFIG_FILE
from core.youtube import CookieImportWorker, cookies_exist, clear_cookies
class ThemePreviewCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(0, 0, W, H, TH.border_radius, TH.border_radius)
        p.fillPath(path, QColor(TH.surface))
        p.setPen(QPen(QColor(TH.border), 1))
        p.drawPath(path)
        accent = QColor(TH.accent)
        bar_path = QPainterPath()
        bar_path.addRoundedRect(14, 14, 90, 10, 5, 5)
        g = QLinearGradient(14, 0, 104, 0)
        g.setColorAt(0, accent)
        g.setColorAt(1, blend_color(accent, QColor(TH.white), 0.3))
        p.fillPath(bar_path, g)
        for i, col in enumerate([TH.text, TH.text2, TH.text3]):
            r = QPainterPath()
            r.addRoundedRect(14, 34 + i * 14, 40 + i * 20, 8, 4, 4)
            p.fillPath(r, QColor(col))
        btn = QPainterPath()
        btn.addRoundedRect(W - 74, H - 30, 60, 22, 8, 8)
        p.fillPath(btn, accent)
        p.setPen(QColor(255, 255, 255, 220))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(QRect(W - 74, H - 30, 60, 22), Qt.AlignmentFlag.AlignCenter, "Button")
class SettingsScreen(QWidget):
    theme_changed = pyqtSignal()
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._cookie_worker = None
        self._build()
    def _section(self, lay, text):
        lbl = QLabel(text.upper())
        lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {TH.text3}; letter-spacing: 2px; background: transparent;")
        lay.addWidget(lbl)
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {TH.bg}; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setStyleSheet(f"background: {TH.bg};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 20, 28, 24)
        lay.setSpacing(14)
        self._section(lay, "Theme Preview")
        self._preview = ThemePreviewCard()
        lay.addWidget(self._preview)
        self._section(lay, "Color Mode")
        mode_card = RoundedCard(radius=12)
        mode_lay = QVBoxLayout(mode_card)
        mode_lay.setContentsMargins(16, 14, 16, 14)
        mode_lay.setSpacing(8)
        self._mode_btns = {}
        mode_row1 = QHBoxLayout()
        mode_row1.setSpacing(8)
        mode_row2 = QHBoxLayout()
        mode_row2.setSpacing(8)
        for i, mode in enumerate(THEME_MODES.keys()):
            btn = QPushButton(mode)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self._set_mode(m))
            self._mode_btns[mode] = btn
            (mode_row1 if i < 2 else mode_row2).addWidget(btn)
        mode_lay.addLayout(mode_row1)
        mode_lay.addLayout(mode_row2)
        lay.addWidget(mode_card)
        self._update_mode_btns()
        self._section(lay, "Accent Color")
        accent_card = RoundedCard(radius=12)
        accent_outer = QVBoxLayout(accent_card)
        accent_outer.setContentsMargins(16, 14, 16, 14)
        accent_outer.setSpacing(10)
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(6)
        self._swatches = {}
        for name, hex_c in ACCENT_PRESETS.items():
            sw = ColorSwatch(hex_c, name, hex_c.lower() == TH.accent_hex.lower())
            sw.clicked.connect(self._set_accent)
            self._swatches[hex_c] = sw
            swatch_row.addWidget(sw)
        swatch_row.addStretch()
        accent_outer.addLayout(swatch_row)
        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        custom_lbl = QLabel("Custom:")
        custom_lbl.setFont(QFont("Segoe UI", 9))
        custom_lbl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        self._custom_hex = QLineEdit(TH.accent_hex)
        self._custom_hex.setFixedHeight(32)
        self._custom_hex.setMaxLength(7)
        self._custom_hex.setPlaceholderText("#rrggbb")
        self._custom_hex.setStyleSheet(f"""
QLineEdit {{ background: {TH.card}; color: {TH.text}; border: 1px solid {TH.border}; border-radius: 8px; font-family: 'Consolas'; font-size: 11px; padding: 0 8px; }}
QLineEdit:focus {{ border-color: {TH.accent}; }}
""")
        self._custom_swatch = QLabel()
        self._custom_swatch.setFixedSize(32, 32)
        self._custom_swatch.setStyleSheet(f"background: {TH.accent_hex}; border-radius: 8px;")
        self._custom_hex.textChanged.connect(self._on_custom_hex)
        apply_custom = QPushButton("Apply")
        apply_custom.setFixedSize(64, 32)
        apply_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_custom.setStyleSheet(f"""
QPushButton {{ background: {TH.accent}; color: white; border: none; border-radius: 8px; font-family: 'Segoe UI'; font-size: 10px; font-weight: 700; }}
QPushButton:hover {{ background: {TH.accent2}; }}
""")
        apply_custom.clicked.connect(self._apply_custom_hex)
        custom_row.addWidget(custom_lbl)
        custom_row.addWidget(self._custom_swatch)
        custom_row.addWidget(self._custom_hex, 1)
        custom_row.addWidget(apply_custom)
        accent_outer.addLayout(custom_row)
        lay.addWidget(accent_card)
        self._section(lay, "Font Size")
        font_card = RoundedCard(radius=12)
        font_lay = QVBoxLayout(font_card)
        font_lay.setContentsMargins(16, 14, 16, 14)
        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        self._font_btns = {}
        for size, label in [(9, "Small"), (10, "Normal"), (11, "Large"), (13, "X-Large")]:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, s=size: self._set_font_size(s))
            self._font_btns[size] = btn
            font_row.addWidget(btn)
        font_lay.addLayout(font_row)
        lay.addWidget(font_card)
        self._update_font_btns()
        self._section(lay, "Border Radius")
        radius_card = RoundedCard(radius=12)
        radius_lay = QVBoxLayout(radius_card)
        radius_lay.setContentsMargins(16, 14, 16, 14)
        radius_row = QHBoxLayout()
        radius_row.setSpacing(8)
        self._radius_btns = {}
        for r, label in [(4, "Sharp"), (8, "Soft"), (12, "Round"), (18, "Pill")]:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, rv=r: self._set_radius(rv))
            self._radius_btns[r] = btn
            radius_row.addWidget(btn)
        radius_lay.addLayout(radius_row)
        lay.addWidget(radius_card)
        self._update_radius_btns()
        self._section(lay, "Window Size")
        win_card = RoundedCard(radius=12)
        win_lay = QHBoxLayout(win_card)
        win_lay.setContentsMargins(16, 12, 16, 12)
        win_lay.setSpacing(10)
        for label, w, h in [("Compact", 520, 720), ("Default", 680, 880), ("Wide", 860, 880), ("Large", 1024, 980)]:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, ww=w, hh=h: self._resize_window(ww, hh))
            btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border}; border-radius: 10px; font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; }}
QPushButton:hover {{ border-color: {TH.accent}; color: {TH.text}; }}
""")
            win_lay.addWidget(btn)
        lay.addWidget(win_card)
        self._section(lay, "Default Save Folder")
        path_card = RoundedCard(radius=12)
        path_card.setFixedHeight(50)
        path_lay = QHBoxLayout(path_card)
        path_lay.setContentsMargins(16, 0, 10, 0)
        self._path_lbl = ElideLabel(self._app.save_path)
        self._path_lbl.setFont(QFont("Segoe UI", 9))
        self._path_lbl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(72, 34)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.border}; color: {TH.text2}; border: none; border-radius: 8px; font-family: 'Segoe UI'; font-size: 10px; font-weight: 700; }}
QPushButton:hover {{ background: {TH.card}; color: {TH.text}; }}
""")
        browse_btn.clicked.connect(self._browse)
        path_lay.addWidget(self._path_lbl, 1)
        path_lay.addWidget(browse_btn)
        lay.addWidget(path_card)
        self._section(lay, "YouTube Authentication")
        yt_card = RoundedCard(radius=12)
        yt_lay = QVBoxLayout(yt_card)
        yt_lay.setContentsMargins(16, 14, 16, 14)
        yt_lay.setSpacing(10)
        yt_info = QLabel("Import browser cookies to bypass YouTube bot detection.\nYour browser must be logged into YouTube.")
        yt_info.setFont(QFont("Segoe UI", 9))
        yt_info.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        yt_info.setWordWrap(True)
        yt_lay.addWidget(yt_info)
        self._cookie_status = QLabel("")
        self._cookie_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._cookie_status.setStyleSheet(f"color: {TH.text3}; background: transparent;")
        self._cookie_status.setWordWrap(True)
        self._refresh_cookie_status()
        yt_lay.addWidget(self._cookie_status)
        browser_row = QHBoxLayout()
        browser_row.setSpacing(6)
        for browser in ["chrome", "firefox", "edge", "brave"]:
            btn = QPushButton(browser.capitalize())
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border}; border-radius: 10px;
    font-family: 'Segoe UI'; font-size: 10px; font-weight: 700; }}
QPushButton:hover {{ border-color: {TH.accent}; color: {TH.text}; }}
""")
            btn.clicked.connect(lambda _, b=browser: self._import_cookies(b))
            browser_row.addWidget(btn)
        yt_lay.addLayout(browser_row)
        clr_cookies_btn = QPushButton("🗑  Clear Saved Cookies")
        clr_cookies_btn.setFixedHeight(32)
        clr_cookies_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clr_cookies_btn.setStyleSheet(f"""
QPushButton {{ background: transparent; color: {TH.text3}; border: 1px solid {TH.border}; border-radius: 8px;
    font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; }}
QPushButton:hover {{ color: #e63946; border-color: #e63946; }}
""")
        clr_cookies_btn.clicked.connect(self._clear_cookies)
        yt_lay.addWidget(clr_cookies_btn)
        lay.addWidget(yt_card)
        self._section(lay, "About")
        about = RoundedCard(radius=12)
        about.setFixedHeight(120)
        ab_lay = QVBoxLayout(about)
        ab_lay.setContentsMargins(20, 14, 20, 14)
        ab_lay.setSpacing(5)
        row1 = QHBoxLayout()
        ic = QLabel("▶")
        ic.setFont(QFont("Segoe UI Symbol", 18))
        ic.setStyleSheet(f"color: {TH.accent}; background: transparent;")
        title = QLabel("MusicHub")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TH.text}; background: transparent;")
        row1.addWidget(ic)
        row1.addWidget(title)
        row1.addStretch()
        ab_lay.addLayout(row1)
        for txt, col in [("YouTube MP3 & MP4 Downloader + Media Player", TH.text2), ("Built with yt-dlp  •  Requires FFmpeg", TH.text3), ("Libraries: PyQt6, yt-dlp, mutagen, ffmpeg", TH.text3)]:
            l = QLabel(txt)
            l.setFont(QFont("Segoe UI", 9))
            l.setStyleSheet(f"color: {col}; background: transparent;")
            ab_lay.addWidget(l)
        lay.addWidget(about)
        self._section(lay, "Requirements")
        req = RoundedCard(radius=12)
        req.setFixedHeight(80)
        req_lay = QVBoxLayout(req)
        req_lay.setContentsMargins(16, 12, 16, 12)
        req_lay.setSpacing(5)
        for txt, col in [("pip install PyQt6 yt-dlp mutagen", TH.green), ("winget install ffmpeg  (or ffmpeg.org)", TH.text2), ("FFmpeg must be in your system PATH", TH.text3)]:
            l = QLabel(txt)
            l.setFont(QFont("Consolas", 9))
            l.setStyleSheet(f"color: {col}; background: transparent;")
            req_lay.addWidget(l)
        lay.addWidget(req)
        self._section(lay, "Danger Zone")
        danger_card = RoundedCard(radius=12)
        danger_lay = QVBoxLayout(danger_card)
        danger_lay.setContentsMargins(16, 12, 16, 12)
        danger_lay.setSpacing(8)
        rst = QPushButton("🗑  Reset All Settings & Theme")
        rst.setFixedHeight(44)
        rst.setCursor(Qt.CursorShape.PointingHandCursor)
        rst.setStyleSheet(f"""
QPushButton {{ background: transparent; color: #e63946; border: 1px solid {blend_color(QColor('#e63946'), QColor(TH.bg), 0.5).name()}; border-radius: 10px; font-family: 'Segoe UI'; font-size: 12px; font-weight: 700; }}
QPushButton:hover {{ background: {blend_color(QColor('#e63946'), QColor(TH.bg), 0.75).name()}; }}
""")
        rst.clicked.connect(self._reset)
        danger_lay.addWidget(rst)
        lay.addWidget(danger_card)
        lay.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
    def _refresh_cookie_status(self):
        if cookies_exist():
            self._cookie_status.setText("✅  Cookies saved — YouTube authentication active")
            self._cookie_status.setStyleSheet(f"color: {TH.green}; background: transparent; font-family: 'Segoe UI'; font-size: 8px; font-weight: 700;")
        else:
            self._cookie_status.setText("⚠  No cookies saved — searches may hit bot detection")
            self._cookie_status.setStyleSheet(f"color: {TH.text3}; background: transparent; font-family: 'Segoe UI'; font-size: 8px;")
    def _import_cookies(self, browser: str):
        if self._cookie_worker and self._cookie_worker.isRunning():
            return
        self._cookie_status.setText(f"⏳  Importing cookies from {browser.capitalize()}…")
        self._cookie_status.setStyleSheet(f"color: {TH.text2}; background: transparent; font-family: 'Segoe UI'; font-size: 8px;")
        self._cookie_worker = CookieImportWorker(browser)
        self._cookie_worker.done.connect(self._on_cookie_import_done)
        self._cookie_worker.start()
    def _on_cookie_import_done(self, success: bool, msg: str):
        self._refresh_cookie_status()
        if not success:
            self._cookie_status.setText(f"❌  {msg}")
            self._cookie_status.setStyleSheet(f"color: #e63946; background: transparent; font-family: 'Segoe UI'; font-size: 8px;")
    def _clear_cookies(self):
        clear_cookies()
        self._refresh_cookie_status()
    def _resize_window(self, w, h):
        win = self.window()
        if win:
            win.resize(w, h)
    def _update_mode_btns(self):
        for mode, btn in self._mode_btns.items():
            active = mode == TH.mode
            btn.setStyleSheet(f"""
QPushButton {{ background: {TH.accent if active else TH.card}; color: {'#ffffff' if active else TH.text2}; border: 1px solid {TH.accent if active else TH.border}; border-radius: 10px; font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; }}
QPushButton:hover {{ border-color: {TH.accent}; color: {TH.text}; }}
""")
    def _update_font_btns(self):
        for size, btn in self._font_btns.items():
            active = size == TH.font_size
            btn.setStyleSheet(f"""
QPushButton {{ background: {TH.accent if active else TH.card}; color: {'#ffffff' if active else TH.text2}; border: 1px solid {TH.accent if active else TH.border}; border-radius: 10px; font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; }}
QPushButton:hover {{ border-color: {TH.accent}; color: {TH.text}; }}
""")
    def _update_radius_btns(self):
        for r, btn in self._radius_btns.items():
            active = r == TH.border_radius
            btn.setStyleSheet(f"""
QPushButton {{ background: {TH.accent if active else TH.card}; color: {'#ffffff' if active else TH.text2}; border: 1px solid {TH.accent if active else TH.border}; border-radius: 10px; font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; }}
QPushButton:hover {{ border-color: {TH.accent}; color: {TH.text}; }}
""")
    def _update_swatches(self):
        for hex_c, sw in self._swatches.items():
            sw.set_active(hex_c.lower() == TH.accent_hex.lower())
    def _set_mode(self, mode):
        TH.set_mode(mode)
        self._update_mode_btns()
        self._preview.update()
        self.theme_changed.emit()
    def _set_accent(self, hex_c):
        TH.set_accent(hex_c)
        self._update_swatches()
        self._custom_hex.setText(hex_c)
        self._custom_swatch.setStyleSheet(f"background: {hex_c}; border-radius: 8px;")
        self._preview.update()
        self.theme_changed.emit()
    def _on_custom_hex(self, text):
        if len(text) == 7 and text.startswith("#"):
            c = QColor(text)
            if c.isValid():
                self._custom_swatch.setStyleSheet(f"background: {text}; border-radius: 8px;")
    def _apply_custom_hex(self):
        text = self._custom_hex.text().strip()
        if len(text) == 7 and text.startswith("#") and QColor(text).isValid():
            self._set_accent(text)
    def _set_font_size(self, size):
        TH.set_font_size(size)
        self._update_font_btns()
        self.theme_changed.emit()
    def _set_radius(self, r):
        TH.set_border_radius(r)
        self._update_radius_btns()
        self._preview.update()
        self.theme_changed.emit()
    def _browse(self):
        f = QFileDialog.getExistingDirectory(self, "Save folder", self._app.save_path)
        if f:
            self._app.save_path = f
            self._path_lbl.setText(f)
            save_config({"last_save_path": f})
    def _reset(self):
        reply = QMessageBox.question(self, "Reset", "Reset all settings and theme to defaults?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            os.remove(CONFIG_FILE)
        except Exception:
            pass
        TH.set_mode("Dark")
        TH.set_accent("#e63946")
        TH.set_font_size(10)
        TH.set_border_radius(12)
        self._app.save_path = os.path.expanduser("~/Downloads")
        self._path_lbl.setText(self._app.save_path)
        self._update_mode_btns()
        self._update_swatches()
        self._update_font_btns()
        self._update_radius_btns()
        self._custom_hex.setText("#e63946")
        self._preview.update()
        self.theme_changed.emit()
    def on_show(self):
        self._update_mode_btns()
        self._update_swatches()
        self._update_font_btns()
        self._update_radius_btns()
        self._preview.update()
        self._refresh_cookie_status()
    def on_hide(self):
        pass