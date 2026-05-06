import os
from PyQt6.QtCore import *
try:
    import yt_dlp
    YTDLP_OK = True
except ImportError:
    YTDLP_OK = False
QUALITY_OPTIONS = {"MP3": ["128", "192", "256"], "MP4": ["480p", "720p", "1080p", "best"]}
class PlaylistProbeWorker(QThread):
    entry_found = pyqtSignal(dict)
    probe_done = pyqtSignal(list, str)
    error = pyqtSignal(str)
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self._abort = False
    def abort(self):
        self._abort = True
    def run(self):
        if not YTDLP_OK:
            self.error.emit("yt-dlp not installed. Run: pip install yt-dlp")
            return
        try:
            opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            if self._abort:
                return
            is_playlist = info.get("_type") == "playlist"
            playlist_title = info.get("title", "Playlist") if is_playlist else ""
            entries = info.get("entries", []) if is_playlist else [info]
            results = []
            for e in entries:
                if self._abort:
                    return
                if not e:
                    continue
                vid_id = e.get("id", "")
                dur = e.get("duration", 0) or 0
                m, s = divmod(int(dur), 60)
                item = {
                    "id": vid_id,
                    "title": e.get("title") or e.get("url", "Unknown"),
                    "channel": e.get("uploader") or e.get("channel") or "",
                    "duration": f"{m}:{s:02d}" if dur else "—",
                    "url": e.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else self.url),
                    "thumbnail": f"https://i.ytimg.com/vi/{vid_id}/default.jpg" if vid_id else "",
                    "is_playlist": is_playlist,
                }
                results.append(item)
                self.entry_found.emit(item)
            self.probe_done.emit(results, playlist_title)
        except Exception as ex:
            self.error.emit(str(ex))
