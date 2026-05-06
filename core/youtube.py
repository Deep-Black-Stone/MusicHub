from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtNetwork import *
import json
import os
try:
    import yt_dlp
    YTDLP_OK = True
except ImportError:
    YTDLP_OK = False
TRENDING_QUERIES = [
    "trending music 2024",
    "top hits playlist",
    "new music releases",
    "popular songs",
    "viral music",
]
_COOKIES_FILE = os.path.join(os.path.expanduser("~"), ".musichub_yt_cookies.txt")
def _base_opts(extra=None):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["web", "android"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }
    if os.path.isfile(_COOKIES_FILE):
        opts["cookiefile"] = _COOKIES_FILE
    if extra:
        opts.update(extra)
    return opts
class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)
    def __init__(self, query: str, max_results: int = 12, parent=None):
        super().__init__(parent)
        self.query = query
        self.max_results = max_results
    def run(self):
        if not YTDLP_OK:
            self.error.emit("yt-dlp not installed")
            return
        try:
            opts = _base_opts({"extract_flat": True, "skip_download": True})
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch{self.max_results}:{self.query}", download=False)
            entries = info.get("entries", []) if info else []
            results = []
            for e in entries:
                if not e:
                    continue
                vid_id = e.get("id", "")
                results.append({
                    "id": vid_id,
                    "title": e.get("title", "Unknown"),
                    "channel": e.get("uploader") or e.get("channel") or "Unknown",
                    "duration": e.get("duration", 0) or 0,
                    "url": e.get("url") or f"https://www.youtube.com/watch?v={vid_id}",
                    "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg",
                    "view_count": e.get("view_count", 0) or 0,
                })
            self.results_ready.emit(results)
        except Exception as ex:
            self.error.emit(str(ex))
class TrendingWorker(QThread):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
    def run(self):
        if not YTDLP_OK:
            self.error.emit("yt-dlp not installed")
            return
        try:
            opts = _base_opts({"extract_flat": True, "skip_download": True, "playlistend": 10})
            all_results = []
            queries = ["top music hits 2025", "trending songs right now"]
            for q in queries:
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(f"ytsearch8:{q}", download=False)
                    entries = info.get("entries", []) if info else []
                    for e in entries:
                        if not e:
                            continue
                        vid_id = e.get("id", "")
                        all_results.append({
                            "id": vid_id,
                            "title": e.get("title", "Unknown"),
                            "channel": e.get("uploader") or e.get("channel") or "Unknown",
                            "duration": e.get("duration", 0) or 0,
                            "url": e.get("url") or f"https://www.youtube.com/watch?v={vid_id}",
                            "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/mqdefault.jpg",
                            "view_count": e.get("view_count", 0) or 0,
                        })
                except Exception:
                    pass
            seen = set()
            unique = []
            for r in all_results:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    unique.append(r)
            self.results_ready.emit(unique[:12])
        except Exception as ex:
            self.error.emit(str(ex))
class StreamUrlWorker(QThread):
    url_ready = pyqtSignal(str, str, dict)
    error = pyqtSignal(str)
    def __init__(self, video_url: str, mode: str = "audio", parent=None):
        super().__init__(parent)
        self.video_url = video_url
        self.mode = mode
    def run(self):
        if not YTDLP_OK:
            self.error.emit("yt-dlp not installed")
            return
        try:
            if self.mode == "audio":
                fmt = "bestaudio[ext=m4a]/bestaudio/best"
            else:
                fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best"
            opts = _base_opts({"format": fmt})
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.video_url, download=False)
            if self.mode == "audio":
                stream_url = info.get("url", "")
            else:
                fmts = info.get("formats", [])
                stream_url = info.get("url", "")
                for f in reversed(fmts):
                    if f.get("vcodec") != "none" and f.get("acodec") != "none":
                        stream_url = f.get("url", stream_url)
                        break
            meta = {
                "title": info.get("title", "Unknown"),
                "channel": info.get("uploader") or info.get("channel") or "Unknown",
                "duration": info.get("duration", 0) or 0,
                "thumbnail": info.get("thumbnail", ""),
            }
            self.url_ready.emit(stream_url, self.mode, meta)
        except Exception as ex:
            self.error.emit(str(ex))
class ThumbnailLoader(QThread):
    loaded = pyqtSignal(str, QPixmap)
    def __init__(self, video_id: str, url: str, parent=None):
        super().__init__(parent)
        self.video_id = video_id
        self.url = url
    def run(self):
        try:
            import urllib.request
            data = urllib.request.urlopen(self.url, timeout=8).read()
            pm = QPixmap()
            pm.loadFromData(data)
            if not pm.isNull():
                self.loaded.emit(self.video_id, pm)
        except Exception:
            pass
class CookieImportWorker(QThread):
    done = pyqtSignal(bool, str)
    def __init__(self, browser: str, parent=None):
        super().__init__(parent)
        self.browser = browser
    def run(self):
        if not YTDLP_OK:
            self.done.emit(False, "yt-dlp not installed")
            return
        try:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "cookiesfrombrowser": (self.browser,),
                "cookiefile": _COOKIES_FILE,
                "skip_download": True,
                "extract_flat": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
            if os.path.isfile(_COOKIES_FILE):
                self.done.emit(True, f"Cookies saved from {self.browser}")
            else:
                self.done.emit(False, "Cookie file not created")
        except Exception as ex:
            self.done.emit(False, str(ex))
def fmt_views(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M views"
    if n >= 1_000:
        return f"{n//1_000}K views"
    return f"{n} views"
def fmt_dur(secs: int) -> str:
    secs = int(max(0, secs))
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
def cookies_exist() -> bool:
    return os.path.isfile(_COOKIES_FILE)
def clear_cookies():
    try:
        os.remove(_COOKIES_FILE)
    except Exception:
        pass