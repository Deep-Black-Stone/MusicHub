import os
import random
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from theme.engine import TH, blend_color
from ui.widgets import (AlbumArtWidget, RoundedCard,
                        GlowButton, IconButton, SeekSlider, VolumeSlider,
                        FolderSidebarItem, TrackRowWidget)
from ui.dialogs import show_music_info, show_shortcuts_dialog
from ui.lyrics_widget import LyricsWidget
from core.library import MediaLibrary
from core.favorites import FavoritesManager
from core.scanner import ScanWorker
from core.lyrics import LyricsWorker, load_lrc_file
from utils.media import get_audio_tags, get_album_art, fmt_time, AUDIO_EXTS
class MusicScreen(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._library = MediaLibrary("audio")
        self._current_folder = None
        self._all_files = []
        self._displayed_files = []
        self._cur_idx = 0
        self._shuffle = False
        self._repeat = False
        self._muted = False
        self._pre_mute_vol = 1.0
        self._player = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._audio_out.setVolume(1.0)
        self._player.setAudioOutput(self._audio_out)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.errorOccurred.connect(self._on_error)
        self._seeking = False
        self._fav_only = False
        self._scanner = None
        self._lyrics_worker = None
        self._build()
        self._library.library_changed.connect(self._on_library_changed)
        QTimer.singleShot(100, self._initial_scan)
    def _initial_scan(self):
        folders = self._library.get_folders()
        if folders:
            self._run_scan(folders)
    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background: {TH.surface};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)
        sb_hdr = QWidget()
        sb_hdr.setFixedHeight(44)
        sb_hdr.setStyleSheet(f"background: {TH.surface}; border-bottom: 1px solid {TH.border};")
        sb_hdr_lay = QHBoxLayout(sb_hdr)
        sb_hdr_lay.setContentsMargins(12, 0, 8, 0)
        folders_lbl = QLabel("FOLDERS")
        folders_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        folders_lbl.setStyleSheet(f"color: {TH.text3}; letter-spacing: 2px; background: transparent;")
        add_folder_btn = QPushButton("+")
        add_folder_btn.setFixedSize(26, 26)
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.setToolTip("Add Folder")
        add_folder_btn.setStyleSheet(f"QPushButton {{ background: {TH.accent}; color: white; border: none; border-radius: 13px; font-size: 16px; font-weight: bold; }} QPushButton:hover {{ background: {TH.accent2}; }}")
        add_folder_btn.clicked.connect(self._add_folder)
        sb_hdr_lay.addWidget(folders_lbl)
        sb_hdr_lay.addStretch()
        sb_hdr_lay.addWidget(add_folder_btn)
        sb_lay.addWidget(sb_hdr)
        self._folder_scroll = QScrollArea()
        self._folder_scroll.setWidgetResizable(True)
        self._folder_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._folder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._folder_scroll.setStyleSheet(f"background: {TH.surface}; border: none;")
        self._folder_list_widget = QWidget()
        self._folder_list_widget.setStyleSheet(f"background: {TH.surface};")
        self._folder_list_layout = QVBoxLayout(self._folder_list_widget)
        self._folder_list_layout.setContentsMargins(4, 4, 4, 4)
        self._folder_list_layout.setSpacing(2)
        all_item = self._make_folder_item("__all__", 0, True)
        self._folder_list_layout.addWidget(all_item)
        self._folder_list_layout.addStretch()
        self._folder_scroll.setWidget(self._folder_list_widget)
        sb_lay.addWidget(self._folder_scroll, 1)
        clr_btn = QPushButton("Clear All")
        clr_btn.setFixedHeight(36)
        clr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clr_btn.setStyleSheet(f"QPushButton {{ background: {TH.card}; color: {TH.text2}; border-top: 1px solid {TH.border}; border-left: none; border-right: none; border-bottom: none; font-family: 'Segoe UI'; font-size: 10px; font-weight: 700; }} QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}")
        clr_btn.clicked.connect(self._clear_all)
        sb_lay.addWidget(clr_btn)
        root.addWidget(sidebar)
        main_col = QWidget()
        main_col.setStyleSheet(f"background: {TH.bg};")
        main_lay = QVBoxLayout(main_col)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)
        player_bg = QWidget()
        player_bg.setMinimumHeight(270)
        player_bg.setMaximumHeight(340)
        player_bg.setStyleSheet(f"background: {TH.bg};")
        player_lay = QVBoxLayout(player_bg)
        player_lay.setContentsMargins(0, 0, 0, 0)
        player_lay.setSpacing(0)
        sec_row = QHBoxLayout()
        sec_row.setContentsMargins(20, 10, 14, 0)
        sec_lbl = QLabel("MUSIC PLAYER")
        sec_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec_lbl.setStyleSheet(f"color: {TH.text3}; letter-spacing: 2px; background: transparent;")
        kb_btn = QPushButton("Shortcuts")
        kb_btn.setFixedHeight(26)
        kb_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kb_btn.setStyleSheet(f"QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border}; border-radius: 8px; font-size: 9px; font-weight: 700; padding: 0 8px; }} QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}")
        kb_btn.clicked.connect(lambda: show_shortcuts_dialog(self))
        sec_row.addWidget(sec_lbl)
        sec_row.addStretch()
        sec_row.addWidget(kb_btn)
        player_lay.addLayout(sec_row)
        art_row = QHBoxLayout()
        art_row.setContentsMargins(20, 8, 20, 0)
        art_row.setSpacing(16)
        self._album_art = AlbumArtWidget(size=110)
        art_row.addWidget(self._album_art)
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.addStretch()
        self._track_lbl = QLabel("Add a folder to get started")
        self._track_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._track_lbl.setStyleSheet(f"color: {TH.text}; background: transparent;")
        self._track_lbl.setWordWrap(True)
        self._artist_lbl = QLabel("Unknown Artist")
        self._artist_lbl.setFont(QFont("Segoe UI", 9))
        self._artist_lbl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        self._counter_lbl = QLabel("0 / 0")
        self._counter_lbl.setFont(QFont("Segoe UI", 9))
        self._counter_lbl.setStyleSheet(f"color: {TH.accent}; background: transparent;")
        sr_row = QHBoxLayout()
        sr_row.setSpacing(6)
        self._shuf_btn = QPushButton("Shuffle")
        self._shuf_btn.setFixedHeight(26)
        self._shuf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._shuf_btn.clicked.connect(self._toggle_shuffle)
        self._rep_btn = QPushButton("Repeat")
        self._rep_btn.setFixedHeight(26)
        self._rep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rep_btn.clicked.connect(self._toggle_repeat)
        sr_row.addWidget(self._shuf_btn)
        sr_row.addWidget(self._rep_btn)
        sr_row.addStretch()
        self._update_sr_btns()
        info_col.addWidget(self._track_lbl)
        info_col.addWidget(self._artist_lbl)
        info_col.addWidget(self._counter_lbl)
        info_col.addLayout(sr_row)
        info_col.addStretch()
        art_row.addLayout(info_col)
        player_lay.addLayout(art_row)
        seek_lay = QVBoxLayout()
        seek_lay.setContentsMargins(20, 6, 20, 0)
        seek_lay.setSpacing(2)
        self._seek_slider = SeekSlider(TH.accent)
        self._seek_slider.sliderPressed.connect(self._on_seek_press)
        self._seek_slider.sliderReleased.connect(self._on_seek_release)
        self._seek_slider.seek_requested.connect(self._on_click_seek)
        time_row = QHBoxLayout()
        self._t_elapsed = QLabel("0:00")
        self._t_elapsed.setFont(QFont("Consolas", 9))
        self._t_elapsed.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        self._t_total = QLabel("0:00")
        self._t_total.setFont(QFont("Consolas", 9))
        self._t_total.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        time_row.addWidget(self._t_elapsed)
        time_row.addStretch()
        time_row.addWidget(self._t_total)
        seek_lay.addWidget(self._seek_slider)
        seek_lay.addLayout(time_row)
        player_lay.addLayout(seek_lay)
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(20, 4, 20, 0)
        ctrl_row.setSpacing(8)
        self._prev_btn = IconButton("Prev", 40, "Previous (P)")
        self._prev_btn.clicked.connect(self._prev_track)
        self._pp_btn = GlowButton("Play", TH.accent)
        self._pp_btn.setFixedHeight(42)
        self._pp_btn.setFixedWidth(120)
        self._pp_btn.clicked.connect(self._toggle_play)
        self._stop_btn = IconButton("Stop", 40, "Stop (S)")
        self._stop_btn.clicked.connect(self._stop)
        self._next_btn = IconButton("Next", 40, "Next (N)")
        self._next_btn.clicked.connect(self._next_track)
        ctrl_row.addWidget(self._prev_btn)
        ctrl_row.addWidget(self._pp_btn)
        ctrl_row.addWidget(self._stop_btn)
        ctrl_row.addWidget(self._next_btn)
        ctrl_row.addStretch()
        self._vol_icon = QLabel("Vol")
        self._vol_icon.setStyleSheet(f"color: {TH.text2}; background: transparent; font-size: 10px;")
        self._vol_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self._vol_icon.mousePressEvent = lambda _: self._toggle_mute()
        self._vol_slider = VolumeSlider()
        self._vol_slider.valueChanged.connect(self._set_volume)
        self._vol_pct = QLabel("100%")
        self._vol_pct.setFont(QFont("Segoe UI", 8))
        self._vol_pct.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        ctrl_row.addWidget(self._vol_icon)
        ctrl_row.addWidget(self._vol_slider)
        ctrl_row.addWidget(self._vol_pct)
        player_lay.addLayout(ctrl_row)
        player_lay.addStretch()
        main_lay.addWidget(player_bg)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {TH.border}; }}")
        playlist_container = QWidget()
        playlist_container.setStyleSheet(f"background: {TH.bg};")
        pl_container_lay = QVBoxLayout(playlist_container)
        pl_container_lay.setContentsMargins(0, 0, 0, 0)
        pl_container_lay.setSpacing(0)
        pl_hdr = QHBoxLayout()
        pl_hdr.setContentsMargins(16, 4, 16, 4)
        pl_lbl = QLabel("PLAYLIST")
        pl_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        pl_lbl.setStyleSheet(f"color: {TH.text3}; letter-spacing: 2px; background: transparent;")
        self._scan_status = QLabel("")
        self._scan_status.setFont(QFont("Segoe UI", 8))
        self._scan_status.setStyleSheet(f"color: {TH.text3}; background: transparent;")
        self._fav_filter_btn = QPushButton("★ Favorites")
        self._fav_filter_btn.setFixedHeight(24)
        self._fav_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fav_only = False
        self._fav_filter_btn.clicked.connect(self._toggle_fav_filter)
        self._update_fav_filter_btn_style()
        pl_hdr.addWidget(pl_lbl)
        pl_hdr.addStretch()
        pl_hdr.addWidget(self._fav_filter_btn)
        pl_hdr.addWidget(self._scan_status)
        pl_container_lay.addLayout(pl_hdr)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(f"background: {TH.bg}; border: none;")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._pl_widget = QWidget()
        self._pl_widget.setStyleSheet(f"background: {TH.bg};")
        self._pl_layout = QVBoxLayout(self._pl_widget)
        self._pl_layout.setContentsMargins(12, 4, 12, 12)
        self._pl_layout.setSpacing(3)
        self._pl_layout.addStretch()
        self._scroll.setWidget(self._pl_widget)
        pl_container_lay.addWidget(self._scroll, 1)
        splitter.addWidget(playlist_container)
        self._lyrics_widget = LyricsWidget()
        self._lyrics_widget.load_lrc_requested.connect(self._load_lrc_file)
        self._lyrics_widget.seek_requested.connect(self._on_lyrics_seek)
        self._lyrics_widget.setMinimumWidth(160)
        splitter.addWidget(self._lyrics_widget)
        splitter.setSizes([320, 240])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_lay.addWidget(splitter, 1)
        root.addWidget(main_col, 1)
    def _make_folder_item(self, folder, count, active=False):
        if folder == "__all__":
            display_count = self._library.total_count()
        else:
            display_count = count
        item = FolderSidebarItem(folder if folder != "__all__" else ".", display_count, active)
        item._folder_key = folder
        item.clicked.connect(self._on_folder_click)
        return item
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
        if folder_key == "__all__" or folder_key == ".":
            self._current_folder = None
            self._displayed_files = list(self._all_files)
        else:
            self._current_folder = folder_key
            self._displayed_files = self._library.get_folder_files(folder_key)
        self._rebuild_sidebar()
        self._refresh_playlist()
        self._update_counter()
    def _add_folder(self):
        while True:
            f = QFileDialog.getExistingDirectory(self, "Pick a music folder", self._app.save_path)
            if not f:
                break
            added = self._library.add_folder(f)
            if added:
                self._run_scan([f])
            reply = QMessageBox.question(self, "Add More?", f"Added:\n{f}\n\nAdd another folder?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                break
    def _run_scan(self, folders):
        self._scan_status.setText("Scanning...")
        self._scanner = ScanWorker(folders, AUDIO_EXTS)
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
        self._scan_status.setText(f"{self._library.total_count()} tracks")
        self._all_files = self._library.get_all_files()
        if self._current_folder is None:
            self._displayed_files = list(self._all_files)
        self._rebuild_sidebar()
        self._refresh_playlist()
        self._update_counter()
    def _clear_all(self):
        self._stop()
        self._library.clear()
        self._all_files = []
        self._displayed_files = []
        self._current_folder = None
        self._cur_idx = 0
        self._rebuild_sidebar()
        self._refresh_playlist()
        self._track_lbl.setText("Add a folder to get started")
        self._artist_lbl.setText("Unknown Artist")
        self._album_art.set_pixmap(None)
        self._update_counter()
        self._scan_status.setText("")
        self._lyrics_widget.clear()
    def _refresh_playlist(self):
        while self._pl_layout.count() > 1:
            item = self._pl_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self._displayed_files:
            lbl = QLabel("  No files found. Add a folder using the + button.")
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet(f"color: {TH.text3}; background: transparent;")
            self._pl_layout.insertWidget(0, lbl)
            return
        state = self._player.playbackState()
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        for i, fp in enumerate(self._displayed_files):
            active = i == self._cur_idx
            row = TrackRowWidget(i, fp, active, playing)
            row.clicked.connect(self._on_row_click)
            row.dbl_clicked.connect(self._load_and_play)
            row.fav_toggled.connect(self._on_fav_toggled)
            row.info_requested.connect(lambda idx, files=self._displayed_files: show_music_info(self, files[idx]))
            self._pl_layout.insertWidget(i, row)
    def _update_counter(self):
        n = len(self._displayed_files)
        self._counter_lbl.setText(f"{self._cur_idx + 1 if n else 0} / {n}")
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
        self._player.play()
        name = os.path.splitext(os.path.basename(fp))[0]
        self._track_lbl.setText(name if len(name) <= 36 else name[:33] + "...")
        tags = get_audio_tags(fp)
        self._artist_lbl.setText(tags["artist"] or "Unknown Artist")
        pm = get_album_art(fp)
        self._album_art.set_pixmap(pm)
        self._refresh_playlist()
        self._update_counter()
        self._fetch_lyrics(fp, tags)
    def _fetch_lyrics(self, filepath, tags):
        if self._lyrics_worker and self._lyrics_worker.isRunning():
            self._lyrics_worker.terminate()
            self._lyrics_worker.wait(500)
        self._lyrics_widget.set_fetching(True)
        artist = tags.get("artist") or ""
        title = tags.get("title") or os.path.splitext(os.path.basename(filepath))[0]
        self._lyrics_worker = LyricsWorker(artist, title, filepath)
        self._lyrics_worker.done.connect(self._on_lyrics_done)
        self._lyrics_worker.start()
    def _on_lyrics_done(self, lines, source):
        self._lyrics_widget.set_lyrics(lines, source)
    def _on_lyrics_seek(self, time_ms: int):
        """Seek audio to the timestamp of the clicked lyric line."""
        self._player.setPosition(time_ms)
    def _load_lrc_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open LRC File", self._app.save_path, "LRC Files (*.lrc)")
        if path:
            lines = load_lrc_file(path)
            if lines:
                self._lyrics_widget.set_lyrics(lines, "lrc_file")
            else:
                QMessageBox.warning(self, "LRC Error", "Could not parse the LRC file.")
    def _stop(self):
        self._player.stop()
        self._pp_btn.setText("Play")
        self._pp_btn.set_color(TH.accent)
        self._seek_slider.blockSignals(True)
        self._seek_slider.setValue(0)
        self._seek_slider.blockSignals(False)
        self._t_elapsed.setText("0:00")
    def _prev_track(self):
        if self._displayed_files:
            self._load_and_play((self._cur_idx - 1) % len(self._displayed_files))
    def _next_track(self):
        if not self._displayed_files:
            return
        if self._shuffle:
            idx = random.randint(0, len(self._displayed_files) - 1)
        else:
            idx = (self._cur_idx + 1) % len(self._displayed_files)
        self._load_and_play(idx)
    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._pp_btn.setText("Pause")
            self._pp_btn.set_color(blend_color(QColor(TH.accent), QColor(TH.bg), 0.3).name())
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._pp_btn.setText("Play")
            self._pp_btn.set_color(TH.accent)
        else:
            self._pp_btn.setText("Play")
            self._pp_btn.set_color(TH.accent)
            dur = self._player.duration()
            pos = self._player.position()
            if dur > 0 and pos >= dur - 300:
                QTimer.singleShot(200, self._auto_next)
    def _auto_next(self):
        if self._displayed_files:
            if self._repeat:
                self._load_and_play(self._cur_idx)
            else:
                self._next_track()
    def _on_position_changed(self, pos_ms):
        if not self._seeking:
            dur = self._player.duration()
            if dur > 0:
                self._seek_slider.blockSignals(True)
                self._seek_slider.setValue(int(pos_ms / dur * 1000))
                self._seek_slider.blockSignals(False)
            self._t_elapsed.setText(fmt_time(pos_ms / 1000))
        self._lyrics_widget.update_position(pos_ms)
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
    def _set_volume(self, val):
        self._audio_out.setVolume(val / 100)
        icon = "Mute" if val == 0 else "Vol"
        self._vol_icon.setText(icon)
        self._vol_pct.setText(f"{val}%")
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
    def _toggle_shuffle(self):
        self._shuffle = not self._shuffle
        self._update_sr_btns()
    def _toggle_repeat(self):
        self._repeat = not self._repeat
        self._update_sr_btns()
    def _update_sr_btns(self):
        for btn, active in [(self._shuf_btn, self._shuffle), (self._rep_btn, self._repeat)]:
            c = TH.accent if active else TH.card
            tc = TH.text if active else TH.text2
            btn.setStyleSheet(f"QPushButton {{ background: {c}; color: {tc}; border: 1px solid {TH.accent if active else TH.border}; border-radius: 8px; font-family: 'Segoe UI'; font-size: 9px; font-weight: 700; padding: 0 8px; }} QPushButton:hover {{ border-color: {TH.accent}; color: {TH.text}; }}")
    def _on_row_click(self, idx):
        state = self._player.playbackState()
        if idx == self._cur_idx and state in (QMediaPlayer.PlaybackState.PlayingState, QMediaPlayer.PlaybackState.PausedState):
            self._toggle_play()
        else:
            self._load_and_play(idx)
    def _toggle_fav_filter(self):
        self._fav_only = not self._fav_only
        self._update_fav_filter_btn_style()
        self._apply_fav_filter()
    def _update_fav_filter_btn_style(self):
        if self._fav_only:
            self._fav_filter_btn.setStyleSheet(f"QPushButton {{ background: #ffd60a; color: #111; border: none; border-radius: 6px; font-size: 9px; font-weight: 700; padding: 0 8px; }} QPushButton:hover {{ background: #ffe566; }}")
        else:
            self._fav_filter_btn.setStyleSheet(f"QPushButton {{ background: {TH.card}; color: {TH.text3}; border: 1px solid {TH.border}; border-radius: 6px; font-size: 9px; font-weight: 700; padding: 0 8px; }} QPushButton:hover {{ color: #ffd60a; }}")
    def _apply_fav_filter(self):
        fav_mgr = FavoritesManager.get()
        if self._fav_only:
            self._displayed_files = [f for f in self._all_files if fav_mgr.is_fav(f)]
        elif self._current_folder is None:
            self._displayed_files = list(self._all_files)
        else:
            self._displayed_files = self._library.get_folder_files(self._current_folder)
        self._refresh_playlist()
        self._update_counter()
    def _on_fav_toggled(self, idx):
        if self._fav_only:
            self._apply_fav_filter()
    def handle_key(self, key, modifiers):
        shift = modifiers & Qt.KeyboardModifier.ShiftModifier
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        if key == Qt.Key.Key_Space:
            self._toggle_play()
            return True
        if key == Qt.Key.Key_S and not ctrl:
            self._stop()
            return True
        if key == Qt.Key.Key_N and not ctrl:
            self._next_track()
            return True
        if key == Qt.Key.Key_P and not ctrl:
            self._prev_track()
            return True
        if key == Qt.Key.Key_Right and not ctrl:
            self._seek_forward(30000 if shift else 5000)
            return True
        if key == Qt.Key.Key_Left and not ctrl:
            self._seek_backward(30000 if shift else 5000)
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
        if key == Qt.Key.Key_M:
            self._toggle_mute()
            return True
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            v = (key - Qt.Key.Key_0) * 10
            self._vol_slider.setValue(v)
            self._set_volume(v)
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
        self._update_counter()
        self._scan_status.setText(f"{self._library.total_count()} tracks")
    def refresh_after_download(self):
        sp = self._app.save_path
        if sp not in self._library.get_folders():
            self._library.add_folder(sp)
            self._run_scan([sp])
    def on_show(self):
        self._update_counter()
    def on_hide(self):
        pass