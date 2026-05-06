import os
import sys


def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    return os.path.join(base, relative_path)


def get_icon_path() -> str:
    return resource_path(os.path.join("assets", "MusicHub.ico"))


def get_logo_path() -> str:
    return resource_path(os.path.join("assets", "MusicHub.png"))
