from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, blend_color
from ui.widgets import RoundedCard, GlowButton, IconButton, ElideLabel
from core.downloader import DownloadWorker, DownloadQueue, PlaylistProbeWorker, QUALITY_OPTIONS
from utils.config import save_config
STATUS_COLORS = {
    "queued": None,
    "downloading": "#4361ee",
    "done": "#06d6a0",
    "error": "#e63946",
}
class VideoEntryRow(QWidget):
    checkbox_changed = pyqtSignal(int, bool)
    def __init__(self, idx: int, item: dict, parent=None):
        super().__init__(parent)
        self._idx = idx
        self._item = item
        self._status = "queued"
        self._progress = 0.0
        self.setFixedHeight(52)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)
        self._chk = QCheckBox()
        self._chk.setChecked(True)
        self._chk.toggled.connect(lambda v: self.checkbox_changed.emit(self._idx, v))
        self._chk.setStyleSheet(f"QCheckBox::indicator{{width:16px;height:16px;border-radius:4px;border:1.5px solid {TH.border};background:{TH.surface};}}QCheckBox::indicator:checked{{background:{TH.accent};border-color:{TH.accent};}}")
        lay.addWidget(self._chk)
        num = QLabel(f"{idx+1:02d}")
        num.setFixedWidth(28)
        num.setFont(QFont("Consolas", 8))
        num.setStyleSheet(f"color:{TH.text3};background:transparent;")
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(num)
        info = QVBoxLayout()
        info.setSpacing(1)
        title = item.get("title", "Unknown")
        self._title_lbl = QLabel(title[:58] + "…" if len(title) > 58 else title)
        self._title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color:{TH.text};background:transparent;")
        sub_parts = []
        if item.get("channel"):
            sub_parts.append(item["channel"])
        if item.get("duration") and item["duration"] != "—":
            sub_parts.append(item["duration"])
        self._sub_lbl = QLabel("  •  ".join(sub_parts) if sub_parts else "")
        self._sub_lbl.setFont(QFont("Segoe UI", 8))
        self._sub_lbl.setStyleSheet(f"color:{TH.text2};background:transparent;")
        info.addWidget(self._title_lbl)
        info.addWidget(self._sub_lbl)
        lay.addLayout(info, 1)
        self._status_lbl = QLabel("")
        self._status_lbl.setFixedWidth(72)
        self._status_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(f"color:{TH.text3};background:transparent;border-radius:4px;")
        lay.addWidget(self._status_lbl)
        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, 100)
        self._prog_bar.setValue(0)
        self._prog_bar.setFixedWidth(80)
        self._prog_bar.setFixedHeight(5)
        self._prog_bar.setTextVisible(False)
        self._prog_bar.setStyleSheet(f"QProgressBar{{background:{TH.border};border-radius:2px;border:none;}}QProgressBar::chunk{{background:{TH.accent};border-radius:2px;}}")
        self._prog_bar.hide()
        lay.addWidget(self._prog_bar)
    def set_status(self, status: str, progress: float = 0.0):
        self._status = status
        self._progress = progress
        color = STATUS_COLORS.get(status)
        labels = {"queued": "QUEUED", "downloading": "⬇ DL", "done": "✓ DONE", "error": "✗ ERR"}
        lbl = labels.get(status, status.upper())
        self._status_lbl.setText(lbl)
        if color:
            self._status_lbl.setStyleSheet(f"color:{color};background:transparent;border-radius:4px;font-family:'Segoe UI';font-size:7px;font-weight:700;")
        else:
            self._status_lbl.setStyleSheet(f"color:{TH.text3};background:transparent;border-radius:4px;font-family:'Segoe UI';font-size:7px;font-weight:700;")
        if status == "downloading":
            self._prog_bar.show()
            self._prog_bar.setStyleSheet(f"QProgressBar{{background:{TH.border};border-radius:2px;border:none;}}QProgressBar::chunk{{background:{TH.blue};border-radius:2px;}}")
            self._prog_bar.setValue(int(progress))
        elif status == "done":
            self._prog_bar.show()
            self._prog_bar.setValue(100)
            self._prog_bar.setStyleSheet(f"QProgressBar{{background:{TH.border};border-radius:2px;border:none;}}QProgressBar::chunk{{background:{TH.green};border-radius:2px;}}")
        elif status == "error":
            self._prog_bar.show()
            self._prog_bar.setValue(100)
            self._prog_bar.setStyleSheet(f"QProgressBar{{background:{TH.border};border-radius:2px;border:none;}}QProgressBar::chunk{{background:#e63946;border-radius:2px;}}")
        else:
            self._prog_bar.hide()
        if status in ("downloading", "done", "error"):
            self._chk.setEnabled(False)
        self.update()
    def set_checked(self, v: bool):
        self._chk.setChecked(v)
    def is_checked(self) -> bool:
        return self._chk.isChecked()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = STATUS_COLORS.get(self._status)
        if color:
            bg = blend_color(QColor(color), QColor(TH.card), 0.88)
        else:
            bg = QColor(TH.card)
        path = QPainterPath()
        path.addRoundedRect(2, 1, self.width()-4, self.height()-2, 8, 8)
        p.fillPath(path, bg)
