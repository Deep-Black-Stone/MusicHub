import bisect
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, blend_color
_EASE_FAST = 0.28
_EASE_SLOW = 0.12
_SETTLE_PX = 0.8
class LyricsWidget(QWidget):
    load_lrc_requested = pyqtSignal()
    seek_requested = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lines = []
        self._times_ms = []
        self._current_idx = -1
        self._prev_idx = -1
        self._source = 'none'
        self._fetching = False
        self._synced = False
        self._c_accent = QColor(TH.accent)
        self._c_text3 = QColor(TH.text3)
        self._c_bg = QColor(TH.bg)
        self._c_text = QColor(TH.text)
        self._c_near1 = blend_color(QColor(TH.accent), QColor(TH.text3), 0.7)
        self._c_near2 = blend_color(QColor(TH.text3), QColor(TH.text), 0.3)
        self._c_active_bg = blend_color(QColor(TH.accent), QColor(TH.bg), 0.88)
        self._target_scroll = 0.0
        self._current_scroll = 0.0
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(16)
        self._scroll_timer.timeout.connect(self._scroll_step)
        self._build()
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        hdr = QWidget()
        hdr.setFixedHeight(40)
        hdr.setStyleSheet(f'background: {TH.surface}; border-bottom: 1px solid {TH.border};')
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 0, 8, 0)
        hdr_lay.setSpacing(6)
        icon = QLabel('🎤')
        icon.setFont(QFont('Segoe UI Symbol', 12))
        icon.setStyleSheet('background: transparent;')
        title = QLabel('LYRICS')
        title.setFont(QFont('Segoe UI', 8, QFont.Weight.Bold))
        title.setStyleSheet(f'color: {TH.text3}; letter-spacing: 2px; background: transparent;')
        self._src_lbl = QLabel('')
        self._src_lbl.setFont(QFont('Segoe UI', 7))
        self._src_lbl.setStyleSheet(f'color: {TH.text3}; background: transparent;')
        self._load_btn = QPushButton('📂 LRC')
        self._load_btn.setFixedHeight(26)
        self._load_btn.setFixedWidth(58)
        self._load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_btn.setToolTip('Load .lrc file')
        self._load_btn.setStyleSheet(f"""
QPushButton {{ background: {TH.card}; color: {TH.text2}; border: 1px solid {TH.border};
    border-radius: 6px; font-family: 'Segoe UI'; font-size: 8px; font-weight: 700; }}
QPushButton:hover {{ background: {TH.border}; color: {TH.text}; }}
""")
        self._load_btn.clicked.connect(self.load_lrc_requested)
        hdr_lay.addWidget(icon)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()
        hdr_lay.addWidget(self._src_lbl)
        hdr_lay.addWidget(self._load_btn)
        lay.addWidget(hdr)
        self._list = QListWidget()
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setStyleSheet(f"""
QListWidget {{
    background: {TH.bg};
    border: none;
    outline: none;
    padding: 4px 0;
}}
QListWidget::item {{
    padding: 6px 14px;
    border: none;
    color: {TH.text3};
    font-family: 'Segoe UI';
    font-size: 11px;
    border-radius: 6px;
    margin: 1px 6px;
}}
QListWidget::item:selected {{
    background: transparent;
    color: {TH.accent};
}}
QScrollBar:vertical {{
    background: {TH.bg}; width: 4px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {TH.border}; border-radius: 2px; min-height: 16px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
""")
        self._list.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self._list, 1)
        self._empty_lbl = QLabel('Searching for lyrics…')
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setFont(QFont('Segoe UI', 10))
        self._empty_lbl.setStyleSheet(f'color: {TH.text3}; background: {TH.bg}; padding: 40px;')
        self._empty_lbl.setWordWrap(True)
        lay.addWidget(self._empty_lbl)
        self._list.hide()
    def _on_item_clicked(self, item: QListWidgetItem):
        if not self._synced:
            return
        idx = self._list.row(item)
        if 0 <= idx < len(self._lines):
            self.seek_requested.emit(self._lines[idx].time_ms)
    def set_fetching(self, fetching: bool):
        self._fetching = fetching
        if fetching:
            self._lines = []
            self._times_ms = []
            self._current_idx = -1
            self._prev_idx = -1
            self._synced = False
            self._list.clear()
            self._list.hide()
            self._empty_lbl.setText('🎤  Searching for lyrics…')
            self._empty_lbl.show()
            self._src_lbl.setText('')
    def set_lyrics(self, lines: list, source: str):
        self._scroll_timer.stop()
        self._lines = lines
        self._times_ms = [ln.time_ms for ln in lines]
        self._current_idx = -1
        self._prev_idx = -1
        self._source = source
        self._synced = source in ('synced', 'lrc_file')
        self._list.clear()
        if not lines:
            self._list.hide()
            self._empty_lbl.setText('No lyrics found.\nTry loading a .lrc file.')
            self._empty_lbl.show()
            self._src_lbl.setText('')
            return
        self._empty_lbl.hide()
        self._list.show()
        self._list.setCursor(Qt.CursorShape.PointingHandCursor if self._synced else Qt.CursorShape.ArrowCursor)
        src_map = {'synced': '● synced', 'plain': '● plain', 'lrc_file': '● .lrc', 'none': ''}
        self._src_lbl.setText(src_map.get(source, ''))
        self._c_accent = QColor(TH.accent)
        self._c_text3 = QColor(TH.text3)
        self._c_bg = QColor(TH.bg)
        self._c_text = QColor(TH.text)
        self._c_near1 = blend_color(QColor(TH.accent), QColor(TH.text3), 0.7)
        self._c_near2 = blend_color(QColor(TH.text3), QColor(TH.text), 0.3)
        self._c_active_bg = blend_color(QColor(TH.accent), QColor(TH.bg), 0.88)
        base_font = QFont('Segoe UI', 10)
        for line in lines:
            item = QListWidgetItem(line.text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFont(base_font)
            item.setForeground(self._c_text3)
            item.setSizeHint(QSize(0, 26))
            self._list.addItem(item)
        self._target_scroll = 0.0
        self._current_scroll = 0.0
        sb = self._list.verticalScrollBar()
        if sb:
            sb.setValue(0)
    def clear(self):
        self._scroll_timer.stop()
        self._lines = []
        self._times_ms = []
        self._current_idx = -1
        self._prev_idx = -1
        self._synced = False
        self._list.clear()
        self._list.hide()
        self._empty_lbl.setText('Play a track to see lyrics')
        self._empty_lbl.show()
        self._src_lbl.setText('')
    def update_position(self, pos_ms: int):
        if not self._lines:
            return
        raw = bisect.bisect_right(self._times_ms, pos_ms) - 1
        idx = max(0, raw)
        if idx == self._current_idx:
            return
        prev = self._current_idx
        self._current_idx = idx
        self._update_item_style(prev, idx)
        self._scroll_to(idx)
    def _item_role(self, i: int, active: int) -> int:
        return min(abs(i - active), 3)
    def _apply_role(self, item: QListWidgetItem, role: int):
        if role == 0:
            item.setForeground(self._c_accent)
            item.setBackground(self._c_active_bg)
            item.setFont(QFont('Segoe UI', 13, QFont.Weight.Bold))
            item.setSizeHint(QSize(0, 44))
        elif role == 1:
            item.setForeground(self._c_near1)
            item.setBackground(QColor(0, 0, 0, 0))
            item.setFont(QFont('Segoe UI', 11))
            item.setSizeHint(QSize(0, 32))
        elif role == 2:
            item.setForeground(self._c_near2)
            item.setBackground(QColor(0, 0, 0, 0))
            item.setFont(QFont('Segoe UI', 10))
            item.setSizeHint(QSize(0, 28))
        else:
            item.setForeground(self._c_text3)
            item.setBackground(QColor(0, 0, 0, 0))
            item.setFont(QFont('Segoe UI', 10))
            item.setSizeHint(QSize(0, 26))
    def _update_item_style(self, prev_idx: int, new_idx: int):
        n = self._list.count()
        dirty = set()
        radius = 2
        if prev_idx >= 0:
            for i in range(max(0, prev_idx - radius), min(n, prev_idx + radius + 1)):
                dirty.add(i)
        for i in range(max(0, new_idx - radius), min(n, new_idx + radius + 1)):
            dirty.add(i)
        for i in sorted(dirty):
            item = self._list.item(i)
            if item:
                self._apply_role(item, self._item_role(i, new_idx))
    def _scroll_to(self, idx: int):
        item = self._list.item(idx)
        if not item:
            return
        sb = self._list.verticalScrollBar()
        if not sb:
            return
        offset = 0
        for i in range(idx):
            it = self._list.item(i)
            if it:
                offset += it.sizeHint().height() if it.sizeHint().height() > 0 else 26
        active_h = item.sizeHint().height() if item.sizeHint().height() > 0 else 44
        viewport_h = self._list.viewport().height()
        target = offset + active_h // 2 - viewport_h // 2
        target = max(0, min(target, sb.maximum()))
        self._target_scroll = float(target)
        self._current_scroll = float(sb.value())
        if not self._scroll_timer.isActive():
            self._scroll_timer.start()
    def _scroll_step(self):
        diff = self._target_scroll - self._current_scroll
        if abs(diff) < _SETTLE_PX:
            self._current_scroll = self._target_scroll
            sb = self._list.verticalScrollBar()
            if sb:
                sb.setValue(int(self._target_scroll))
            self._scroll_timer.stop()
            return
        t = _EASE_FAST if abs(diff) > 60 else _EASE_SLOW
        self._current_scroll += diff * t
        sb = self._list.verticalScrollBar()
        if sb:
            sb.setValue(int(self._current_scroll))