from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, blend_color
from ui.widgets import RoundedCard, GlowButton, IconButton
from core.youtube import SearchWorker, TrendingWorker, StreamUrlWorker, ThumbnailLoader, fmt_views, fmt_dur
from core.downloader import DownloadWorker
from core.favorites import FavoritesManager
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    from PyQt6.QtCore import QUrl
    QT_MM_OK = True
except ImportError:
    QT_MM_OK = False
try:
    import pygame
    PYGAME_OK = True
except Exception:
    PYGAME_OK = False
class ResultCard(QWidget):
    play_clicked = pyqtSignal(dict)
    download_clicked = pyqtSignal(dict, str)
    fav_clicked = pyqtSignal(dict)
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self._item = item
        self._hovered = False
        self._thumb_pm = None
        self.setFixedHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)
        self._thumb_lbl = QLabel()
        self._thumb_lbl.setFixedSize(112, 64)
        self._thumb_lbl.setStyleSheet(f"border-radius: 8px; background: {TH.border};")
        self._thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._draw_placeholder()
        lay.addWidget(self._thumb_lbl)
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        title = item.get("title", "Unknown")
        self._title_lbl = QLabel(title[:52] + "…" if len(title) > 52 else title)
        self._title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {TH.text}; background: transparent;")
        channel = item.get("channel", "")
        dur = fmt_dur(item.get("duration", 0))
        views = fmt_views(item.get("view_count", 0))
        sub_parts = []
        if channel:
            sub_parts.append(channel)
        if dur and dur != "0:00":
            sub_parts.append(dur)
        if views and views != "0 views":
            sub_parts.append(views)
        self._sub_lbl = QLabel("  •  ".join(sub_parts))
        self._sub_lbl.setFont(QFont("Segoe UI", 8))
        self._sub_lbl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        info_col.addWidget(self._title_lbl)
        info_col.addWidget(self._sub_lbl)
        info_col.addStretch()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        play_btn = QPushButton("▶ Play")
        play_btn.setFixedHeight(24)
        play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.accent}; color: white; border: none; border-radius: 6px;
    font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; padding: 0 8px; }}
QPushButton:hover {{ background: {blend_color(QColor(TH.accent), QColor('#ffffff'), 0.2).name()}; }}
""")
        play_btn.clicked.connect(lambda: self.play_clicked.emit(self._item))
        dl_mp3_btn = QPushButton("⬇ MP3")
        dl_mp3_btn.setFixedHeight(24)
        dl_mp3_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_mp3_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.green}; color: white; border: none; border-radius: 6px;
    font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; padding: 0 8px; }}
QPushButton:hover {{ background: {blend_color(QColor(TH.green), QColor('#ffffff'), 0.2).name()}; }}
""")
        dl_mp3_btn.clicked.connect(lambda: self.download_clicked.emit(self._item, "MP3"))
        dl_mp4_btn = QPushButton("⬇ MP4")
        dl_mp4_btn.setFixedHeight(24)
        dl_mp4_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_mp4_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.blue}; color: white; border: none; border-radius: 6px;
    font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; padding: 0 8px; }}
QPushButton:hover {{ background: {blend_color(QColor(TH.blue), QColor('#ffffff'), 0.2).name()}; }}
""")
        dl_mp4_btn.clicked.connect(lambda: self.download_clicked.emit(self._item, "MP4"))
        fav_man = FavoritesManager.get()
        is_fav = fav_man.is_fav(item.get("url", ""))
        self._fav_btn = QPushButton("♥" if is_fav else "♡")
        self._fav_btn.setFixedSize(24, 24)
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fav_col = TH.accent if is_fav else TH.text3
        self._fav_btn.setStyleSheet(f"""
