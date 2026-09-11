#!/usr/bin/env python3
"""
fetch_platform_34.py — Cache android.jar (platform 34) for offline builds.
"""
import os
import sys
import shutil
import urllib.request
import zipfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER_ROOT = HERE.parent
PLAT_DIR = BUILDER_ROOT / "sdk" / "platforms" / "android-34"

URL = "https://dl.google.com/android/repository/platform-34-ext9_r01.zip"

def find_system_jar():
    candidates = [
        os.environ.get("ANDROID_HOME", ""),
        os.environ.get("ANDROID_SDK_ROOT", ""),
        "/opt/android-sdk",
        "/usr/lib/android-sdk",
        os.path.expanduser("~/Android/Sdk"),
    ]
    for c in candidates:
        if not c: continue
        base = Path(c) / "platforms"
        if not base.exists(): continue
        # android-34 preferred
        for name in ("android-34", "android-33", "android-32"):
            p = base / name / "android.jar"
            if p.exists():
                return p.parent
    return None

def main():
    PLAT_DIR.mkdir(parents=True, exist_ok=True)

    if (PLAT_DIR / "android.jar").exists():
        print(f"[fetch_platform_34] already cached at {PLAT_DIR}")
        return 0

    sys_plat = find_system_jar()
    if sys_plat:
        print(f"[fetch_platform_34] using system platform at {sys_plat}")
        for f in sys_plat.iterdir():
            dst = PLAT_DIR / f.name
            if not dst.exists():
                if f.is_dir():
                    shutil.copytree(f, dst)
                else:
                    shutil.copy2(f, dst)
        return 0

    print(f"[fetch_platform_34] downloading from {URL}")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        urllib.request.urlretrieve(URL, tmp_path)
        with zipfile.ZipFile(tmp_path) as z:
            z.extractall(PLAT_DIR.parent)
        # Rename extracted dir if needed
        for d in PLAT_DIR.parent.iterdir():
            if d.is_dir() and d.name != "android-34":
                if (d / "android.jar").exists():
                    if PLAT_DIR.exists():
                        shutil.rmtree(PLAT_DIR)
                    d.rename(PLAT_DIR)
                    break
        if (PLAT_DIR / "android.jar").exists():
            print(f"[fetch_platform_34] done — android.jar at {PLAT_DIR}")
            return 0
        print(f"[fetch_platform_34] extraction incomplete", file=sys.stderr)
        return 1
    finally:
        tmp_path.unlink(missing_ok=True)

if __name__ == "__main__":
    sys.exit(main())
