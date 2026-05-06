import os
import subprocess
from PyQt6.QtGui import *
from PyQt6.QtCore import *
try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3
    MUTAGEN_OK = True
except ImportError:
    MUTAGEN_OK = False
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".ape", ".alac"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".ts", ".vob"}
def get_album_art(filepath: str):
    if not MUTAGEN_OK:
        return None
    try:
        tags = ID3(filepath)
        for key in tags.keys():
            if key.startswith("APIC"):
                apic = tags[key]
                img = QImage()
                img.loadFromData(apic.data)
                return QPixmap.fromImage(img)
    except Exception:
        pass
    try:
        audio = MutagenFile(filepath)
        if audio and hasattr(audio, "pictures") and audio.pictures:
            p = audio.pictures[0]
            img = QImage()
            img.loadFromData(p.data)
            return QPixmap.fromImage(img)
    except Exception:
        pass
    return None
def get_audio_duration(filepath: str) -> float:
    if MUTAGEN_OK:
        try:
            audio = MutagenFile(filepath)
            if audio and audio.info:
                return float(audio.info.length)
        except Exception:
            pass
    return 0.0
def get_audio_tags(filepath: str) -> dict:
    result = {"title": "", "artist": "", "album": ""}
    if not MUTAGEN_OK:
        return result
    try:
        audio = MutagenFile(filepath)
        if audio and audio.tags:
            def tag(k): return str(audio.tags[k][0]) if k in audio.tags else ""
            result["artist"] = tag("TPE1") or tag("artist") or tag("©ART") or ""
            result["title"] = tag("TIT2") or tag("title") or tag("©nam") or ""
            result["album"] = tag("TALB") or tag("album") or tag("©alb") or ""
    except Exception:
        pass
    return result
def get_video_thumbnail(filepath: str):
    try:
        import tempfile
        tmp = tempfile.mktemp(suffix=".jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "3", "-i", filepath, "-frames:v", "1", "-q:v", "2", tmp],
            capture_output=True, timeout=8
        )
        if os.path.exists(tmp):
            pm = QPixmap(tmp)
            os.remove(tmp)
            if not pm.isNull():
                return pm
    except Exception:
        pass
    return None
def get_video_info(filepath: str) -> dict:
    result = {"duration": "—", "width": "—", "height": "—"}
    try:
        import json
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", filepath],
            capture_output=True, text=True, timeout=8
        )
        data = json.loads(r.stdout)
        fmt = data.get("format", {})
        dur = float(fmt.get("duration", 0) or 0)
        mv, sv = divmod(int(dur), 60)
        result["duration"] = f"{mv}:{sv:02d}"
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                result["width"] = str(stream.get("width", "—"))
                result["height"] = str(stream.get("height", "—"))
                break
    except Exception:
        pass
    return result
def scan_folder_recursive(folder: str, exts: set) -> list:
    found = []
    try:
        for root, dirs, files in os.walk(folder):
            dirs.sort()
            for fn in sorted(files):
                if os.path.splitext(fn)[1].lower() in exts:
                    found.append(os.path.join(root, fn))
    except Exception:
        pass
    return found
def fmt_time(secs: float) -> str:
    secs = int(max(0, secs))
    m, s = divmod(secs, 60)
    return f"{m}:{s:02d}"