QPushButton {{ background: transparent; color: {fav_col}; border: none; font-size: 14px; }}
QPushButton:hover {{ color: {TH.accent}; }}
""")
        self._fav_btn.clicked.connect(self._toggle_fav)
        btn_row.addWidget(play_btn)
        btn_row.addWidget(dl_mp3_btn)
        btn_row.addWidget(dl_mp4_btn)
        btn_row.addWidget(self._fav_btn)
        btn_row.addStretch()
        info_col.addLayout(btn_row)
        lay.addLayout(info_col)
    def _draw_placeholder(self):
        pm = QPixmap(112, 64)
        pm.fill(Qt.GlobalColor.transparent)
        ptr = QPainter(pm)
        ptr.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, 112, 64)
        g.setColorAt(0, blend_color(QColor(TH.blue), QColor(TH.bg), 0.5))
        g.setColorAt(1, blend_color(QColor(TH.purple), QColor(TH.bg), 0.6))
        path = QPainterPath()
        path.addRoundedRect(0, 0, 112, 64, 8, 8)
        ptr.fillPath(path, g)
        ptr.setPen(QColor(255, 255, 255, 100))
        ptr.setFont(QFont("Segoe UI Symbol", 22))
        ptr.drawText(QRect(0, 0, 112, 64), Qt.AlignmentFlag.AlignCenter, "▶")
        ptr.end()
        self._thumb_lbl.setPixmap(pm)
    def set_thumbnail(self, pm: QPixmap):
        self._thumb_pm = pm
        scaled = pm.scaled(112, 64, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        ox = (scaled.width() - 112) // 2
        oy = (scaled.height() - 64) // 2
        cropped = scaled.copy(ox, oy, 112, 64)
        rounded = QPixmap(112, 64)
        rounded.fill(Qt.GlobalColor.transparent)
        ptr = QPainter(rounded)
        ptr.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 112, 64, 8, 8)
        ptr.setClipPath(path)
        ptr.drawPixmap(0, 0, cropped)
        ptr.end()
        self._thumb_lbl.setPixmap(rounded)
    def _toggle_fav(self):
        fav_man = FavoritesManager.get()
        url = self._item.get("url", "")
        is_fav = fav_man.toggle(url)
        self._fav_btn.setText("♥" if is_fav else "♡")
        fav_col = TH.accent if is_fav else TH.text3
        self._fav_btn.setStyleSheet(f"""
QPushButton {{ background: transparent; color: {fav_col}; border: none; font-size: 14px; }}
QPushButton:hover {{ color: {TH.accent}; }}
""")
        self.fav_clicked.emit(self._item)
    def enterEvent(self, _):
        self._hovered = True
        self.update()
    def leaveEvent(self, _):
        self._hovered = False
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(4, 2, self.width() - 8, self.height() - 4, 10, 10)
        if self._hovered:
            p.fillPath(path, blend_color(QColor(TH.border), QColor(TH.card), 0.5))
        else:
            p.fillPath(path, QColor(TH.card))
class NowPlayingBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._visible = False
        self.hide()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(10)
        self._thumb = QLabel()
        self._thumb.setFixedSize(40, 40)
        self._thumb.setStyleSheet(f"border-radius: 6px; background: {TH.border};")
        self._title_lbl = QLabel("Not playing")
        self._title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {TH.text}; background: transparent;")
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setFont(QFont("Segoe UI", 8))
        self._status_lbl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.addWidget(self._title_lbl)
        text_col.addWidget(self._status_lbl)
        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setFixedSize(32, 32)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border}; border-radius: 16px; font-size: 12px; }}
QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}
""")
        lay.addWidget(self._thumb)
        lay.addLayout(text_col)
        lay.addStretch()
        lay.addWidget(self._stop_btn)
    def set_item(self, item: dict, status: str = "Loading…"):
        title = item.get("title", "Unknown")
        self._title_lbl.setText(title[:40] + "…" if len(title) > 40 else title)
        self._status_lbl.setText(status)
        if not self._visible:
            self._visible = True
            self.show()
    def set_status(self, status: str):
        self._status_lbl.setText(status)
    def set_thumbnail(self, pm: QPixmap):
        scaled = pm.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self._thumb.setPixmap(scaled)
    def stop(self):
        self._visible = False
        self.hide()
    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(TH.surface))
        p.setPen(QColor(TH.border))
        p.drawLine(0, 0, self.width(), 0)
class VideoPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("MusicHub — Video Stream")
        self.resize(800, 480)
        self.setMinimumSize(480, 300)
        self.setStyleSheet("background: #000000;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background: #000000;")
        lay.addWidget(self._video_widget, 1)
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background: {TH.surface}; border-top: 1px solid {TH.border};")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(14, 0, 14, 0)
        bar_lay.setSpacing(10)
        self._title_lbl = QLabel("")
        self._title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: {TH.text}; background: transparent;")
        self._status_lbl = QLabel("Loading…")
        self._status_lbl.setFont(QFont("Segoe UI", 8))
        self._status_lbl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        close_btn = QPushButton("⏹ Stop & Close")
        close_btn.setFixedHeight(30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border}; border-radius: 8px;
    font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; padding: 0 10px; }}
QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}
""")
        close_btn.clicked.connect(self.close)
        bar_lay.addWidget(self._title_lbl, 1)
        bar_lay.addWidget(self._status_lbl)
        bar_lay.addWidget(close_btn)
        lay.addWidget(bar)
    def video_widget(self):
        return self._video_widget
    def set_title(self, title: str):
        self._title_lbl.setText(title[:60] + "…" if len(title) > 60 else title)
    def set_status(self, status: str):
        self._status_lbl.setText(status)
class SearchScreen(QWidget):
    navigate = pyqtSignal(str)
    download_to_tab = pyqtSignal(str, str, str)
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._search_worker = None
        self._trending_worker = None
        self._stream_worker = None
        self._dl_worker = None
        self._thumb_loaders = []
        self._card_map = {}
        self._player = None
        self._audio_out = None
        self._video_player = None
        self._video_audio_out = None
        self._video_popup = None
        self._current_item = None
        self._play_mode = "audio"
        self._build()
        if QT_MM_OK:
            self._audio_out = QAudioOutput()
            self._audio_out.setVolume(1.0)
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_out)
            self._player.playbackStateChanged.connect(self._on_state_changed)
            self._video_audio_out = QAudioOutput()
            self._video_audio_out.setVolume(1.0)
            self._video_player = QMediaPlayer()
            self._video_player.setAudioOutput(self._video_audio_out)
            self._video_player.playbackStateChanged.connect(self._on_video_state_changed)
    def _build(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background: {TH.surface};")
        top_bar.setFixedHeight(56)
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(16, 8, 16, 8)
        top_lay.setSpacing(8)
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍  Search YouTube music & videos…")
        self._search_box.setFixedHeight(38)
        self._search_box.setStyleSheet(f"""
QLineEdit {{ background: {TH.card}; color: {TH.text}; border: 1px solid {TH.border}; border-radius: 10px;
    font-family: 'Segoe UI'; font-size: 11px; padding: 0 12px; }}