class DownloadWorker(QThread):
    progress = pyqtSignal(float, str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str, str, str)
    error = pyqtSignal(str)
    def __init__(self, url: str, fmt: str, quality: str, save_path: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.fmt = fmt
        self.quality = quality
        self.save_path = save_path
    def run(self):
        if not YTDLP_OK:
            self.error.emit("yt-dlp not installed. Run: pip install yt-dlp")
            return
        def hook(d):
            if d["status"] == "downloading":
                dl = d.get("downloaded_bytes", 0)
                tot = d.get("total_bytes") or d.get("total_bytes_estimate", 1) or 1
                pct = min(dl / tot * 100, 99)
                self.progress.emit(pct, f"Downloading…  {pct:.1f}%  |  {d.get('_speed_str', '--')}  |  ETA {d.get('_eta_str', '--')}")
            elif d["status"] == "finished":
                self.progress.emit(99, "Converting…" if self.fmt == "MP3" else "Merging streams…")
        try:
            probe_opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
            with yt_dlp.YoutubeDL(probe_opts) as probe:
                info = probe.extract_info(self.url, download=False)
            is_playlist = info.get("_type") == "playlist"
            if is_playlist:
                pname = info.get("title", "Playlist")
                safe = "".join(c for c in pname if c not in r'\/:*?"<>|')
                out_dir = os.path.join(self.save_path, safe)
                os.makedirs(out_dir, exist_ok=True)
                output = os.path.join(out_dir, "%(title)s.%(ext)s")
                count = len(info.get("entries", []))
                self.log_line.emit(f"[📂]  Playlist: {pname}  ({count} tracks)")
                self.log_line.emit(f"[Folder]  {out_dir}")
                title = pname
            else:
                output = os.path.join(self.save_path, "%(title)s.%(ext)s")
                title = info.get("title", "Unknown")
                dur = info.get("duration", 0) or 0
                mv, sv = divmod(int(dur), 60)
                el = "MP3" if self.fmt == "MP3" else "MP4"
                ql = f"{self.quality} kbps" if self.fmt == "MP3" else self.quality
                self.log_line.emit(f"[{'🎵' if self.fmt == 'MP3' else '🎬'}]  {title}")
                self.log_line.emit(f"[Info]  {mv}:{sv:02d}  |  {el}  |  {ql}")
            if self.fmt == "MP3":
                opts = {
                    "format": "bestaudio/best",
                    "outtmpl": output,
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": self.quality}],
                    "progress_hooks": [hook],
                    "quiet": True,
                    "no_warnings": True,
                }
            else:
                if self.quality == "best":
                    fmt_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else:
                    h = self.quality.replace("p", "")
                    fmt_str = (f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
                               f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]/best")
                opts = {
                    "format": fmt_str,
                    "outtmpl": output,
                    "merge_output_format": "mp4",
                    "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
                    "progress_hooks": [hook],
                    "quiet": True,
                    "no_warnings": True,
                }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            self.finished.emit(title, self.fmt, self.quality)
        except Exception as e:
            self.error.emit(str(e))
class SingleDownloadWorker(QThread):
    progress = pyqtSignal(float, str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str, str, str)
    error = pyqtSignal(str)
    def __init__(self, url: str, title: str, fmt: str, quality: str, save_path: str, parent=None):
        super().__init__(parent)
        self.url = url
        self._title = title
        self.fmt = fmt
        self.quality = quality
        self.save_path = save_path
        self._abort = False
    def abort(self):
        self._abort = True
    def run(self):
        if not YTDLP_OK:
            self.error.emit("yt-dlp not installed.")
            return
        def hook(d):
            if self._abort:
                raise Exception("Aborted")
            if d["status"] == "downloading":
                dl = d.get("downloaded_bytes", 0)
                tot = d.get("total_bytes") or d.get("total_bytes_estimate", 1) or 1
                pct = min(dl / tot * 100, 99)
                self.progress.emit(pct, f"{pct:.1f}%  |  {d.get('_speed_str', '--')}  |  ETA {d.get('_eta_str', '--')}")
            elif d["status"] == "finished":
                self.progress.emit(99, "Converting…" if self.fmt == "MP3" else "Merging…")
        try:
            output = os.path.join(self.save_path, "%(title)s.%(ext)s")
            if self.fmt == "MP3":
                opts = {
                    "format": "bestaudio/best",
                    "outtmpl": output,
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": self.quality}],
                    "progress_hooks": [hook],
                    "quiet": True,
                    "no_warnings": True,
                }
            else:
                if self.quality == "best":
                    fmt_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else:
                    h = self.quality.replace("p", "")
                    fmt_str = (f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
                               f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]/best")
                opts = {
                    "format": fmt_str,
                    "outtmpl": output,
                    "merge_output_format": "mp4",
                    "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
                    "progress_hooks": [hook],
                    "quiet": True,
                    "no_warnings": True,
                }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            self.finished.emit(self._title, self.fmt, self.quality)
        except Exception as e:
            if not self._abort:
                self.error.emit(str(e))
class DownloadQueue(QObject):
    queue_updated = pyqtSignal()
    item_started = pyqtSignal(int)
    item_progress = pyqtSignal(int, float, str)
    item_finished = pyqtSignal(int, str)
    item_error = pyqtSignal(int, str)
    all_done = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = []
        self._current_idx = -1
        self._worker = None
        self._running = False
        self._fmt = "MP4"
        self._quality = "720p"
        self._save_path = ""
    def set_options(self, fmt: str, quality: str, save_path: str):
        self._fmt = fmt
        self._quality = quality
        self._save_path = save_path
    def add_items(self, items: list):
        for item in items:
            entry = dict(item)
            entry["status"] = "queued"
            entry["progress"] = 0.0
            entry["msg"] = ""
            self._queue.append(entry)
        self.queue_updated.emit()
    def clear(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(1000)
        self._queue.clear()
        self._current_idx = -1
        self._running = False
        self._worker = None
        self.queue_updated.emit()
    def start(self):
        if self._running:
            return
        self._running = True
        self._next()
    def stop(self):
        self._running = False
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(1000)
        for i, entry in enumerate(self._queue):
            if entry["status"] == "downloading":
                entry["status"] = "queued"
                entry["progress"] = 0.0
        self.queue_updated.emit()
    def get_queue(self):
        return list(self._queue)
    def _next(self):
        if not self._running:
            return
        next_idx = None
        for i, entry in enumerate(self._queue):
            if entry["status"] == "queued":
                next_idx = i
                break
        if next_idx is None:
            self._running = False
            self.all_done.emit()
            return
        self._current_idx = next_idx
        entry = self._queue[next_idx]
        entry["status"] = "downloading"
        self.item_started.emit(next_idx)
        self.queue_updated.emit()
        self._worker = SingleDownloadWorker(
            entry["url"], entry["title"], self._fmt, self._quality, self._save_path
        )
        self._worker.progress.connect(lambda p, m, idx=next_idx: self._on_progress(idx, p, m))
        self._worker.finished.connect(lambda t, f, q, idx=next_idx: self._on_finished(idx, t))
        self._worker.error.connect(lambda e, idx=next_idx: self._on_error(idx, e))
        self._worker.start()
    def _on_progress(self, idx, pct, msg):
        if 0 <= idx < len(self._queue):
            self._queue[idx]["progress"] = pct
            self._queue[idx]["msg"] = msg
        self.item_progress.emit(idx, pct, msg)
    def _on_finished(self, idx, title):
        if 0 <= idx < len(self._queue):
            self._queue[idx]["status"] = "done"
            self._queue[idx]["progress"] = 100.0
        self.item_finished.emit(idx, title)
        self.queue_updated.emit()
        QTimer.singleShot(0, self._next)
    def _on_error(self, idx, err):
        if 0 <= idx < len(self._queue):
            self._queue[idx]["status"] = "error"
            self._queue[idx]["msg"] = err
        self.item_error.emit(idx, err)
        self.queue_updated.emit()
        QTimer.singleShot(0, self._next)
    def is_running(self):
        return self._running
    def counts(self):
        done = sum(1 for e in self._queue if e["status"] == "done")
        error = sum(1 for e in self._queue if e["status"] == "error")
        total = len(self._queue)
        return done, error, total