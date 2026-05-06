import os
import random
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from theme.engine import TH, blend_color
from ui.widgets import (RoundedCard, GlowButton, IconButton, SeekSlider,
                        VolumeSlider, FolderSidebarItem, VideoRowWidget)
from ui.dialogs import show_video_info, show_shortcuts_dialog
from core.library import MediaLibrary
from core.favorites import FavoritesManager
from core.scanner import ScanWorker
from utils.media import fmt_time, VIDEO_EXTS
class OverlaySeekBar(QWidget):
    seek_requested = pyqtSignal(float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._hover_value = 0.0
        self._hovered = False
        self._dragging = False
        self._duration = 0
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
    def set_value(self, v):
        self._value = max(0.0, min(1.0, v))
        self.update()
    def set_duration(self, ms):
        self._duration = ms
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        track_h = 5 if not self._hovered else 7
        y = (H - track_h) // 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 55))
        p.drawRoundedRect(0, y, W, track_h, track_h//2, track_h//2)
        fill_w = int(self._value * W)
        if fill_w > 0:
            p.setBrush(QColor(TH.blue))
            p.drawRoundedRect(0, y, fill_w, track_h, track_h//2, track_h//2)
        if self._hovered:
            hover_x = int(self._hover_value * W)
            if hover_x > fill_w:
                p.setBrush(QColor(255, 255, 255, 30))
                p.drawRoundedRect(fill_w, y, hover_x - fill_w, track_h, track_h//2, track_h//2)
            p.setBrush(QColor(255, 255, 255))
            r = 8 if self._dragging else 6
            p.drawEllipse(QPointF(fill_w, H / 2), r, r)
            if self._duration > 0:
                t = fmt_time(self._hover_value * self._duration / 1000)
                p.setPen(QColor(255, 255, 255))
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                tw = 38
                tx = max(2, min(hover_x - tw//2, W - tw - 2))
                bg_rect = QRect(tx - 4, 0, tw + 8, H - track_h - 2)
                p.fillRect(bg_rect, QColor(0, 0, 0, 160))
                p.drawText(QRect(tx, 0, tw, H - track_h - 2), Qt.AlignmentFlag.AlignCenter, t)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            v = e.position().x() / max(1, self.width())
            self._value = max(0.0, min(1.0, v))
            self.update()
            self.seek_requested.emit(self._value)
    def mouseMoveEvent(self, e):
        self._hovered = True
        self._hover_value = max(0.0, min(1.0, e.position().x() / max(1, self.width())))
        if self._dragging and (e.buttons() & Qt.MouseButton.LeftButton):
            self._value = self._hover_value
            self.seek_requested.emit(self._value)
        self.update()
    def mouseReleaseEvent(self, e):
        self._dragging = False
        self.update()
    def leaveEvent(self, _):
        self._hovered = False
        self.update()
    def enterEvent(self, _):
        self._hovered = True
        self.update()
class VideoOverlayControls(QWidget):
    play_pause = pyqtSignal()
    seek_changed = pyqtSignal(float)
    volume_changed = pyqtSignal(int)
    mute_toggled = pyqtSignal()
    fullscreen_toggled = pyqtSignal()
    theater_toggled = pyqtSignal()
    mini_toggled = pyqtSignal()
    prev_track = pyqtSignal()
    next_track = pyqtSignal()
    speed_up = pyqtSignal()
    speed_down = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._fade_val = 1.0
        self._fade_dir = 0
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_step)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_hide)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._build()
    def _make_btn(self, text, tip, w=32, h=32, fsize=15):
        b = QPushButton(text)
        b.setFixedSize(w, h)
        b.setToolTip(tip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet("""
QPushButton{background:transparent;color:white;border:none;font-size:%dpx;font-weight:bold;border-radius:%dpx;}
QPushButton:hover{background:rgba(255,255,255,0.2);}
QPushButton:pressed{background:rgba(255,255,255,0.08);}
""" % (fsize, min(w,h)//2))
        return b
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch()
        self._grad_w = QWidget()
        self._grad_w.setObjectName("ovgrad")
        self._grad_w.setStyleSheet("QWidget#ovgrad{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(0,0,0,0),stop:0.35 rgba(0,0,0,90),stop:1 rgba(0,0,0,220));}")
        inner = QVBoxLayout(self._grad_w)
        inner.setContentsMargins(16, 10, 16, 10)
        inner.setSpacing(5)
        self._title_lbl = QLabel("")
        self._title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color:white;background:transparent;")
        inner.addWidget(self._title_lbl)
        self._seekbar = OverlaySeekBar()
        self._seekbar.seek_requested.connect(self.seek_changed)
        inner.addWidget(self._seekbar)
        bot = QHBoxLayout()
        bot.setSpacing(7)
        self._prev_btn = self._make_btn("⏮", "Previous (Shift+P)")
        self._prev_btn.clicked.connect(self.prev_track)
        self._pp_btn = self._make_btn("▶", "Play/Pause (Space/K)", 38, 38, 18)
        self._pp_btn.clicked.connect(self.play_pause)
        self._next_btn = self._make_btn("⏭", "Next (Shift+N)")
        self._next_btn.clicked.connect(self.next_track)
        self._t_cur = QLabel("0:00")
        self._t_cur.setFont(QFont("Consolas", 9))
        self._t_cur.setStyleSheet("color:white;background:transparent;")
        sep = QLabel("/")
        sep.setStyleSheet("color:rgba(255,255,255,0.5);background:transparent;")
        self._t_tot = QLabel("0:00")
        self._t_tot.setFont(QFont("Consolas", 9))
        self._t_tot.setStyleSheet("color:rgba(255,255,255,0.7);background:transparent;")
        self._speed_lbl = QLabel("1×")
        self._speed_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._speed_lbl.setStyleSheet("color:rgba(255,255,255,0.85);background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:4px;min-width:30px;")
        self._speed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vol_btn = self._make_btn("🔊", "Mute (M)", 28, 28, 13)
        self._vol_btn.clicked.connect(self.mute_toggled)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(100)
        self._vol_slider.setFixedWidth(75)
        self._vol_slider.setFixedHeight(18)
        self._vol_slider.setStyleSheet("""
QSlider::groove:horizontal{background:rgba(255,255,255,0.3);height:3px;border-radius:2px;}
QSlider::handle:horizontal{background:white;width:12px;height:12px;margin:-4px 0;border-radius:6px;}
QSlider::sub-page:horizontal{background:white;border-radius:2px;}
""")
        self._vol_slider.valueChanged.connect(self.volume_changed)
        self._theater_btn = self._make_btn("⬜", "Theater Mode (T)", 28, 28, 13)
        self._theater_btn.clicked.connect(self.theater_toggled)
        self._mini_btn = self._make_btn("⊡", "Mini Player (I)", 28, 28, 13)
        self._mini_btn.clicked.connect(self.mini_toggled)
        self._fs_btn = self._make_btn("⛶", "Fullscreen (F)", 28, 28, 13)
        self._fs_btn.clicked.connect(self.fullscreen_toggled)
        bot.addWidget(self._prev_btn)
        bot.addWidget(self._pp_btn)
        bot.addWidget(self._next_btn)
        bot.addWidget(self._t_cur)
        bot.addWidget(sep)
        bot.addWidget(self._t_tot)
        bot.addWidget(self._speed_lbl)
        bot.addStretch()
        bot.addWidget(self._vol_btn)
        bot.addWidget(self._vol_slider)
        bot.addWidget(self._theater_btn)
        bot.addWidget(self._mini_btn)
        bot.addWidget(self._fs_btn)
        inner.addLayout(bot)
        outer.addWidget(self._grad_w)
    def set_playing(self, playing):
        self._pp_btn.setText("⏸" if playing else "▶")
    def set_time(self, elapsed_ms, total_ms):
        self._t_cur.setText(fmt_time(elapsed_ms / 1000))
        self._t_tot.setText(fmt_time(total_ms / 1000))
        if total_ms > 0:
            self._seekbar.set_value(elapsed_ms / total_ms)
            self._seekbar.set_duration(total_ms)
    def set_title(self, t):
        self._title_lbl.setText(t)
    def set_speed(self, s):
        self._speed_lbl.setText(f"{s}×")
    def set_volume(self, v):
        self._vol_slider.blockSignals(True)
        self._vol_slider.setValue(v)
        self._vol_slider.blockSignals(False)
        self._vol_btn.setText("🔇" if v == 0 else ("🔉" if v < 50 else "🔊"))
    def _fade_step(self):
        step = 0.08
        self._fade_val = max(0.0, min(1.0, self._fade_val + self._fade_dir * step))
        self._effect.setOpacity(self._fade_val)
        if self._fade_dir > 0 and self._fade_val >= 1.0:
            self._fade_timer.stop()
        elif self._fade_dir < 0 and self._fade_val <= 0.0:
            self._fade_timer.stop()
            self.hide()
    def _start_hide(self):
        self._fade_dir = -1
        self._fade_timer.start(16)
    def show_with_autohide(self, ms=3000):
        if not self.isVisible():
            super().show()
        self._fade_dir = 1
        self._fade_timer.start(16)
        self._hide_timer.stop()
        self._hide_timer.start(ms)
    def keep_visible(self):
        self._hide_timer.stop()
        if not self.isVisible():
            super().show()
        self._fade_val = 1.0
        self._fade_dir = 1
        self._effect.setOpacity(1.0)
        self._fade_timer.stop()
        self._hide_timer.start(3000)
class VideoContainer(QWidget):
    mouse_moved = pyqtSignal()
    clicked = pyqtSignal()
    dbl_clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#000000;")
        self.setMouseTracking(True)
        self._last_press_time = 0
        self._pending_click = False
    def resizeEvent(self, e):
        super().resizeEvent(e)
        for c in self.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            c.setGeometry(0, 0, self.width(), self.height())
    def mouseMoveEvent(self, e):
        self.mouse_moved.emit()
        super().mouseMoveEvent(e)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            now = QDateTime.currentMSecsSinceEpoch()
            if now - self._last_press_time < 350:
                self._pending_click = False
                self.dbl_clicked.emit()
                self._last_press_time = 0
            else:
                self._last_press_time = now
                self._pending_click = True
                QTimer.singleShot(360, self._emit_single)
    def _emit_single(self):
        if self._pending_click:
            self._pending_click = False
            self.clicked.emit()
class MiniPlayerWindow(QWidget):
    closed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.resize(400, 240)
        self.setMinimumSize(280, 160)
        self.setWindowTitle("MusicHub Mini Player")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = QWidget()
        bar.setFixedHeight(26)
        bar.setStyleSheet("background:rgba(20,20,30,0.95);")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(8, 0, 6, 0)
        lbl = QLabel("⊡  Mini Player")
        lbl.setStyleSheet("color:rgba(255,255,255,0.8);font-size:9px;background:transparent;font-family:'Segoe UI';font-weight:bold;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{background:transparent;color:rgba(255,255,255,0.6);border:none;font-size:10px;} QPushButton:hover{color:#ff4444;}")
        close_btn.clicked.connect(self._on_close)
        bar_lay.addWidget(lbl)
        bar_lay.addStretch()
        bar_lay.addWidget(close_btn)
        lay.addWidget(bar)
        self._vw = QVideoWidget()
        self._vw.setStyleSheet("background:#000;")
        lay.addWidget(self._vw, 1)
        self._drag_pos = None
        bar.mousePressEvent = self._bar_press
        bar.mouseMoveEvent = self._bar_move
        bar.mouseReleaseEvent = lambda e: setattr(self, "_drag_pos", None)
    def _bar_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def _bar_move(self, e):
        if self._drag_pos and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_pos)
    def _on_close(self):
        self.closed.emit()
        self.close()
    def video_widget(self):
        return self._vw
class VideoScreen(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._library = MediaLibrary("video")
        self._current_folder = None
        self._all_files = []
        self._displayed_files = []
        self._cur_idx = 0
        self._shuffle = False
        self._repeat = False
        self._muted = False
        self._pre_mute_vol = 1.0
        self._seeking = False
        self._fav_only = False
        self._scanner = None
        self._theater_mode = False
        self._mini_mode = False
        self._mini_window = None
        self._speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
        self._speed_idx = 3
        self._speed = 1.0
        self._player = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._audio_out.setVolume(1.0)
        self._player.setAudioOutput(self._audio_out)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.errorOccurred.connect(self._on_error)
        self._build()
        self._player.setVideoOutput(self._video_widget)
        self._library.library_changed.connect(self._on_library_changed)
        QTimer.singleShot(100, self._initial_scan)
    def _initial_scan(self):
        folders = self._library.get_folders()
        if folders:
            self._run_scan(folders)
    def _build(self):
        self._root_layout = QHBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)
        self._sidebar = QWidget()
        self._sidebar.setFixedWidth(190)
        self._sidebar.setStyleSheet(f"background:{TH.surface};")
        sb_lay = QVBoxLayout(self._sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)
        sb_hdr = QWidget()
        sb_hdr.setFixedHeight(44)
        sb_hdr.setStyleSheet(f"background:{TH.surface};border-bottom:1px solid {TH.border};")
        sb_hdr_lay = QHBoxLayout(sb_hdr)
        sb_hdr_lay.setContentsMargins(12, 0, 8, 0)
        folders_lbl = QLabel("FOLDERS")
        folders_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        folders_lbl.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;background:transparent;")
        add_folder_btn = QPushButton("+")
        add_folder_btn.setFixedSize(26, 26)
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.setStyleSheet(f"QPushButton{{background:{TH.blue};color:white;border:none;border-radius:13px;font-size:16px;font-weight:bold;}}QPushButton:hover{{background:{TH.blue2};}}")
        add_folder_btn.clicked.connect(self._add_folder)
        sb_hdr_lay.addWidget(folders_lbl)
        sb_hdr_lay.addStretch()
        sb_hdr_lay.addWidget(add_folder_btn)
        sb_lay.addWidget(sb_hdr)
        self._folder_scroll = QScrollArea()
        self._folder_scroll.setWidgetResizable(True)
        self._folder_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._folder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._folder_scroll.setStyleSheet(f"background:{TH.surface};border:none;")
        self._folder_list_widget = QWidget()
        self._folder_list_widget.setStyleSheet(f"background:{TH.surface};")
        self._folder_list_layout = QVBoxLayout(self._folder_list_widget)
        self._folder_list_layout.setContentsMargins(4, 4, 4, 4)
        self._folder_list_layout.setSpacing(2)
        self._folder_list_layout.addStretch()
        self._folder_scroll.setWidget(self._folder_list_widget)
        sb_lay.addWidget(self._folder_scroll, 1)
        clr_btn = QPushButton("🗑  Clear All")
        clr_btn.setFixedHeight(36)
        clr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clr_btn.setStyleSheet(f"QPushButton{{background:{TH.card};color:{TH.text2};border-top:1px solid {TH.border};border-left:none;border-right:none;border-bottom:none;font-family:'Segoe UI';font-size:10px;font-weight:700;}}QPushButton:hover{{background:{TH.border};color:{TH.text};}}")
        clr_btn.clicked.connect(self._clear_all)
        sb_lay.addWidget(clr_btn)
        self._root_layout.addWidget(self._sidebar)
        self._main_col = QWidget()
        self._main_col.setStyleSheet(f"background:{TH.bg};")
        self._main_lay = QVBoxLayout(self._main_col)
        self._main_lay.setContentsMargins(0, 0, 0, 0)
        self._main_lay.setSpacing(0)
        sec_row = QHBoxLayout()
        sec_row.setContentsMargins(16, 8, 14, 4)
        sec_lbl = QLabel("VIDEO PLAYER")
        sec_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec_lbl.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;background:transparent;")
        self._vid_title = QLabel("No video selected")
        self._vid_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._vid_title.setStyleSheet(f"color:{TH.text};background:transparent;")
        self._vid_title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        kb_btn = QPushButton("⌨")
        kb_btn.setFixedSize(28, 28)
        kb_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kb_btn.setStyleSheet(f"QPushButton{{background:{TH.card};color:{TH.text2};border:1px solid {TH.border};border-radius:14px;font-size:13px;}}QPushButton:hover{{background:{TH.border};color:{TH.text};}}")
        kb_btn.clicked.connect(lambda: show_shortcuts_dialog(self))
        sec_row.addWidget(sec_lbl)
        sec_row.addWidget(self._vid_title, 1)
        sec_row.addWidget(kb_btn)
        self._main_lay.addLayout(sec_row)
        self._video_container = VideoContainer()
        self._video_container.setMinimumHeight(200)
        self._video_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._video_widget = QVideoWidget(self._video_container)
        self._overlay = VideoOverlayControls(self._video_container)
        self._overlay.play_pause.connect(self._toggle_play)
        self._overlay.seek_changed.connect(self._on_overlay_seek)
        self._overlay.volume_changed.connect(self._on_overlay_volume)
        self._overlay.mute_toggled.connect(self._toggle_mute)
        self._overlay.fullscreen_toggled.connect(self._toggle_fullscreen)
        self._overlay.theater_toggled.connect(self._toggle_theater)
        self._overlay.mini_toggled.connect(self._toggle_mini)
        self._overlay.prev_track.connect(self._prev_track)
        self._overlay.next_track.connect(self._next_track)
        self._overlay.speed_up.connect(self._speed_up)
        self._overlay.speed_down.connect(self._speed_down)
        self._video_container.mouse_moved.connect(self._on_mouse_moved)
        self._video_container.clicked.connect(self._toggle_play)
        self._video_container.dbl_clicked.connect(self._toggle_fullscreen)
        self._video_container.setMouseTracking(True)
        self._main_lay.addWidget(self._video_container, 3)
        self._ctrl_bg = QWidget()
        self._ctrl_bg.setStyleSheet(f"background:{TH.surface};")
        ctrl_main = QVBoxLayout(self._ctrl_bg)
        ctrl_main.setContentsMargins(14, 6, 14, 6)
        ctrl_main.setSpacing(4)
        seek_lay = QVBoxLayout()
        seek_lay.setSpacing(2)
        self._seek_slider = SeekSlider(TH.blue)
        self._seek_slider.sliderPressed.connect(self._on_seek_press)
        self._seek_slider.sliderReleased.connect(self._on_seek_release)
        self._seek_slider.seek_requested.connect(self._on_click_seek)
        time_row = QHBoxLayout()
        self._t_elapsed = QLabel("0:00")
        self._t_elapsed.setFont(QFont("Consolas", 9))
        self._t_elapsed.setStyleSheet(f"color:{TH.text2};background:transparent;")
        self._t_total = QLabel("0:00")
        self._t_total.setFont(QFont("Consolas", 9))
        self._t_total.setStyleSheet(f"color:{TH.text2};background:transparent;")
        time_row.addWidget(self._t_elapsed)
        time_row.addStretch()
        time_row.addWidget(self._t_total)
        seek_lay.addWidget(self._seek_slider)
        seek_lay.addLayout(time_row)
        ctrl_main.addLayout(seek_lay)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._v_prev = IconButton("⏮", 38, "Previous (Shift+P)")
        self._v_prev.clicked.connect(self._prev_track)
        self._v_pp = GlowButton("▶  Play", TH.blue)
        self._v_pp.setFixedHeight(38)
        self._v_pp.setFixedWidth(110)
        self._v_pp.clicked.connect(self._toggle_play)
        self._v_stop = IconButton("⏹", 38, "Stop (S)")
        self._v_stop.clicked.connect(self._stop)
        self._v_next = IconButton("⏭", 38, "Next (Shift+N)")
        self._v_next.clicked.connect(self._next_track)
        self._v_fullscreen = IconButton("⛶", 38, "Fullscreen (F)")
        self._v_fullscreen.clicked.connect(self._toggle_fullscreen)
        self._v_theater = IconButton("⬜", 38, "Theater Mode (T)")
        self._v_theater.clicked.connect(self._toggle_theater)
        self._v_shuf = QPushButton("⇀")
        self._v_shuf.setFixedSize(38, 38)
        self._v_shuf.setCursor(Qt.CursorShape.PointingHandCursor)
        self._v_shuf.setToolTip("Shuffle")
        self._v_shuf.clicked.connect(self._toggle_shuffle)
        self._v_rep = QPushButton("↺")
        self._v_rep.setFixedSize(38, 38)
        self._v_rep.setCursor(Qt.CursorShape.PointingHandCursor)
        self._v_rep.setToolTip("Repeat")
        self._v_rep.clicked.connect(self._toggle_repeat)
        self._update_sr_btns()
        self._speed_btn = QPushButton("1×")
        self._speed_btn.setFixedSize(44, 38)
        self._speed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._speed_btn.setToolTip("Playback Speed (Shift+. / Shift+,)")
        self._speed_btn.setStyleSheet(f"QPushButton{{background:{TH.card};color:{TH.text2};border:1px solid {TH.border};border-radius:8px;font-family:'Segoe UI';font-size:10px;font-weight:700;}}QPushButton:hover{{color:{TH.text};border-color:{TH.blue};}}")
        self._speed_btn.clicked.connect(self._cycle_speed)
        self._vol_icon = QLabel("🔊")
        self._vol_icon.setStyleSheet(f"color:{TH.text2};background:transparent;font-size:12px;")
        self._vol_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vol_icon.mousePressEvent = lambda _: self._toggle_mute()
        self._vol_slider = VolumeSlider()
        self._vol_slider.valueChanged.connect(self._set_volume)
        self._vol_pct = QLabel("100%")
        self._vol_pct.setFont(QFont("Segoe UI", 8))
        self._vol_pct.setStyleSheet(f"color:{TH.text2};background:transparent;")
        btn_row.addWidget(self._v_prev)
        btn_row.addWidget(self._v_pp)
        btn_row.addWidget(self._v_stop)
        btn_row.addWidget(self._v_next)
        btn_row.addWidget(self._v_fullscreen)
        btn_row.addWidget(self._v_theater)
        btn_row.addWidget(self._v_shuf)
        btn_row.addWidget(self._v_rep)
        btn_row.addWidget(self._speed_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._vol_icon)
        btn_row.addWidget(self._vol_slider)
        btn_row.addWidget(self._vol_pct)
        ctrl_main.addLayout(btn_row)
        info_row = QHBoxLayout()
        self._vid_counter = QLabel("0 / 0")
        self._vid_counter.setFont(QFont("Segoe UI", 9))
        self._vid_counter.setStyleSheet(f"color:{TH.blue};background:transparent;")
        self._scan_status = QLabel("")
        self._scan_status.setFont(QFont("Segoe UI", 8))
        self._scan_status.setStyleSheet(f"color:{TH.text3};background:transparent;")
        info_row.addWidget(self._vid_counter)
        info_row.addStretch()
        info_row.addWidget(self._scan_status)
        ctrl_main.addLayout(info_row)
        self._main_lay.addWidget(self._ctrl_bg)
        pl_hdr_w = QWidget()
        pl_hdr_lay = QHBoxLayout(pl_hdr_w)
        pl_hdr_lay.setContentsMargins(14, 2, 14, 2)
        pl_hdr_lay.setSpacing(8)
        pl_lbl = QLabel("PLAYLIST")
        pl_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        pl_lbl.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;background:transparent;")
        self._fav_filter_btn = QPushButton("★ Favorites")
        self._fav_filter_btn.setFixedHeight(24)
        self._fav_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_filter_btn.clicked.connect(self._toggle_fav_filter)
        self._update_fav_filter_btn_style()
        pl_hdr_lay.addWidget(pl_lbl)
        pl_hdr_lay.addStretch()
        pl_hdr_lay.addWidget(self._fav_filter_btn)
        self._main_lay.addWidget(pl_hdr_w)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(f"background:{TH.bg};border:none;")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._pl_widget = QWidget()
        self._pl_widget.setStyleSheet(f"background:{TH.bg};")
        self._pl_layout = QVBoxLayout(self._pl_widget)
        self._pl_layout.setContentsMargins(10, 4, 10, 10)
        self._pl_layout.setSpacing(3)
        self._pl_layout.addStretch()
        self._scroll.setWidget(self._pl_widget)
        self._main_lay.addWidget(self._scroll, 1)
        self._root_layout.addWidget(self._main_col, 1)
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._layout_video_children()
    def _layout_video_children(self):
        if hasattr(self, '_video_widget') and hasattr(self, '_overlay') and hasattr(self, '_video_container'):
            w = self._video_container.width()
            h = self._video_container.height()
            self._video_widget.setGeometry(0, 0, w, h)
            self._overlay.setGeometry(0, 0, w, h)
    def _on_mouse_moved(self):
        self._overlay.keep_visible()
        if not self._overlay.isVisible():
            self._overlay.show_with_autohide()
        QApplication.restoreOverrideCursor()
        if not hasattr(self, '_cursor_timer'):
            self._cursor_timer = QTimer(self)
            self._cursor_timer.setSingleShot(True)
            self._cursor_timer.timeout.connect(lambda: QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor) if self._video_container.isFullScreen() else None)
        self._cursor_timer.start(3500)
    def _on_overlay_seek(self, fraction):
        dur = self._player.duration()
        if dur > 0:
            self._player.setPosition(int(fraction * dur))
    def _on_overlay_volume(self, val):
        self._audio_out.setVolume(val / 100)
        icon = "🔇" if val == 0 else ("🔉" if val < 50 else "🔊")
        self._vol_icon.setText(icon)
        self._vol_slider.blockSignals(True)
        self._vol_slider.setValue(val)
        self._vol_slider.blockSignals(False)
        self._vol_pct.setText(f"{val}%")
    def _rebuild_sidebar(self):
        while self._folder_list_layout.count() > 1:
            w = self._folder_list_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        total = self._library.total_count()
        all_item = FolderSidebarItem(".", total, self._current_folder is None)
        all_item._folder_key = "__all__"
        all_item.clicked.connect(self._on_folder_click)
        self._folder_list_layout.insertWidget(0, all_item)
        for i, folder in enumerate(self._library.get_folders()):
            cnt = self._library.folder_count(folder)
            item = FolderSidebarItem(folder, cnt, folder == self._current_folder)
            item._folder_key = folder
            item.clicked.connect(self._on_folder_click)
            self._folder_list_layout.insertWidget(i + 1, item)
    def _on_folder_click(self, folder_key):
        if folder_key in ("__all__", "."):
            self._current_folder = None
            self._displayed_files = list(self._all_files)
        else:
            self._current_folder = folder_key
            self._displayed_files = self._library.get_folder_files(folder_key)
        self._rebuild_sidebar()
        self._refresh_playlist()
        self._update_info()
    def _add_folder(self):
        while True:
            f = QFileDialog.getExistingDirectory(self, "Pick a video folder", self._app.save_path)
            if not f:
                break
            added = self._library.add_folder(f)
            if added:
                self._run_scan([f])
            reply = QMessageBox.question(self, "Add More?", f"Added: {f}\n\nAdd another folder?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                break
    def _run_scan(self, folders):
        self._scan_status.setText("Scanning…")
        self._scanner = ScanWorker(folders, VIDEO_EXTS)
        self._scanner.folder_done.connect(self._on_folder_scanned)
        self._scanner.scan_complete.connect(self._on_scan_complete)
        self._scanner.start()
    def _on_folder_scanned(self, folder, files):
        self._library._folder_files[folder] = files
        self._library._rebuild_all()
        self._library._watcher.watch_folder(folder)
        self._all_files = self._library.get_all_files()
        if self._current_folder is None:
            self._displayed_files = list(self._all_files)
        self._rebuild_sidebar()
    def _on_scan_complete(self):
        self._scan_status.setText(f"{self._library.total_count()} videos")
        self._all_files = self._library.get_all_files()
        if self._current_folder is None:
            self._displayed_files = list(self._all_files)
        self._rebuild_sidebar()
        self._refresh_playlist()
        self._update_info()
    def _clear_all(self):
        self._player.stop()
        self._player.setSource(QUrl())
        self._library.clear()
        self._all_files = []
        self._displayed_files = []
        self._current_folder = None
        self._cur_idx = 0
        self._rebuild_sidebar()
        self._refresh_playlist()
        self._update_info()
        self._vid_title.setText("No video selected")
        self._seek_slider.setValue(0)
        self._t_elapsed.setText("0:00")
        self._t_total.setText("0:00")
        self._scan_status.setText("")
    def _refresh_playlist(self):
        while self._pl_layout.count() > 1:
            item = self._pl_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self._displayed_files:
            lbl = QLabel("  No files found. Add a folder using the + button.")
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet(f"color:{TH.text3};background:transparent;")
            self._pl_layout.insertWidget(0, lbl)
            return
        for i, fp in enumerate(self._displayed_files):
            row = VideoRowWidget(i, fp, i == self._cur_idx)
            row.clicked.connect(self._select_idx)
            row.dbl_clicked.connect(self._play_idx)
            row.info_requested.connect(lambda idx, files=self._displayed_files: show_video_info(self, files[idx]))
            self._pl_layout.insertWidget(i, row)
    def _update_info(self):
        n = len(self._displayed_files)
        self._vid_counter.setText(f"{self._cur_idx + 1 if n else 0} / {n}")
    def _toggle_play(self):
        if not self._displayed_files:
            QMessageBox.information(self, "No Files", "Add a folder first!")
            return
        state = self._player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
        else:
            self._load_and_play(self._cur_idx)
    def _load_and_play(self, idx):
        if not self._displayed_files:
            return
        self._cur_idx = idx
        fp = self._displayed_files[idx]
        self._player.setSource(QUrl.fromLocalFile(fp))
        self._player.setPlaybackRate(self._speed)
        self._player.play()
        name = os.path.splitext(os.path.basename(fp))[0]
        display = name if len(name) <= 42 else name[:39] + "…"
        self._vid_title.setText(display)
        self._overlay.set_title(display)
        self._overlay.show_with_autohide(3000)
        self._refresh_playlist()
        self._update_info()
    def _stop(self):
        self._player.stop()
        self._v_pp.setText("▶  Play")
        self._v_pp.set_color(TH.blue)
        self._seek_slider.blockSignals(True)
        self._seek_slider.setValue(0)
        self._seek_slider.blockSignals(False)
        self._t_elapsed.setText("0:00")
    def _is_fullscreen(self):
        return bool(self._video_container.windowFlags() & Qt.WindowType.Window) and self._video_container.isFullScreen()
    def _toggle_fullscreen(self):
        if self._is_fullscreen():
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()
    def _enter_fullscreen(self):
        self._video_container.setParent(None)
        self._video_container.setWindowFlags(Qt.WindowType.Window)
        self._video_container.showFullScreen()
        self._video_container.setMouseTracking(True)
        self._layout_video_children()
    def _exit_fullscreen(self):
        self._video_container.setWindowFlags(Qt.WindowType.Widget)
        self._video_container.showNormal()
        self._main_lay.insertWidget(1, self._video_container, 3)
        self._video_container.setMouseTracking(True)
        QApplication.restoreOverrideCursor()
        QTimer.singleShot(50, self._layout_video_children)
    def _toggle_theater(self):
        self._theater_mode = not self._theater_mode
        if self._theater_mode:
            self._sidebar.hide()
            self._ctrl_bg.hide()
            self._video_container.setMinimumHeight(350)
        else:
            self._sidebar.show()
            self._ctrl_bg.show()
            self._video_container.setMinimumHeight(200)
        active = self._theater_mode
        self._v_theater.setStyleSheet(f"QPushButton{{background:{TH.blue if active else TH.card};color:{'white' if active else TH.text2};border:1px solid {TH.blue if active else TH.border};border-radius:8px;font-size:14px;}}QPushButton:hover{{border-color:{TH.blue};}}")
    def _toggle_mini(self):
        if self._mini_mode:
            if self._mini_window:
                self._player.setVideoOutput(self._video_widget)
                self._mini_window.close()
                self._mini_window = None
            self._mini_mode = False
        else:
            self._mini_mode = True
            self._mini_window = MiniPlayerWindow()
            self._mini_window.closed.connect(self._on_mini_closed)
            self._player.setVideoOutput(self._mini_window.video_widget())
            self._mini_window.show()
    def _on_mini_closed(self):
        self._player.setVideoOutput(self._video_widget)
        self._mini_mode = False
        self._mini_window = None
    def _on_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        if playing:
            self._v_pp.setText("⏸  Pause")
            self._v_pp.set_color(blend_color(QColor(TH.blue), QColor(TH.bg), 0.3).name())
            self._overlay.set_playing(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._v_pp.setText("▶  Play")
            self._v_pp.set_color(TH.blue)
            self._overlay.set_playing(False)
        else:
            self._v_pp.setText("▶  Play")
            self._v_pp.set_color(TH.blue)
            self._overlay.set_playing(False)
            dur = self._player.duration()
            pos = self._player.position()
            if dur > 0 and pos >= dur - 300:
                QTimer.singleShot(200, self._auto_next)
    def _auto_next(self):
        if self._displayed_files:
            if self._repeat:
                self._load_and_play(self._cur_idx)
            elif self._shuffle:
                self._load_and_play(random.randint(0, len(self._displayed_files) - 1))
            else:
                self._load_and_play((self._cur_idx + 1) % len(self._displayed_files))
    def _on_position_changed(self, pos_ms):
        if not self._seeking:
            dur = self._player.duration()
            if dur > 0:
                self._seek_slider.blockSignals(True)
                self._seek_slider.setValue(int(pos_ms / dur * 1000))
                self._seek_slider.blockSignals(False)
            self._t_elapsed.setText(fmt_time(pos_ms / 1000))
            self._overlay.set_time(pos_ms, self._player.duration())
    def _on_duration_changed(self, dur_ms):
        self._t_total.setText(fmt_time(dur_ms / 1000))
    def _on_seek_press(self):
        self._seeking = True
    def _on_seek_release(self):
        self._seeking = False
        dur = self._player.duration()
        if dur > 0:
            pos = int(self._seek_slider.value() / 1000 * dur)
            self._player.setPosition(pos)
    def _on_click_seek(self, val):
        dur = self._player.duration()
        if dur > 0:
            pos = int(val / 1000 * dur)
            self._player.setPosition(pos)
    def _on_error(self, error, error_str):
        QMessageBox.critical(self, "Playback Error", error_str)
    def _select_idx(self, idx):
        if 0 <= idx < len(self._displayed_files):
            self._cur_idx = idx
            self._refresh_playlist()
            self._update_info()
    def _play_idx(self, idx):
        self._load_and_play(idx)
    def _prev_track(self):
        if self._displayed_files:
            self._load_and_play((self._cur_idx - 1) % len(self._displayed_files))
    def _next_track(self):
        if not self._displayed_files:
            return
        if self._shuffle:
            self._load_and_play(random.randint(0, len(self._displayed_files) - 1))
        else:
            self._load_and_play((self._cur_idx + 1) % len(self._displayed_files))
    def _set_volume(self, val):
        self._audio_out.setVolume(val / 100)
        icon = "🔇" if val == 0 else ("🔉" if val < 50 else "🔊")
        self._vol_icon.setText(icon)
        self._vol_pct.setText(f"{val}%")
        self._overlay.set_volume(val)
    def _toggle_mute(self):
        if self._muted:
            self._muted = False
            v = int(self._pre_mute_vol * 100)
            self._vol_slider.setValue(v)
            self._set_volume(v)
        else:
            self._pre_mute_vol = self._vol_slider.value() / 100
            self._muted = True
            self._vol_slider.setValue(0)
            self._set_volume(0)
    def _volume_up(self):
        v = min(self._vol_slider.value() + 5, 100)
        self._vol_slider.setValue(v)
        self._set_volume(v)
    def _volume_down(self):
        v = max(self._vol_slider.value() - 5, 0)
        self._vol_slider.setValue(v)
        self._set_volume(v)
    def _seek_forward(self, ms=5000):
        dur = self._player.duration()
        if dur > 0:
            self._player.setPosition(min(self._player.position() + ms, dur - 100))
    def _seek_backward(self, ms=5000):
        self._player.setPosition(max(self._player.position() - ms, 0))
    def _jump_percent(self, pct):
        dur = self._player.duration()
        if dur > 0:
            self._player.setPosition(int(pct / 100 * dur))
    def _speed_up(self):
        self._speed_idx = min(self._speed_idx + 1, len(self._speeds) - 1)
        self._apply_speed()
    def _speed_down(self):
        self._speed_idx = max(self._speed_idx - 1, 0)
        self._apply_speed()
    def _cycle_speed(self):
        self._speed_idx = (self._speed_idx + 1) % len(self._speeds)
        self._apply_speed()
    def _apply_speed(self):
        self._speed = self._speeds[self._speed_idx]
        self._player.setPlaybackRate(self._speed)
        s = self._speed
        label = f"{int(s)}×" if s == int(s) else f"{s}×"
        self._speed_btn.setText(label)
        self._overlay.set_speed(s)
    def _toggle_shuffle(self):
        self._shuffle = not self._shuffle
        self._update_sr_btns()
    def _toggle_repeat(self):
        self._repeat = not self._repeat
        self._update_sr_btns()
    def _update_sr_btns(self):
        for btn, active in [(self._v_shuf, self._shuffle), (self._v_rep, self._repeat)]:
            c = TH.blue if active else TH.card
            tc = TH.text if active else TH.text2
            btn.setStyleSheet(f"QPushButton{{background:{c};color:{tc};border:1px solid {TH.blue if active else TH.border};border-radius:19px;font-size:14px;}}QPushButton:hover{{border-color:{TH.blue};color:{TH.text};}}")
    def _toggle_fav_filter(self):
        self._fav_only = not self._fav_only
        self._update_fav_filter_btn_style()
        self._apply_fav_filter()
    def _update_fav_filter_btn_style(self):
        if self._fav_only:
            self._fav_filter_btn.setStyleSheet("QPushButton{background:#ffd60a;color:#111;border:none;border-radius:6px;font-size:9px;font-weight:700;padding:0 8px;}QPushButton:hover{background:#ffe566;}")
        else:
            self._fav_filter_btn.setStyleSheet(f"QPushButton{{background:{TH.card};color:{TH.text3};border:1px solid {TH.border};border-radius:6px;font-size:9px;font-weight:700;padding:0 8px;}}QPushButton:hover{{color:#ffd60a;}}")
    def _apply_fav_filter(self):
        fav_mgr = FavoritesManager.get()
        if self._fav_only:
            self._displayed_files = [f for f in self._all_files if fav_mgr.is_fav(f)]
        elif self._current_folder is None:
            self._displayed_files = list(self._all_files)
        else:
            self._displayed_files = self._library.get_folder_files(self._current_folder)
        self._refresh_playlist()
        self._update_info()
    def handle_key(self, key, modifiers):
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        if key in (Qt.Key.Key_Space, Qt.Key.Key_K):
            self._toggle_play()
            return True
        if key == Qt.Key.Key_S and not ctrl:
            self._stop()
            return True
        if key == Qt.Key.Key_N and shift:
            self._next_track()
            return True
        if key == Qt.Key.Key_P and shift:
            self._prev_track()
            return True
        if key in (Qt.Key.Key_F, Qt.Key.Key_F11) and not ctrl:
            self._toggle_fullscreen()
            return True
        if key == Qt.Key.Key_T and not ctrl:
            self._toggle_theater()
            return True
        if key == Qt.Key.Key_I and not ctrl:
            self._toggle_mini()
            return True
        if key == Qt.Key.Key_Escape:
            self._exit_fullscreen()
            return True
        if key == Qt.Key.Key_J:
            self._seek_backward(10000)
            return True
        if key == Qt.Key.Key_L and not ctrl:
            self._seek_forward(10000)
            return True
        if key == Qt.Key.Key_Right and not ctrl:
            self._seek_forward(5000)
            return True
        if key == Qt.Key.Key_Left and not ctrl:
            self._seek_backward(5000)
            return True
        if ctrl and key == Qt.Key.Key_Right:
            self._next_track()
            return True
        if ctrl and key == Qt.Key.Key_Left:
            self._prev_track()
            return True
        if ctrl and key == Qt.Key.Key_End:
            if self._displayed_files:
                self._load_and_play(len(self._displayed_files) - 1)
            return True
        if ctrl and key == Qt.Key.Key_Home:
            if self._displayed_files:
                self._load_and_play(0)
            return True
        if key == Qt.Key.Key_Up:
            self._volume_up()
            return True
        if key == Qt.Key.Key_Down:
            self._volume_down()
            return True
        if key == Qt.Key.Key_M and not ctrl:
            self._toggle_mute()
            return True
        if key == Qt.Key.Key_Period and shift:
            self._speed_up()
            return True
        if key == Qt.Key.Key_Comma and shift:
            self._speed_down()
            return True
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            pct = (key - Qt.Key.Key_0) * 10
            self._jump_percent(pct)
            return True
        return False
    def _on_library_changed(self):
        self._all_files = self._library.get_all_files()
        if self._fav_only:
            self._apply_fav_filter()
            return
        if self._current_folder is None:
            self._displayed_files = list(self._all_files)
        else:
            self._displayed_files = self._library.get_folder_files(self._current_folder)
        self._rebuild_sidebar()
        self._refresh_playlist()
        self._update_info()
        self._scan_status.setText(f"{self._library.total_count()} videos")
    def refresh_after_download(self):
        sp = self._app.save_path
        if sp not in self._library.get_folders():
            self._library.add_folder(sp)
            self._run_scan([sp])
    def on_show(self):
        self._update_info()
    def on_hide(self):
        state = self._player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()