QLineEdit:focus {{ border-color: {TH.accent}; }}
""")
        self._search_box.returnPressed.connect(self._do_search)
        search_btn = QPushButton("Search")
        search_btn.setFixedSize(72, 38)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.accent}; color: white; border: none; border-radius: 10px;
    font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; }}
QPushButton:hover {{ background: {blend_color(QColor(TH.accent), QColor('#ffffff'), 0.15).name()}; }}
""")
        search_btn.clicked.connect(self._do_search)
        top_lay.addWidget(self._search_box)
        top_lay.addWidget(search_btn)
        main.addWidget(top_bar)
        mode_bar = QWidget()
        mode_bar.setStyleSheet(f"background: {TH.surface}; border-bottom: 1px solid {TH.border};")
        mode_bar.setFixedHeight(36)
        mode_lay = QHBoxLayout(mode_bar)
        mode_lay.setContentsMargins(16, 4, 16, 4)
        mode_lay.setSpacing(6)
        mode_lbl = QLabel("Play as:")
        mode_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        mode_lbl.setStyleSheet(f"color: {TH.text3}; background: transparent; letter-spacing: 1px;")
        self._audio_mode_btn = QPushButton("♪ Audio")
        self._audio_mode_btn.setFixedHeight(26)
        self._audio_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._audio_mode_btn.clicked.connect(lambda: self._set_play_mode("audio"))
        self._video_mode_btn = QPushButton("▶ Video")
        self._video_mode_btn.setFixedHeight(26)
        self._video_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._video_mode_btn.clicked.connect(lambda: self._set_play_mode("video"))
        mode_lay.addWidget(mode_lbl)
        mode_lay.addWidget(self._audio_mode_btn)
        mode_lay.addWidget(self._video_mode_btn)
        mode_lay.addStretch()
        self._mode_hint = QLabel("Audio plays inline  •  Video opens in a window")
        self._mode_hint.setFont(QFont("Segoe UI", 8))
        self._mode_hint.setStyleSheet(f"color: {TH.text3}; background: transparent;")
        mode_lay.addWidget(self._mode_hint)
        main.addWidget(mode_bar)
        self._update_mode_btns()
        self._status_bar = QLabel("  Trending suggestions loading…")
        self._status_bar.setFixedHeight(28)
        self._status_bar.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._status_bar.setStyleSheet(f"color: {TH.text3}; background: {TH.bg}; padding-left: 16px; letter-spacing: 1px;")
        main.addWidget(self._status_bar)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(f"""
QProgressBar {{ background: {TH.border}; border: none; }}
QProgressBar::chunk {{ background: {TH.accent}; }}
""")
        self._progress.hide()
        main.addWidget(self._progress)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {TH.bg}; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._results_widget = QWidget()
        self._results_widget.setStyleSheet(f"background: {TH.bg};")
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(12, 8, 12, 12)
        self._results_layout.setSpacing(4)
        self._results_layout.addStretch()
        scroll.setWidget(self._results_widget)
        main.addWidget(scroll, 1)
        self._dl_bar = QWidget()
        self._dl_bar.setStyleSheet(f"background: {TH.surface};")
        self._dl_bar.setFixedHeight(44)
        self._dl_bar.hide()
        dl_bar_lay = QHBoxLayout(self._dl_bar)
        dl_bar_lay.setContentsMargins(16, 0, 16, 0)
        dl_bar_lay.setSpacing(8)
        self._dl_icon = QLabel("⬇")
        self._dl_icon.setStyleSheet(f"color: {TH.green}; background: transparent; font-size: 14px;")
        self._dl_title = QLabel("")
        self._dl_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._dl_title.setStyleSheet(f"color: {TH.text}; background: transparent;")
        self._dl_prog = QProgressBar()
        self._dl_prog.setRange(0, 100)
        self._dl_prog.setValue(0)
        self._dl_prog.setFixedHeight(4)
        self._dl_prog.setTextVisible(False)
        self._dl_prog.setStyleSheet(f"""
QProgressBar {{ background: {TH.border}; border-radius: 2px; border: none; }}
QProgressBar::chunk {{ background: {TH.green}; border-radius: 2px; }}
""")
        dl_bar_lay.addWidget(self._dl_icon)
        dl_bar_lay.addWidget(self._dl_title)
        dl_bar_lay.addWidget(self._dl_prog, 1)
        main.addWidget(self._dl_bar)
        self._now_playing = NowPlayingBar()
        self._now_playing._stop_btn.clicked.connect(self._stop_stream)
        main.addWidget(self._now_playing)
    def _set_play_mode(self, mode: str):
        if self._play_mode == mode:
            return
        self._stop_stream()
        self._play_mode = mode
        self._update_mode_btns()
    def _update_mode_btns(self):
        audio_active = self._play_mode == "audio"
        a_bg = TH.accent if audio_active else TH.card
        a_tc = "#ffffff" if audio_active else TH.text2
        a_bd = TH.accent if audio_active else TH.border
        v_bg = TH.blue if not audio_active else TH.card
        v_tc = "#ffffff" if not audio_active else TH.text2
        v_bd = TH.blue if not audio_active else TH.border
        self._audio_mode_btn.setStyleSheet(f"""
QPushButton {{ background: {a_bg}; color: {a_tc}; border: 1px solid {a_bd}; border-radius: 8px;
    font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; padding: 0 10px; }}
QPushButton:hover {{ border-color: {TH.accent}; }}
""")
        self._video_mode_btn.setStyleSheet(f"""
QPushButton {{ background: {v_bg}; color: {v_tc}; border: 1px solid {v_bd}; border-radius: 8px;
    font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; padding: 0 10px; }}
QPushButton:hover {{ border-color: {TH.blue}; }}
""")
        if audio_active:
            self._mode_hint.setText("Audio plays inline  •  Video opens in a window")
        else:
            self._mode_hint.setText("Video opens in a separate window")
    def _clear_results(self):
        self._card_map.clear()
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for w in self._thumb_loaders:
            if w.isRunning():
                w.quit()
        self._thumb_loaders.clear()
    def _populate_results(self, items: list, section_label: str = ""):
        self._clear_results()
        if section_label:
            lbl = QLabel(section_label.upper())
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {TH.text3}; letter-spacing: 2px; background: transparent;")
            lbl.setContentsMargins(4, 4, 0, 4)
            self._results_layout.insertWidget(0, lbl)
        if not items:
            no_res = QLabel("  No results found. Try a different search.")
            no_res.setFont(QFont("Segoe UI", 10))
            no_res.setStyleSheet(f"color: {TH.text3}; background: transparent;")
            self._results_layout.insertWidget(self._results_layout.count() - 1, no_res)
            return
        for i, item in enumerate(items):
            card = ResultCard(item)
            card.play_clicked.connect(self._on_play)
            card.download_clicked.connect(self._on_download)
            card.fav_clicked.connect(lambda it: None)
            self._results_layout.insertWidget(self._results_layout.count() - 1, card)
            vid_id = item.get("id", "")
            thumb_url = item.get("thumbnail", "")
            if vid_id and thumb_url:
                self._card_map[vid_id] = card
                loader = ThumbnailLoader(vid_id, thumb_url)
                loader.loaded.connect(self._on_thumb_loaded)
                loader.start()
                self._thumb_loaders.append(loader)
    def _on_thumb_loaded(self, vid_id: str, pm: QPixmap):
        card = self._card_map.get(vid_id)
        if card:
            card.set_thumbnail(pm)
    def _do_search(self):
        query = self._search_box.text().strip()
        if not query:
            return
        self._status_bar.setText(f"  SEARCHING: {query}…")
        self._progress.show()
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
        self._search_worker = SearchWorker(query, max_results=12)
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.start()
    def _on_search_results(self, items: list):
        self._progress.hide()
        query = self._search_box.text().strip()
        self._status_bar.setText(f"  RESULTS: {query}")
        self._populate_results(items, f"Results for \"{query}\"")
    def _on_search_error(self, err: str):
        self._progress.hide()
        self._status_bar.setText("  SEARCH ERROR")
        self._clear_results()
        lbl = QLabel(f"  Error: {err}")
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet(f"color: {TH.accent}; background: transparent;")
        self._results_layout.insertWidget(0, lbl)
    def _load_trending(self):
        self._status_bar.setText("  TRENDING SUGGESTIONS")
        self._progress.show()
        self._trending_worker = TrendingWorker()
        self._trending_worker.results_ready.connect(self._on_trending_results)
        self._trending_worker.error.connect(lambda e: self._on_trending_done())
        self._trending_worker.start()
    def _on_trending_results(self, items: list):
        self._progress.hide()
        self._status_bar.setText("  TRENDING NOW")
        self._populate_results(items, "Trending Music")
    def _on_trending_done(self):
        self._progress.hide()
        self._status_bar.setText("  TRENDING SUGGESTIONS")
    def _on_play(self, item: dict):
        self._current_item = item
        if self._play_mode == "video":
            self._play_video(item)
        else:
            self._play_audio(item)
    def _play_audio(self, item: dict):
        self._now_playing.set_item(item, "Extracting stream URL…")
        self._progress.show()
        if self._stream_worker and self._stream_worker.isRunning():
            self._stream_worker.quit()
        url = item.get("url", "")
        self._stream_worker = StreamUrlWorker(url, mode="audio")
        self._stream_worker.url_ready.connect(self._on_stream_ready)
        self._stream_worker.error.connect(self._on_stream_error)
        self._stream_worker.start()
    def _play_video(self, item: dict):
        if not QT_MM_OK:
            QMessageBox.warning(self, "Not Available", "QtMultimedia is required for video playback.")
            return
        self._now_playing.set_item(item, "Extracting video stream…")
        self._progress.show()
        if self._stream_worker and self._stream_worker.isRunning():
            self._stream_worker.quit()
        url = item.get("url", "")
        self._stream_worker = StreamUrlWorker(url, mode="video")
        self._stream_worker.url_ready.connect(self._on_video_stream_ready)
        self._stream_worker.error.connect(self._on_stream_error)
        self._stream_worker.start()
    def _on_stream_ready(self, stream_url: str, mode: str, meta: dict):
        self._progress.hide()
        if not stream_url:
            self._now_playing.set_status("Failed to get stream URL")
            return
        if QT_MM_OK and self._player:
            self._player.stop()
            self._player.setSource(QUrl(stream_url))
            self._player.play()
            self._now_playing.set_status("▶ Playing…")
        elif PYGAME_OK:
            try:
                import pygame
                pygame.mixer.music.load(stream_url)
                pygame.mixer.music.play()
                self._now_playing.set_status("▶ Playing…")
            except Exception as ex:
                self._now_playing.set_status(f"Error: {ex}")
        else:
            self._now_playing.set_status("No audio backend available")
    def _on_video_stream_ready(self, stream_url: str, mode: str, meta: dict):
        self._progress.hide()
        if not stream_url:
            self._now_playing.set_status("Failed to get video stream URL")
            return
        if self._video_popup and self._video_popup.isVisible():
            self._video_player.stop()
            self._video_popup.close()
        self._video_popup = VideoPopup(self)
        title = self._current_item.get("title", "Unknown") if self._current_item else ""
        self._video_popup.set_title(title)
        self._video_popup.set_status("▶ Playing…")
        self._video_popup.finished.connect(self._on_video_popup_closed)
        self._video_player.setVideoOutput(self._video_popup.video_widget())
        self._video_player.setSource(QUrl(stream_url))
        self._video_popup.show()
        self._video_player.play()
        self._now_playing.set_item(self._current_item, "▶ Playing video…")
    def _on_video_popup_closed(self):
        if self._video_player:
            self._video_player.stop()
            self._video_player.setSource(QUrl())
        self._now_playing.stop()
    def _on_stream_error(self, err: str):
        self._progress.hide()
        self._now_playing.set_status(f"Error: {err[:60]}")
    def _on_state_changed(self, state):
        if not QT_MM_OK:
            return
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._now_playing.set_status("▶ Playing…")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._now_playing.set_status("⏸ Paused")
        else:
            self._now_playing.set_status("Stopped")
    def _on_video_state_changed(self, state):
        if not QT_MM_OK:
            return
        if self._video_popup and self._video_popup.isVisible():
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self._video_popup.set_status("▶ Playing…")
            elif state == QMediaPlayer.PlaybackState.PausedState:
                self._video_popup.set_status("⏸ Paused")
            else:
                self._video_popup.set_status("Stopped")
    def _stop_stream(self):
        if QT_MM_OK and self._player:
            self._player.stop()
        if QT_MM_OK and self._video_player:
            self._video_player.stop()
            self._video_player.setSource(QUrl())
        if self._video_popup and self._video_popup.isVisible():
            self._video_popup.close()
            self._video_popup = None
        elif PYGAME_OK:
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._now_playing.stop()
        self._current_item = None
    def _on_download(self, item: dict, fmt: str):
        url = item.get("url", "")
        title = item.get("title", "Unknown")
        if not url:
            QMessageBox.warning(self, "No URL", "Could not get video URL.")
            return
        quality = "256" if fmt == "MP3" else "720p"
        self._dl_bar.show()
        self._dl_title.setText(title[:40] + "…" if len(title) > 40 else title)
        self._dl_prog.setValue(0)
        self._dl_icon.setStyleSheet(f"color: {TH.green if fmt == 'MP3' else TH.blue}; background: transparent; font-size: 14px;")
        if self._dl_worker and self._dl_worker.isRunning():
            self._dl_worker.quit()
        self._dl_worker = DownloadWorker(url, fmt, quality, self._app.save_path)
        self._dl_worker.progress.connect(lambda pct, msg: self._dl_prog.setValue(int(pct)))
        self._dl_worker.finished.connect(self._on_dl_done)
        self._dl_worker.error.connect(self._on_dl_error)
        self._dl_worker.start()
    def _on_dl_done(self, title, fmt, quality):
        self._dl_prog.setValue(100)
        self._dl_title.setText(f"✅ Done: {title[:30]}")
        QTimer.singleShot(3000, self._dl_bar.hide)
    def _on_dl_error(self, err: str):
        self._dl_prog.setValue(0)
        self._dl_title.setText(f"❌ {err[:50]}")
        QTimer.singleShot(4000, self._dl_bar.hide)
    def on_show(self):
        if not hasattr(self, "_loaded_trending"):
            self._loaded_trending = True
            QTimer.singleShot(300, self._load_trending)
    def on_hide(self):
        pass