from utils.config import load_config, save_config
class FavoritesManager:
    _instance = None
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = FavoritesManager()
        return cls._instance
    def __init__(self):
        cfg = load_config()
        self._favs = set(cfg.get("favorites", []))
    def is_fav(self, filepath: str) -> bool:
        return filepath in self._favs
    def toggle(self, filepath: str) -> bool:
        if filepath in self._favs:
            self._favs.discard(filepath)
        else:
            self._favs.add(filepath)
        save_config({"favorites": list(self._favs)})
        return filepath in self._favs
    def add(self, filepath: str):
        self._favs.add(filepath)
        save_config({"favorites": list(self._favs)})
    def remove(self, filepath: str):
        self._favs.discard(filepath)
        save_config({"favorites": list(self._favs)})
    def get_all(self) -> list:
        return list(self._favs)
