from PyQt6.QtCore import QObject, QFileSystemWatcher, pyqtSignal, QTimer
import os
from utils.media import AUDIO_EXTS, VIDEO_EXTS
class MediaFolderWatcher(QObject):
    files_added = pyqtSignal(list)
    files_removed = pyqtSignal(list)
    files_renamed = pyqtSignal(list, list)
    def __init__(self, media_type: str, parent=None):
        super().__init__(parent)
        self._media_type = media_type
        self._exts = AUDIO_EXTS if media_type == "audio" else VIDEO_EXTS
        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._on_dir_changed)
        self._folder_snapshots = {}
        self._pending_dirs = set()
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._process_pending)
    def watch_folder(self, folder: str):
        if not os.path.isdir(folder):
            return
        self._watcher.addPath(folder)
        for root, dirs, _ in os.walk(folder):
            for d in dirs:
                sub = os.path.join(root, d)
                self._watcher.addPath(sub)
        self._folder_snapshots[folder] = self._snapshot(folder)
    def unwatch_folder(self, folder: str):
        paths = [p for p in self._watcher.directories() if p == folder or p.startswith(folder + os.sep)]
        if paths:
            self._watcher.removePaths(paths)
        self._folder_snapshots.pop(folder, None)
        self._pending_dirs.discard(folder)
    def unwatch_all(self):
        dirs = self._watcher.directories()
        if dirs:
            self._watcher.removePaths(dirs)
        self._folder_snapshots.clear()
        self._pending_dirs.clear()
    def _snapshot(self, folder: str) -> dict:
        result = {}
        try:
            for root, dirs, files in os.walk(folder):
                dirs.sort()
                for fn in sorted(files):
                    if os.path.splitext(fn)[1].lower() in self._exts:
                        fp = os.path.join(root, fn)
                        try:
                            result[fp] = os.path.getmtime(fp)
                        except OSError:
                            pass
        except Exception:
            pass
        return result
    def _root_folder(self, changed_dir: str) -> str:
        for folder in self._folder_snapshots:
            if changed_dir == folder or changed_dir.startswith(folder + os.sep):
                return folder
        return ""
    def _on_dir_changed(self, path: str):
        root = self._root_folder(path)
        if root:
            self._pending_dirs.add(root)
            new_subdirs = set()
            try:
                for r, dirs, _ in os.walk(path):
                    for d in dirs:
                        sub = os.path.join(r, d)
                        if sub not in self._watcher.directories():
                            new_subdirs.add(sub)
            except Exception:
                pass
            if new_subdirs:
                self._watcher.addPaths(list(new_subdirs))
            if not self._debounce.isActive():
                self._debounce.start()
    def _process_pending(self):
        for folder in list(self._pending_dirs):
            self._pending_dirs.discard(folder)
            old = self._folder_snapshots.get(folder, {})
            new = self._snapshot(folder)
            old_set = set(old.keys())
            new_set = set(new.keys())
            added = sorted(new_set - old_set)
            removed = sorted(old_set - new_set)
            if added and removed:
                matched_add, matched_rem = [], []
                for a in list(added):
                    a_name = os.path.basename(a)
                    for r in list(removed):
                        r_name = os.path.basename(r)
                        if (os.path.dirname(a) == os.path.dirname(r) and
                                os.path.splitext(a_name)[1] == os.path.splitext(r_name)[1] and
                                abs(new.get(a, 0) - old.get(r, 0)) < 5):
                            matched_add.append(a)
                            matched_rem.append(r)
                            added.remove(a)
                            removed.remove(r)
                            break
                if matched_add:
                    self.files_renamed.emit(matched_rem, matched_add)
            if added:
                self.files_added.emit(added)
            if removed:
                self.files_removed.emit(removed)
            self._folder_snapshots[folder] = new