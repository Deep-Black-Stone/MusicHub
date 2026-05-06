import re
import os
import hashlib
import urllib.request
import urllib.parse
import json
from PyQt6.QtCore import *
_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".musichub_lyrics_cache")
class LrcLine:
    def __init__(self, time_ms, text):
        self.time_ms = time_ms
        self.text = text
def _cache_key(artist: str, title: str) -> str:
    raw = f"{artist.lower().strip()}|{title.lower().strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()
def _cache_path(key: str) -> str:
    return os.path.join(_CACHE_DIR, f"{key}.json")
def _ensure_cache_dir():
    os.makedirs(_CACHE_DIR, exist_ok=True)
def _load_from_cache(key: str):
    path = _cache_path(key)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        src = data.get("source", "cache")
        lines = [LrcLine(item["t"], item["x"]) for item in data.get("lines", [])]
        if lines:
            return lines, src
    except Exception:
        pass
    return None, None
def _save_to_cache(key: str, lines: list, source: str):
    _ensure_cache_dir()
    path = _cache_path(key)
    try:
        data = {
            "source": source,
            "lines": [{"t": ln.time_ms, "x": ln.text} for ln in lines],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        pass
def parse_lrc(content):
    lines = []
    pattern = re.compile(r'\[(\d+):(\d+)(?:[.:](\d+))?\](.*)')
    for raw in content.splitlines():
        m = pattern.match(raw.strip())
        if m:
            mins = int(m.group(1))
            secs = int(m.group(2))
            cs = int(m.group(3)) if m.group(3) else 0
            ms = (mins * 60 + secs) * 1000 + cs * 10
            text = m.group(4).strip()
            if text:
                lines.append(LrcLine(ms, text))
    lines.sort(key=lambda x: x.time_ms)
    return lines
def fetch_lyrics_lrclib(artist, title):
    try:
        q = urllib.parse.urlencode({'artist_name': artist, 'track_name': title})
        url = f'https://lrclib.net/api/get?{q}'
        req = urllib.request.Request(url, headers={'User-Agent': 'MusicHub/1.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        synced = data.get('syncedLyrics') or ''
        plain = data.get('plainLyrics') or ''
        if synced:
            return parse_lrc(synced), 'synced'
        if plain:
            lines = [LrcLine(i * 4000, l) for i, l in enumerate(plain.splitlines()) if l.strip()]
            return lines, 'plain'
    except Exception:
        pass
    return [], 'none'
def fetch_lyrics_ovh(artist, title):
    try:
        a = urllib.parse.quote(artist)
        t = urllib.parse.quote(title)
        url = f'https://api.lyrics.ovh/v1/{a}/{t}'
        req = urllib.request.Request(url, headers={'User-Agent': 'MusicHub/1.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        plain = data.get('lyrics') or ''
        if plain:
            lines = [LrcLine(i * 4000, l) for i, l in enumerate(plain.splitlines()) if l.strip()]
            return lines, 'plain'
    except Exception:
        pass
    return [], 'none'
def find_lrc_file(audio_path):
    base = os.path.splitext(audio_path)[0]
    candidate = base + '.lrc'
    if os.path.isfile(candidate):
        return candidate
    return None
def load_lrc_file(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return parse_lrc(f.read())
    except Exception:
        return []
class LyricsWorker(QThread):
    done = pyqtSignal(list, str)
    def __init__(self, artist, title, audio_path, parent=None):
        super().__init__(parent)
        self.artist = artist
        self.title = title
        self.audio_path = audio_path
    def run(self):
        lrc_path = find_lrc_file(self.audio_path)
        if lrc_path:
            lines = load_lrc_file(lrc_path)
            if lines:
                self.done.emit(lines, 'lrc_file')
                return
        key = _cache_key(self.artist, self.title)
        cached_lines, cached_src = _load_from_cache(key)
        if cached_lines:
            self.done.emit(cached_lines, cached_src)
            return
        lines, src = fetch_lyrics_lrclib(self.artist, self.title)
        if lines:
            _save_to_cache(key, lines, src)
            self.done.emit(lines, src)
            return
        lines, src = fetch_lyrics_ovh(self.artist, self.title)
        if lines:
            _save_to_cache(key, lines, src)
            self.done.emit(lines, src)
            return
        self.done.emit([], 'none')