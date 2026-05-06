from PyQt6.QtGui import *
from PyQt6.QtCore import *
from utils.config import load_config, save_config
ACCENT_PRESETS = {
    "Red": "#e63946",
    "Orange": "#ff9f1c",
    "Blue": "#4361ee",
    "Purple": "#7b2fbe",
    "Green": "#06d6a0",
    "Pink": "#f72585",
    "Cyan": "#4cc9f0",
    "Gold": "#ffd60a",
}
DARK_BASE = {"bg": "#0d0d1a", "surface": "#12121f", "card": "#181828", "border": "#252540", "text": "#eef0f2", "text2": "#7777aa", "text3": "#383856"}
LIGHT_BASE = {"bg": "#f0f2f8", "surface": "#ffffff", "card": "#e8eaf2", "border": "#c8cce0", "text": "#1a1a2e", "text2": "#5555aa", "text3": "#aaaacc"}
AMOLED_BASE = {"bg": "#000000", "surface": "#0a0a0a", "card": "#111111", "border": "#1e1e1e", "text": "#ffffff", "text2": "#888888", "text3": "#333333"}
MIDNIGHT_BASE = {"bg": "#0a0e1a", "surface": "#0f1525", "card": "#141d33", "border": "#1e2a45", "text": "#dde8ff", "text2": "#6677aa", "text3": "#2a3555"}
THEME_MODES = {"Dark": DARK_BASE, "Light": LIGHT_BASE, "AMOLED": AMOLED_BASE, "Midnight": MIDNIGHT_BASE}
def blend_color(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(c1.red() * (1 - t) + c2.red() * t),
        int(c1.green() * (1 - t) + c2.green() * t),
        int(c1.blue() * (1 - t) + c2.blue() * t),
    )
class ThemeEngine:
    _instance = None
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = ThemeEngine()
        return cls._instance
    def __init__(self):
        cfg = load_config()
        self._mode = cfg.get("theme_mode", "Dark")
        self._accent = cfg.get("theme_accent", "#e63946")
        self._font_size = int(cfg.get("theme_font_size", 10))
        self._border_radius = int(cfg.get("theme_border_radius", 12))
        self._apply_base()
    def _apply_base(self):
        base = THEME_MODES.get(self._mode, DARK_BASE)
        self.bg = base["bg"]
        self.surface = base["surface"]
        self.card = base["card"]
        self.border = base["border"]
        self.text = base["text"]
        self.text2 = base["text2"]
        self.text3 = base["text3"]
        self.accent = self._accent
        a = QColor(self._accent)
        self.accent2 = blend_color(a, QColor("#ffffff"), 0.2).name()
        self.orange = "#ff9f1c"
        self.blue = "#4361ee"
        self.blue2 = "#4cc9f0"
        self.purple = "#7b2fbe"
        self.green = "#06d6a0"
        self.white = "#ffffff"
    def set_mode(self, mode):
        self._mode = mode
        self._apply_base()
        save_config({"theme_mode": mode})
    def set_accent(self, hex_color):
        self._accent = hex_color
        self._apply_base()
        save_config({"theme_accent": hex_color})
    def set_font_size(self, size):
        self._font_size = size
        save_config({"theme_font_size": size})
    def set_border_radius(self, r):
        self._border_radius = r
        save_config({"theme_border_radius": r})
    @property
    def font_size(self): return self._font_size
    @property
    def border_radius(self): return self._border_radius
    @property
    def mode(self): return self._mode
    @property
    def accent_hex(self): return self._accent
    def qss(self):
        return f"""
QMainWindow, QWidget {{ background: {self.bg}; color: {self.text}; font-family: 'Segoe UI'; font-size: {self.font_size}pt; }}
QScrollBar:vertical {{ background: {self.bg}; width: 6px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {self.border}; border-radius: 3px; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
QMessageBox {{ background: {self.surface}; }}
QDialog {{ background: {self.bg}; color: {self.text}; }}
QToolTip {{ background: {self.surface}; color: {self.text}; border: 1px solid {self.border}; padding: 4px; }}
"""
TH = ThemeEngine.get()
