from PyQt6.QtCore import *
from utils.media import scan_folder_recursive
class ScanWorker(QThread):
    folder_done = pyqtSignal(str, list)
    scan_complete = pyqtSignal()
    def __init__(self, folders: list, exts: set, parent=None):
        super().__init__(parent)
        self._folders = folders
        self._exts = exts
    def run(self):
        for folder in self._folders:
            files = scan_folder_recursive(folder, self._exts)
            self.folder_done.emit(folder, files)
        self.scan_complete.emit()