class DownloadScreen(QWidget):
    navigate_after = pyqtSignal(str)
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._fmt = "MP3"
        self._qual = "256"
        self._worker = None
        self._probe_worker = None
        self._playlist_items = []
        self._selected_ids = set()
        self._entry_rows = []
        self._playlist_title = ""
        self._queue = DownloadQueue(self)
        self._queue.item_started.connect(self._on_queue_item_started)
        self._queue.item_progress.connect(self._on_queue_item_progress)
        self._queue.item_finished.connect(self._on_queue_item_finished)
        self._queue.item_error.connect(self._on_queue_item_error)
        self._queue.all_done.connect(self._on_queue_all_done)
        self._build()
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background:{TH.bg};border:none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setStyleSheet(f"background:{TH.bg};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 20, 28, 24)
        lay.setSpacing(14)
        sec = QLabel("YOUTUBE DOWNLOADER")
        sec.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;")
        lay.addWidget(sec)
        url_card = RoundedCard(radius=12)
        url_card.setFixedHeight(56)
        url_lay = QHBoxLayout(url_card)
        url_lay.setContentsMargins(14, 0, 10, 0)
        url_lay.setSpacing(8)
        url_icon = QLabel("🔗")
        url_icon.setFont(QFont("Segoe UI Symbol", 14))
        url_icon.setStyleSheet("background:transparent;")
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("Paste YouTube link or playlist URL here…")
        self._url_edit.setStyleSheet(f"QLineEdit{{background:transparent;border:none;color:{TH.text};font-family:'Segoe UI';font-size:12px;}}")
        self._url_edit.returnPressed.connect(self._on_url_entered)
        self._url_edit.textChanged.connect(self._on_url_text_changed)
        clear_btn = IconButton("✕", size=28)
        clear_btn.clicked.connect(self._clear_url)
        self._probe_btn = QPushButton("Load")
        self._probe_btn.setFixedSize(52, 34)
        self._probe_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._probe_btn.setStyleSheet(f"QPushButton{{background:{TH.accent};color:white;border:none;border-radius:8px;font-family:'Segoe UI';font-size:10px;font-weight:700;}}QPushButton:hover{{background:{TH.accent2};}}")
        self._probe_btn.clicked.connect(self._on_url_entered)
        url_lay.addWidget(url_icon)
        url_lay.addWidget(self._url_edit, 1)
        url_lay.addWidget(clear_btn)
        url_lay.addWidget(self._probe_btn)
        lay.addWidget(url_card)
        self._probe_status = QLabel("")
        self._probe_status.setFont(QFont("Segoe UI", 8))
        self._probe_status.setStyleSheet(f"color:{TH.text3};background:transparent;")
        self._probe_status.hide()
        lay.addWidget(self._probe_status)
        self._probe_progress = QProgressBar()
        self._probe_progress.setRange(0, 0)
        self._probe_progress.setFixedHeight(3)
        self._probe_progress.setTextVisible(False)
        self._probe_progress.setStyleSheet(f"QProgressBar{{background:{TH.border};border:none;}}QProgressBar::chunk{{background:{TH.accent};}}")
        self._probe_progress.hide()
        lay.addWidget(self._probe_progress)
        self._playlist_panel = QWidget()
        self._playlist_panel.setStyleSheet(f"background:transparent;")
        pl_lay = QVBoxLayout(self._playlist_panel)
        pl_lay.setContentsMargins(0, 0, 0, 0)
        pl_lay.setSpacing(8)
        pl_hdr_row = QHBoxLayout()
        pl_hdr_row.setSpacing(8)
        self._pl_title_lbl = QLabel("")
        self._pl_title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._pl_title_lbl.setStyleSheet(f"color:{TH.text};background:transparent;")
        self._pl_count_lbl = QLabel("")
        self._pl_count_lbl.setFont(QFont("Segoe UI", 8))
        self._pl_count_lbl.setStyleSheet(f"color:{TH.text3};background:transparent;")
        pl_hdr_row.addWidget(self._pl_title_lbl)
        pl_hdr_row.addWidget(self._pl_count_lbl)
        pl_hdr_row.addStretch()
        self._sel_all_btn = QPushButton("Select All")
        self._sel_all_btn.setFixedHeight(26)
        self._sel_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sel_all_btn.setStyleSheet(f"QPushButton{{background:{TH.card};color:{TH.text2};border:1px solid {TH.border};border-radius:6px;font-family:'Segoe UI';font-size:9px;font-weight:700;padding:0 8px;}}QPushButton:hover{{color:{TH.text};border-color:{TH.accent};}}")
        self._sel_all_btn.clicked.connect(self._select_all)
        self._sel_none_btn = QPushButton("None")
        self._sel_none_btn.setFixedHeight(26)
        self._sel_none_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sel_none_btn.setStyleSheet(f"QPushButton{{background:{TH.card};color:{TH.text2};border:1px solid {TH.border};border-radius:6px;font-family:'Segoe UI';font-size:9px;font-weight:700;padding:0 8px;}}QPushButton:hover{{color:{TH.text};border-color:{TH.accent};}}")
        self._sel_none_btn.clicked.connect(self._select_none)
        pl_hdr_row.addWidget(self._sel_all_btn)
        pl_hdr_row.addWidget(self._sel_none_btn)
        pl_lay.addLayout(pl_hdr_row)
        list_card = RoundedCard(radius=10)
        list_inner = QVBoxLayout(list_card)
        list_inner.setContentsMargins(6, 6, 6, 6)
        list_inner.setSpacing(2)
        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_scroll.setStyleSheet(f"background:transparent;border:none;")
        self._list_scroll.setFixedHeight(220)
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background:transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        self._list_scroll.setWidget(self._list_widget)
        list_inner.addWidget(self._list_scroll)
        pl_lay.addWidget(list_card)
        lay.addWidget(self._playlist_panel)
        self._playlist_panel.hide()
        fmt_sec = QLabel("FORMAT")
        fmt_sec.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        fmt_sec.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;")
        lay.addWidget(fmt_sec)
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(10)
        self._fmt_btns = {}
        for fmt in ["MP3", "MP4"]:
            btn = QPushButton(fmt)
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, f=fmt: self._set_fmt(f))
            self._fmt_btns[fmt] = btn
            fmt_row.addWidget(btn)
        lay.addLayout(fmt_row)
        self._update_fmt_btns()
        qual_sec = QLabel("QUALITY")
        qual_sec.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        qual_sec.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;")
        lay.addWidget(qual_sec)
        self._qual_row = QHBoxLayout()
        self._qual_row.setSpacing(8)
        self._qual_btns = {}
        lay.addLayout(self._qual_row)
        self._rebuild_quality()
        path_sec = QLabel("SAVE FOLDER")
        path_sec.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        path_sec.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;")
        lay.addWidget(path_sec)
        path_card = RoundedCard(radius=12)
        path_card.setFixedHeight(50)
        path_lay = QHBoxLayout(path_card)
        path_lay.setContentsMargins(16, 0, 10, 0)
        self._path_lbl = ElideLabel(self._app.save_path)
        self._path_lbl.setFont(QFont("Segoe UI", 9))
        self._path_lbl.setStyleSheet(f"color:{TH.text2};background:transparent;")
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(72, 34)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(f"QPushButton{{background:{TH.border};color:{TH.text2};border:none;border-radius:8px;font-family:'Segoe UI';font-size:10px;font-weight:700;}}QPushButton:hover{{background:{TH.card};color:{TH.text};}}")
        browse_btn.clicked.connect(self._browse)
        path_lay.addWidget(self._path_lbl, 1)
        path_lay.addWidget(browse_btn)
        lay.addWidget(path_card)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self._dl_btn = GlowButton("⬇   DOWNLOAD", TH.accent)
        self._dl_btn.setFixedHeight(54)
        self._dl_btn.clicked.connect(self._start_download)
        self._stop_btn = QPushButton("⏹  Stop")
        self._stop_btn.setFixedHeight(54)
        self._stop_btn.setFixedWidth(100)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setStyleSheet(f"QPushButton{{background:{TH.card};color:{TH.text2};border:1px solid {TH.border};border-radius:12px;font-family:'Segoe UI';font-size:12px;font-weight:700;}}QPushButton:hover{{border-color:#e63946;color:#e63946;}}")
        self._stop_btn.clicked.connect(self._stop_download)
        self._stop_btn.hide()
        action_row.addWidget(self._dl_btn, 1)
        action_row.addWidget(self._stop_btn)
        lay.addLayout(action_row)
        prog_card = RoundedCard(radius=8)
        prog_card.setFixedHeight(68)
        prog_lay = QVBoxLayout(prog_card)
        prog_lay.setContentsMargins(14, 8, 14, 8)
        prog_lay.setSpacing(4)
        self._status_lbl = QLabel("Paste a YouTube link or playlist URL and tap Load")
        self._status_lbl.setFont(QFont("Segoe UI", 9))
        self._status_lbl.setStyleSheet(f"color:{TH.text2};background:transparent;")
        self._queue_lbl = QLabel("")
        self._queue_lbl.setFont(QFont("Segoe UI", 8))
        self._queue_lbl.setStyleSheet(f"color:{TH.text3};background:transparent;")
        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, 100)
        self._prog_bar.setValue(0)
        self._prog_bar.setFixedHeight(6)
        self._prog_bar.setTextVisible(False)
        self._prog_bar.setStyleSheet(f"QProgressBar{{background:{TH.border};border-radius:3px;}}QProgressBar::chunk{{background:{TH.accent};border-radius:3px;}}")
        prog_lay.addWidget(self._status_lbl)
        prog_lay.addWidget(self._queue_lbl)
        prog_lay.addWidget(self._prog_bar)
        lay.addWidget(prog_card)
        log_sec = QLabel("LOG")
        log_sec.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        log_sec.setStyleSheet(f"color:{TH.text3};letter-spacing:2px;")
        lay.addWidget(log_sec)
        log_card = RoundedCard(radius=10)
        log_inner = QVBoxLayout(log_card)
        log_inner.setContentsMargins(14, 10, 14, 10)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(110)
        self._log.setStyleSheet(f"QTextEdit{{background:transparent;border:none;color:{TH.text2};font-family:'Consolas','Courier New';font-size:10px;}}")
        log_inner.addWidget(self._log)
        lay.addWidget(log_card)
        lay.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self._update_dl_btn()
    def _update_fmt_btns(self):
        for fmt, btn in self._fmt_btns.items():
            active = fmt == self._fmt
            color = TH.accent if fmt == "MP3" else TH.blue
            if active:
                c2 = blend_color(QColor(color), QColor("#ffffff"), 0.15).name()
                bg = f"qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {color},stop:1 {c2})"
            else:
                bg = TH.card
            btn.setStyleSheet(f"QPushButton{{background:{bg};color:{TH.text if active else TH.text2};border:1px solid {color if active else TH.border};border-radius:12px;font-family:'Segoe UI';font-size:13px;font-weight:700;}}QPushButton:hover{{border-color:{color};}}")
    def _set_fmt(self, fmt):
        self._fmt = fmt
        self._update_fmt_btns()
        self._rebuild_quality()
        self._update_dl_btn()
        color = TH.accent if fmt == "MP3" else TH.blue
        self._prog_bar.setStyleSheet(f"QProgressBar{{background:{TH.border};border-radius:3px;}}QProgressBar::chunk{{background:{color};border-radius:3px;}}")
    def _rebuild_quality(self):
        for i in reversed(range(self._qual_row.count())):
            w = self._qual_row.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._qual_btns.clear()
        options = QUALITY_OPTIONS[self._fmt]
        self._qual = options[-1]
        for q in options:
            label = f"{q} kbps" if self._fmt == "MP3" else q
            btn = QPushButton(label)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, qv=q: self._set_qual(qv))
            self._qual_btns[q] = btn
            self._qual_row.addWidget(btn)
        self._update_qual_btns()
    def _update_qual_btns(self):
        accent = TH.accent if self._fmt == "MP3" else TH.blue
        for q, btn in self._qual_btns.items():
            active = q == self._qual
            btn.setStyleSheet(f"QPushButton{{background:{accent if active else TH.card};color:{TH.text if active else TH.text2};border:1px solid {accent if active else TH.border};border-radius:10px;font-family:'Consolas','Courier New';font-size:10px;font-weight:700;}}QPushButton:hover{{border-color:{accent};color:{TH.text};}}")
    def _set_qual(self, q):
        self._qual = q
        self._update_qual_btns()
    def _update_dl_btn(self):
        if self._playlist_items:
            checked = sum(1 for r in self._entry_rows if r.is_checked())
            label = f"⬇   DOWNLOAD SELECTED ({checked})" if checked > 0 else "⬇   DOWNLOAD"
        else:
            label = f"⬇   DOWNLOAD {self._fmt}"
        color = TH.accent if self._fmt == "MP3" else TH.blue
        self._dl_btn.setText(label)
        self._dl_btn.set_color(color)
    def _browse(self):
        f = QFileDialog.getExistingDirectory(self, "Save folder", self._app.save_path)
        if f:
            self._app.save_path = f
            self._path_lbl.setText(f)
            save_config({"last_save_path": f})
    def _clear_url(self):
        self._url_edit.clear()
        self._clear_playlist_panel()
    def _on_url_text_changed(self):
        self._clear_playlist_panel()
    def _clear_playlist_panel(self):
        if self._probe_worker and self._probe_worker.isRunning():
            self._probe_worker.abort()
            self._probe_worker.wait(500)
        self._playlist_items.clear()
        self._selected_ids.clear()
        self._entry_rows.clear()
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._playlist_panel.hide()
        self._probe_status.hide()
        self._probe_progress.hide()
        self._update_dl_btn()
    def _on_url_entered(self):
        url = self._url_edit.text().strip()
        if not url:
            return
        self._clear_playlist_panel()
        self._probe_status.setText("Loading URL…")
        self._probe_status.show()
        self._probe_progress.show()
        self._probe_btn.setEnabled(False)
        if self._probe_worker and self._probe_worker.isRunning():
            self._probe_worker.abort()
            self._probe_worker.wait(500)
        self._probe_worker = PlaylistProbeWorker(url)
        self._probe_worker.entry_found.connect(self._on_entry_found)
        self._probe_worker.probe_done.connect(self._on_probe_done)
        self._probe_worker.error.connect(self._on_probe_error)
        self._probe_worker.start()
    def _on_entry_found(self, item: dict):
        idx = len(self._playlist_items)
        self._playlist_items.append(item)
        self._selected_ids.add(item["id"] or item["url"])
        row = VideoEntryRow(idx, item)
        row.checkbox_changed.connect(self._on_checkbox_changed)
        self._entry_rows.append(row)
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)
        is_pl = item.get("is_playlist", False)
        if is_pl:
            self._playlist_panel.show()
            self._pl_title_lbl.setText(self._playlist_title or "Playlist")
            self._pl_count_lbl.setText(f"{len(self._playlist_items)} videos")
        else:
            self._playlist_panel.show()
            self._pl_title_lbl.setText("Single Video")
            self._pl_count_lbl.setText("")
        self._probe_status.setText(f"Found {len(self._playlist_items)} video(s)…")
        self._update_dl_btn()
    def _on_probe_done(self, items: list, playlist_title: str):
        self._probe_progress.hide()
        self._probe_btn.setEnabled(True)
        self._playlist_title = playlist_title
        count = len(items)
        if playlist_title:
            self._pl_title_lbl.setText(playlist_title)
            self._pl_count_lbl.setText(f"{count} videos")
            self._probe_status.setText(f"✓  Playlist loaded: {count} videos")
        else:
            self._probe_status.setText(f"✓  Video loaded")
        self._update_dl_btn()
    def _on_probe_error(self, err: str):
        self._probe_progress.hide()
        self._probe_btn.setEnabled(True)
        self._probe_status.setText(f"✗  Error: {err[:80]}")
        self._probe_status.setStyleSheet(f"color:#e63946;background:transparent;font-family:'Segoe UI';font-size:8px;")
        self._log.append(f"[Probe Error]  {err}")
    def _on_checkbox_changed(self, idx: int, checked: bool):
        if 0 <= idx < len(self._playlist_items):
            item = self._playlist_items[idx]
            key = item["id"] or item["url"]
            if checked:
                self._selected_ids.add(key)
            else:
                self._selected_ids.discard(key)
        self._update_dl_btn()
    def _select_all(self):
        self._selected_ids.clear()
        for row, item in zip(self._entry_rows, self._playlist_items):
            row.set_checked(True)
            self._selected_ids.add(item["id"] or item["url"])
        self._update_dl_btn()
    def _select_none(self):
        self._selected_ids.clear()
        for row in self._entry_rows:
            row.set_checked(False)
        self._update_dl_btn()
    def _start_download(self):
        url = self._url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a YouTube URL first.")
            return
        if self._playlist_items:
            selected = [item for item, row in zip(self._playlist_items, self._entry_rows) if row.is_checked()]
            if not selected:
                QMessageBox.warning(self, "Nothing Selected", "Please select at least one video to download.")
                return
            self._start_queue_download(selected)
        else:
            self._start_single_download(url)
    def _start_single_download(self, url: str):
        self._dl_btn.setEnabled(False)
        self._dl_btn.setText("  Preparing…")
        self._log.clear()
        self._prog_bar.setValue(0)
        self._worker = DownloadWorker(url, self._fmt, self._qual, self._app.save_path)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_line.connect(self._on_log)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self._stop_btn.show()
    def _start_queue_download(self, items: list):
        self._queue.clear()
        save_dir = self._app.save_path
        if self._playlist_title:
            safe = "".join(c for c in self._playlist_title if c not in r'\/:*?"<>|')
            save_dir = __import__("os").path.join(save_dir, safe)
            __import__("os").makedirs(save_dir, exist_ok=True)
        self._queue.set_options(self._fmt, self._qual, save_dir)
        self._queue.add_items(items)
        self._dl_btn.setEnabled(False)
        self._dl_btn.setText("  Downloading…")
        self._stop_btn.show()
        self._log.clear()
        self._prog_bar.setValue(0)
        done, error, total = self._queue.counts()
        self._queue_lbl.setText(f"Queue: 0 / {total}")
        self._status_lbl.setText("Starting queue…")
        self._log.append(f"[Queue]  {total} items  |  {self._fmt}  |  {self._qual}")
        if self._playlist_title:
            self._log.append(f"[Folder]  {save_dir}")
        self._queue.start()
    def _stop_download(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)
        self._queue.stop()
        self._prog_bar.setValue(0)
        self._status_lbl.setText("Stopped.")
        self._stop_btn.hide()
        self._dl_btn.setEnabled(True)
        self._update_dl_btn()
    def _on_queue_item_started(self, idx: int):
        if 0 <= idx < len(self._entry_rows):
            self._entry_rows[idx].set_status("downloading", 0)
        done, error, total = self._queue.counts()
        self._status_lbl.setText(f"Downloading {idx+1} of {total}…")
        self._queue_lbl.setText(f"Queue: {done} / {total}")
    def _on_queue_item_progress(self, idx: int, pct: float, msg: str):
        if 0 <= idx < len(self._entry_rows):
            self._entry_rows[idx].set_status("downloading", pct)
        self._prog_bar.setValue(int(pct))
        done, error, total = self._queue.counts()
        overall = int((done / total) * 100) if total else 0
        self._status_lbl.setText(f"{msg}")
    def _on_queue_item_finished(self, idx: int, title: str):
        if 0 <= idx < len(self._entry_rows):
            self._entry_rows[idx].set_status("done", 100)
        self._log.append(f"[✓]  {title}")
        done, error, total = self._queue.counts()
        self._queue_lbl.setText(f"Queue: {done} / {total}")
        overall = int((done / total) * 100) if total else 0
        self._prog_bar.setValue(overall)
    def _on_queue_item_error(self, idx: int, err: str):
        if 0 <= idx < len(self._entry_rows):
            self._entry_rows[idx].set_status("error")
        self._log.append(f"[✗]  {err[:80]}")
    def _on_queue_all_done(self):
        done, error, total = self._queue.counts()
        self._status_lbl.setText(f"✅  Done!  {done}/{total} downloaded  |  {error} errors  |  Saved to {self._app.save_path}")
        self._prog_bar.setValue(100)
        self._stop_btn.hide()
        self._dl_btn.setEnabled(True)
        self._update_dl_btn()
        dest = "music" if self._fmt == "MP3" else "video"
        self.navigate_after.emit(dest)
    def _on_progress(self, pct, msg):
        self._prog_bar.setValue(int(pct))
        self._status_lbl.setText(msg)
    def _on_log(self, line):
        self._log.append(line)
    def _on_done(self, title, fmt, quality):
        self._prog_bar.setValue(100)
        self._status_lbl.setText(f"✅  Done!  Saved to {self._app.save_path}")
        label = "⬇   DOWNLOAD MP3" if fmt == "MP3" else "⬇   DOWNLOAD MP4"
        self._dl_btn.setText(label)
        self._dl_btn.setEnabled(True)
        self._stop_btn.hide()
        self.navigate_after.emit("music" if fmt == "MP3" else "video")
    def _on_error(self, err):
        self._prog_bar.setValue(0)
        self._status_lbl.setText("❌  Download failed")
        self._on_log(f"[Error]  {err}")
        self._update_dl_btn()
        self._dl_btn.setEnabled(True)
        self._stop_btn.hide()
        QMessageBox.critical(self, "Error", f"{err}\n\nMake sure FFmpeg is installed.")
    def on_show(self):
        pass
    def on_hide(self):
        pass