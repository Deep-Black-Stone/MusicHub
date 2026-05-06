import os
from PyQt6.QtCore import QObject, pyqtSignal
from utils.config import load_config, save_config
from utils.media import scan_folder_recursive, AUDIO_EXTS, VIDEO_EXTS
from core.watcher import MediaFolderWatcher
class MediaLibrary(QObject):
    library_changed = pyqtSignal()
    def __init__(self, media_type: str, parent=None):
        super().__init__(parent)
        self._type = media_type
        self._exts = AUDIO_EXTS if media_type == "audio" else VIDEO_EXTS
        self._folders = []
        self._folder_files = {}
        self._all_files = []
        self._watcher = MediaFolderWatcher(media_type, self)
        self._watcher.files_added.connect(self._on_files_added)
        self._watcher.files_removed.connect(self._on_files_removed)
        self._watcher.files_renamed.connect(self._on_files_renamed)
        self._load_folders()
    def _load_folders(self):
        cfg = load_config()
        key = f"{self._type}_folders"
        saved = cfg.get(key, [])
        for f in saved:
            if os.path.isdir(f):
                self._folders.append(f)
    def _save_folders(self):
        save_config({f"{self._type}_folders": self._folders})
    def add_folder(self, folder: str):
        if folder not in self._folders and os.path.isdir(folder):
            self._folders.append(folder)
            self._save_folders()
            self._watcher.watch_folder(folder)
            return True
        return False
    def remove_folder(self, folder: str):
        if folder in self._folders:
            self._folders.remove(folder)
            self._folder_files.pop(folder, None)
            self._rebuild_all()
            self._save_folders()
            self._watcher.unwatch_folder(folder)
    def scan_all(self, callback=None):
        self._folder_files = {}
        for folder in self._folders:
            files = scan_folder_recursive(folder, self._exts)
            self._folder_files[folder] = files
            if callback:
                callback(folder, files)
        self._rebuild_all()
        for folder in self._folders:
            self._watcher.watch_folder(folder)
    def scan_folder(self, folder: str):
        files = scan_folder_recursive(folder, self._exts)
        self._folder_files[folder] = files
        self._rebuild_all()
        self._watcher.watch_folder(folder)
        return files
    def _rebuild_all(self):
        self._all_files = []
        for folder in self._folders:
            self._all_files.extend(self._folder_files.get(folder, []))
    def _find_root_folder(self, filepath: str) -> str:
        for folder in self._folders:
            if filepath.startswith(folder + os.sep) or filepath.startswith(folder + "/"):
                return folder
        return ""
    def _on_files_added(self, paths: list):
        changed = False
        for fp in paths:
            root = self._find_root_folder(fp)
            if root:
                lst = self._folder_files.setdefault(root, [])
                if fp not in lst:
                    lst.append(fp)
                    lst.sort()
                    changed = True
        if changed:
            self._rebuild_all()
            self.library_changed.emit()
    def _on_files_removed(self, paths: list):
        path_set = set(paths)
        changed = False
        for folder in self._folders:
            lst = self._folder_files.get(folder, [])
            new_lst = [f for f in lst if f not in path_set]
            if len(new_lst) != len(lst):
                self._folder_files[folder] = new_lst
                changed = True
        if changed:
            self._rebuild_all()
            self.library_changed.emit()
    def _on_files_renamed(self, old_paths: list, new_paths: list):
        old_set = dict(zip(old_paths, new_paths))
        changed = False
        for folder in self._folders:
            lst = self._folder_files.get(folder, [])
            new_lst = []
            for f in lst:
                if f in old_set:
                    new_lst.append(old_set[f])
                    changed = True
                else:
                    new_lst.append(f)
            new_lst.sort()
            self._folder_files[folder] = new_lst
        if changed:
            self._rebuild_all()
            self.library_changed.emit()
    def get_folders(self) -> list:
        return list(self._folders)
    def get_folder_files(self, folder: str) -> list:
        return list(self._folder_files.get(folder, []))
    def get_all_files(self) -> list:
        return list(self._all_files)
    def get_subfolder_tree(self, folder: str) -> dict:
        tree = {}
        files = self._folder_files.get(folder, [])
        for fp in files:
            rel = os.path.relpath(os.path.dirname(fp), folder)
            if rel not in tree:
                tree[rel] = []
            tree[rel].append(fp)
        return tree
    def clear(self):
        self._watcher.unwatch_all()
        self._folders.clear()
        self._folder_files.clear()
        self._all_files.clear()
        self._save_folders()
    def total_count(self) -> int:
        return len(self._all_files)
    def folder_count(self, folder: str) -> int:
        return len(self._folder_files.get(folder, []))