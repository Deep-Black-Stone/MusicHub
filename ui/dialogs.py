import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from theme.engine import TH, blend_color
from ui.widgets import RoundedCard, GlowButton
from utils.media import get_audio_duration, get_audio_tags, get_video_info, fmt_time
try:
    from mutagen import File as MutagenFile
    MUTAGEN_OK = True
except ImportError:
    MUTAGEN_OK = False
def show_music_info(parent, filepath):
    stat = os.stat(filepath)
    size_mb = stat.st_size / (1024 * 1024)
    name = os.path.basename(filepath)
    ext = os.path.splitext(name)[1].upper().lstrip(".")
    dur = get_audio_duration(filepath)
    m, s = divmod(int(dur), 60)
    tags = get_audio_tags(filepath)
    dlg = QDialog(parent)
    dlg.setWindowTitle("Track Info")
    dlg.setFixedWidth(400)
    dlg.setStyleSheet(f"background: {TH.bg}; color: {TH.text};")
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(10)
    hdr = QLabel("🎵  Track Info")
    hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    hdr.setStyleSheet(f"color: {TH.accent};")
    lay.addWidget(hdr)
    rows = [
        ("File", name), ("Format", ext), ("Duration", f"{m}:{s:02d}"),
        ("Size", f"{size_mb:.2f} MB"), ("Title", tags["title"] or "—"),
        ("Artist", tags["artist"] or "—"), ("Album", tags["album"] or "—"), ("Path", filepath),
    ]
    card = RoundedCard(radius=10)
    grid = QGridLayout(card)
    grid.setContentsMargins(16, 12, 16, 12)
    grid.setSpacing(6)
    for r, (k, v) in enumerate(rows):
        kl = QLabel(k)
        kl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        kl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        vl = QLabel(v)
        vl.setFont(QFont("Segoe UI", 9))
        vl.setStyleSheet(f"color: {TH.text}; background: transparent;")
        vl.setWordWrap(True)
        grid.addWidget(kl, r, 0)
        grid.addWidget(vl, r, 1)
    lay.addWidget(card)
    ok = GlowButton("Close", TH.accent)
    ok.setFixedHeight(40)
    ok.clicked.connect(dlg.accept)
    lay.addWidget(ok)
    dlg.exec()
def show_video_info(parent, filepath):
    stat = os.stat(filepath)
    size_mb = stat.st_size / (1024 * 1024)
    name = os.path.basename(filepath)
    ext = os.path.splitext(name)[1].upper().lstrip(".")
    info = get_video_info(filepath)
    dlg = QDialog(parent)
    dlg.setWindowTitle("Video Info")
    dlg.setFixedWidth(400)
    dlg.setStyleSheet(f"background: {TH.bg}; color: {TH.text};")
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(10)
    hdr = QLabel("🎬  Video Info")
    hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    hdr.setStyleSheet(f"color: {TH.blue};")
    lay.addWidget(hdr)
    rows = [
        ("File", name), ("Format", ext), ("Duration", info["duration"]),
        ("Size", f"{size_mb:.2f} MB"), ("Width", info["width"]),
        ("Height", info["height"]), ("Path", filepath),
    ]
    card = RoundedCard(radius=10)
    grid = QGridLayout(card)
    grid.setContentsMargins(16, 12, 16, 12)
    grid.setSpacing(6)
    for r, (k, v) in enumerate(rows):
        kl = QLabel(k)
        kl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        kl.setStyleSheet(f"color: {TH.text2}; background: transparent;")
        vl = QLabel(v)
        vl.setFont(QFont("Segoe UI", 9))
        vl.setStyleSheet(f"color: {TH.text}; background: transparent;")
        vl.setWordWrap(True)
        grid.addWidget(kl, r, 0)
        grid.addWidget(vl, r, 1)
    lay.addWidget(card)
    ok = GlowButton("Close", TH.blue)
    ok.setFixedHeight(40)
    ok.clicked.connect(dlg.accept)
    lay.addWidget(ok)
    dlg.exec()
def show_shortcuts_dialog(parent):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Keyboard Shortcuts")
    dlg.setFixedWidth(480)
    dlg.setStyleSheet(f"background: {TH.bg}; color: {TH.text};")
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(12)
    hdr = QLabel("⌨  Keyboard Shortcuts")
    hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    hdr.setStyleSheet(f"color: {TH.accent};")
    lay.addWidget(hdr)
    sections = [
        ("Playback", [("Space / K", "Play / Pause"), ("S", "Stop"), ("→", "Seek +5s"), ("←", "Seek -5s"), ("L", "Seek +10s"), ("J", "Seek -10s")]),
        ("Track Navigation", [("Shift+N", "Next track"), ("Shift+P", "Previous track"), ("Ctrl+→", "Next track"), ("Ctrl+←", "Previous track"), ("Ctrl+End", "Last track"), ("Ctrl+Home", "First track")]),
        ("Volume", [("↑", "Volume +5%"), ("↓", "Volume -5%"), ("M", "Mute / Unmute"), ("Ctrl+M", "Global Mute"), ("0–9", "Jump to 0–90%")]),
        ("Video Player", [("F / F11", "Toggle fullscreen"), ("Ctrl+Shift+F", "Fullscreen (global)"), ("T", "Theater mode"), ("I", "Mini player"), ("Shift+.", "Speed up"), ("Shift+,", "Speed down"), ("Escape", "Exit fullscreen")]),
        ("Global Shortcuts", [("Ctrl+O", "Open file/folder"), ("Ctrl+F", "Search"), ("Ctrl+D", "Download"), ("Ctrl+L", "Toggle lyrics"), ("Ctrl+Q", "Quit app")]),
        ("Navigation", [("Ctrl+1", "Home"), ("Ctrl+2", "Download"), ("Ctrl+3", "Music Player"), ("Ctrl+4", "Video Player"), ("Ctrl+5", "Settings")]),
    ]
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"background: {TH.bg}; border: none;")
    scroll.setFixedHeight(380)
    content = QWidget()
    content.setStyleSheet(f"background: {TH.bg};")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(0, 0, 0, 0)
    cl.setSpacing(10)
    for section_name, binds in sections:
        sec_lbl = QLabel(section_name.upper())
        sec_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        sec_lbl.setStyleSheet(f"color: {TH.text3}; letter-spacing: 2px; background: transparent;")
        cl.addWidget(sec_lbl)
        card = RoundedCard(radius=10)
        grid = QGridLayout(card)
        grid.setContentsMargins(16, 10, 16, 10)
        grid.setSpacing(6)
        for r, (key, desc) in enumerate(binds):
            kl = QLabel(key)
            kl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            kl.setStyleSheet(f"color: {TH.accent}; background: {TH.card}; border: 1px solid {TH.border}; border-radius: 4px; padding: 2px 6px;")
            kl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl = QLabel(desc)
            vl.setFont(QFont("Segoe UI", 9))
            vl.setStyleSheet(f"color: {TH.text}; background: transparent;")
            grid.addWidget(kl, r, 0)
            grid.addWidget(vl, r, 1)
        grid.setColumnStretch(1, 1)
        cl.addWidget(card)
    cl.addStretch()
    scroll.setWidget(content)
    lay.addWidget(scroll)
    ok = GlowButton("Close", TH.accent)
    ok.setFixedHeight(40)
    ok.clicked.connect(dlg.accept)
    lay.addWidget(ok)
    dlg.exec()
