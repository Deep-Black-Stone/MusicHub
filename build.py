#!/usr/bin/env python3
"""
MusicHub Build Script
Run: python build.py
Output: dist/MusicHub.exe (Windows) or dist/MusicHub (Linux/Mac)
"""
import os
import sys
import shutil
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(ROOT, "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "MusicHub.ico")
ICON_PNG = os.path.join(ASSETS_DIR, "MusicHub.png")
MAIN_PY = os.path.join(ROOT, "main.py")
DIST_DIR = os.path.join(ROOT, "dist")
BUILD_DIR = os.path.join(ROOT, "build")
SPEC_FILE = os.path.join(ROOT, "MusicHub.spec")

APP_NAME = "MusicHub"


def clean():
    for d in (DIST_DIR, BUILD_DIR):
        if os.path.isdir(d):
            shutil.rmtree(d)
    if os.path.isfile(SPEC_FILE):
        os.remove(SPEC_FILE)
    print("[build] Cleaned previous build artefacts.")


def run_pyinstaller():
    sep = ";" if sys.platform == "win32" else ":"

    datas = [
        f"{ASSETS_DIR}{sep}assets",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={APP_NAME}",
        f"--icon={ICON_ICO}",
        f"--add-data={ASSETS_DIR}{sep}assets",
        "--hidden-import=PyQt6.QtMultimedia",
        "--hidden-import=pygame",
        "--hidden-import=mutagen",
        "--hidden-import=yt_dlp",
        "--hidden-import=PIL",
        MAIN_PY,
    ]

    print("[build] Running PyInstaller …")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("[build] PyInstaller FAILED.")
        sys.exit(result.returncode)
    print("[build] Build complete!")
    exe = os.path.join(DIST_DIR, APP_NAME + (".exe" if sys.platform == "win32" else ""))
    if os.path.isfile(exe):
        size_mb = os.path.getsize(exe) / 1024 / 1024
        print(f"[build] Output: {exe}  ({size_mb:.1f} MB)")
    else:
        print(f"[build] Warning: expected output not found at {exe}")


def main():
    print("=" * 56)
    print(f"  MusicHub Build  —  Python {sys.version.split()[0]}")
    print("=" * 56)

    try:
        import PyInstaller
        print(f"[build] PyInstaller {PyInstaller.__version__} found.")
    except ImportError:
        print("[build] PyInstaller not found. Installing …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    clean()
    run_pyinstaller()


if __name__ == "__main__":
    main()
