import sys
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH
from utils.config import load_config, save_config
from utils.resources import get_icon_path, get_logo_path
from ui.header import HeaderWidget
from ui.navbar import NavBarWidget, TABS
from ui.screens.home import HomeScreen
from ui.screens.search import SearchScreen
from ui.screens.download import DownloadScreen
from ui.screens.music import MusicScreen
from ui.screens.video import VideoScreen
from ui.screens.settings import SettingsScreen
from ui.dialogs import show_shortcuts_dialog

APP_MIN_W, APP_MIN_H = 520, 620
APP_DEF_W, APP_DEF_H = 780, 920


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusicHub")
        self.setMinimumSize(APP_MIN_W, APP_MIN_H)

        icon_path = get_icon_path()
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        cfg = load_config()
        w = int(cfg.get("win_w", APP_DEF_W))
        h = int(cfg.get("win_h", APP_DEF_H))
        self.resize(w, h)

        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            cx = sg.center() - QPoint(w // 2, h // 2)
            self.move(max(sg.x(), cx.x()), max(sg.y(), cx.y()))

        self.save_path = cfg.get("last_save_path", os.path.expanduser("~/Downloads"))
        if not os.path.isdir(self.save_path):
            self.save_path = os.path.expanduser("~/Downloads")

        self._apply_qss()

        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        self._header = HeaderWidget()
        root_lay.addWidget(self._header)

        self._stack = QStackedWidget()
        root_lay.addWidget(self._stack, 1)

        self._nav = NavBarWidget()
        self._nav.tab_changed.connect(self.navigate)
        root_lay.addWidget(self._nav)

        self._screens = {
            "home": HomeScreen(),
            "search": SearchScreen(self),
            "download": DownloadScreen(self),
            "music": MusicScreen(self),
            "video": VideoScreen(self),
            "settings": SettingsScreen(self),
        }

        self._screens["home"].navigate.connect(self.navigate)
        self._screens["home"].search_query.connect(self._on_search_query)
        self._screens["download"].navigate_after.connect(self._on_download_done)
        self._screens["settings"].theme_changed.connect(self._on_theme_changed)

        for screen in self._screens.values():
            self._stack.addWidget(screen)

        self._current = None
        self.navigate("home")
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        keys = [t[0] for t in TABS]
        for i, key in enumerate(keys):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            shortcut.activated.connect(lambda k=key: self.navigate(k))
        QShortcut(QKeySequence("F1"), self).activated.connect(lambda: show_shortcuts_dialog(self))
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._global_open_file)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._global_search)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self._global_mute)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self._global_lyrics)
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self._global_download)
        QShortcut(QKeySequence("Ctrl+Shift+F"), self).activated.connect(self._global_fullscreen)
    def _global_open_file(self):
        if self._current in ("music", "video"):
            screen = self._screens[self._current]
            if hasattr(screen, "_add_folder"):
                screen._add_folder()
        else:
            self.navigate("music")
            QTimer.singleShot(200, lambda: self._screens["music"]._add_folder())
    def _global_search(self):
        self.navigate("search")
    def _global_mute(self):
        if self._current in ("music", "video"):
            screen = self._screens[self._current]
            if hasattr(screen, "_toggle_mute"):
                screen._toggle_mute()
    def _global_lyrics(self):
        if self._current == "music":
            s = self._screens["music"]
            if hasattr(s, "_toggle_lyrics"):
                s._toggle_lyrics()
        else:
            self.navigate("music")
    def _global_download(self):
        self.navigate("download")
    def _global_fullscreen(self):
        if self._current == "video":
            s = self._screens["video"]
            if hasattr(s, "_toggle_fullscreen"):
                s._toggle_fullscreen()

    def _apply_qss(self):
        extra_qss = f"""
QMainWindow, QWidget {{ background: {TH.bg}; color: {TH.text}; font-family: 'Segoe UI'; font-size: {TH.font_size}pt; }}
QScrollBar:vertical {{ background: {TH.bg}; width: 6px; margin: 0; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: {TH.border}; border-radius: 3px; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
QMessageBox {{ background: {TH.surface}; }}
QDialog {{ background: {TH.bg}; color: {TH.text}; }}
QToolTip {{ background: {TH.surface}; color: {TH.text}; border: 1px solid {TH.border}; padding: 4px; border-radius: 6px; }}
QLineEdit {{ background: {TH.surface}; color: {TH.text}; border: 1.5px solid {TH.border}; border-radius: 10px; padding: 6px 12px; selection-background-color: {TH.accent}; }}
QLineEdit:focus {{ border: 1.5px solid {TH.accent}; }}
QPushButton {{ font-family: 'Segoe UI'; font-weight: 600; }}
QComboBox {{ background: {TH.surface}; color: {TH.text}; border: 1.5px solid {TH.border}; border-radius: 8px; padding: 4px 8px; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background: {TH.surface}; color: {TH.text}; border: 1px solid {TH.border}; selection-background-color: {TH.accent}; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid {TH.border}; background: {TH.surface}; }}
QCheckBox::indicator:checked {{ background: {TH.accent}; border-color: {TH.accent}; }}
QSlider::groove:horizontal {{ background: {TH.border}; height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {TH.accent}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::sub-page:horizontal {{ background: {TH.accent}; border-radius: 2px; }}
QProgressBar {{ background: {TH.border}; border-radius: 4px; height: 8px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {TH.accent}; border-radius: 4px; }}
"""
        self.setStyleSheet(extra_qss)
        QApplication.instance().setFont(QFont("Segoe UI", TH.font_size))

    def _on_theme_changed(self):
        self._apply_qss()
        QMessageBox.information(
            self,
            "Theme Applied",
            "Theme updated.\nRestart the app for a complete refresh of all widgets.",
        )

    def _on_download_done(self, dest):
        if dest == "music":
            self._screens["music"].refresh_after_download()
        else:
            self._screens["video"].refresh_after_download()
        self.navigate(dest)

    def _on_search_query(self, query: str):
        search_screen = self._screens["search"]
        search_screen._search_box.setText(query)
        QTimer.singleShot(200, search_screen._do_search)

    def navigate(self, key: str):
        if self._current and self._current in self._screens:
            self._screens[self._current].on_hide()
        self._current = key
        self._stack.setCurrentWidget(self._screens[key])
        self._screens[key].on_show()
        self._nav.set_active(key)
        playing = key == "music"
        self._header.set_wave(playing)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        save_config({"win_w": self.width(), "win_h": self.height()})

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        if key == Qt.Key.Key_F1:
            show_shortcuts_dialog(self)
            return
        if ctrl and key == Qt.Key.Key_O:
            self._global_open_file()
            return
        if ctrl and key == Qt.Key.Key_F:
            self._global_search()
            return
        if ctrl and key == Qt.Key.Key_Q:
            self.close()
            return
        if ctrl and key == Qt.Key.Key_M:
            self._global_mute()
            return
        if ctrl and key == Qt.Key.Key_L:
            self._global_lyrics()
            return
        if ctrl and key == Qt.Key.Key_D:
            self._global_download()
            return
        if ctrl and shift and key == Qt.Key.Key_F:
            self._global_fullscreen()
            return
        if self._current in ("music", "video"):
            screen = self._screens[self._current]
            if hasattr(screen, "handle_key") and screen.handle_key(key, mods):
                return
        super().keyPressEvent(event)


def main():
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("MusicHub")
    app.setApplicationDisplayName("MusicHub")
    app.setOrganizationName("MusicHub")

    icon_path = get_icon_path()
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setFont(QFont("Segoe UI", 10))

    splash_pix_path = get_logo_path()
    splash = None
    if os.path.isfile(splash_pix_path):
        pix = QPixmap(splash_pix_path).scaled(
            280, 280,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
        splash.setWindowOpacity(0.96)
        splash.show()
        app.processEvents()

    window = AppWindow()

    if splash:
        splash.finish(window)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
