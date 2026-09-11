#!/usr/bin/env python3
"""
fetch_build_tools.py — Cache Android SDK build-tools 34.0.0 for offline builds.

Caches: aapt2, d8, zipalign, apksigner, aidl → Bardom-builder/sdk/build-tools/34.0.0/
"""
import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER_ROOT = HERE.parent
BT_DIR = BUILDER_ROOT / "sdk" / "build-tools" / "34.0.0"

URL = "https://dl.google.com/android/repository/build-tools_r34-linux.zip"

NEEDED = ["aapt2", "d8", "zipalign", "apksigner", "aidl"]

def find_system_tools():
    """Try to find build-tools from system SDK."""
    candidates = [
        os.environ.get("ANDROID_HOME", ""),
        os.environ.get("ANDROID_SDK_ROOT", ""),
        "/opt/android-sdk",
        "/usr/lib/android-sdk",
        os.path.expanduser("~/Android/Sdk"),
    ]
    for c in candidates:
        if not c: continue
        base = Path(c) / "build-tools"
        if not base.exists(): continue
        for v in sorted(base.iterdir(), reverse=True):
            if all((v / t).exists() for t in NEEDED):
                return v
    return None

def main():
    BT_DIR.mkdir(parents=True, exist_ok=True)

    # Already cached?
    if all((BT_DIR / t).exists() for t in NEEDED):
        print(f"[fetch_build_tools] already cached at {BT_DIR}")
        return 0

    # Try system SDK
    sys_bt = find_system_tools()
    if sys_bt:
        print(f"[fetch_build_tools] using system build-tools at {sys_bt}")
        for t in NEEDED:
            src = sys_bt / t
            dst = BT_DIR / t
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            dst.symlink_to(src)
            dst.chmod(0o755)
        # Also copy auxiliary files needed by apksigner (lib/)
        for aux in ("lib", "NOTICE.txt", "source.properties"):
            src = sys_bt / aux
            if src.exists():
                dst = BT_DIR / aux
                if not dst.exists():
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
        return 0

    # Download
    print(f"[fetch_build_tools] downloading from {URL}")
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        urllib.request.urlretrieve(URL, tmp_path)
        print(f"[fetch_build_tools] extracting...")
        with zipfile.ZipFile(tmp_path) as z:
            z.extractall(BT_DIR.parent)
        # Extracted dir name is usually "android-14" — rename to "34.0.0"
        for d in BT_DIR.parent.iterdir():
            if d.is_dir() and d.name != "34.0.0":
                if (d / "aapt2").exists():
                    if BT_DIR.exists():
                        shutil.rmtree(BT_DIR)
                    d.rename(BT_DIR)
                    break
        # Verify
        for t in NEEDED:
            f = BT_DIR / t
            if f.exists():
                f.chmod(0o755)
        if all((BT_DIR / t).exists() for t in NEEDED):
            print(f"[fetch_build_tools] done — tools at {BT_DIR}")
            return 0
        print(f"[fetch_build_tools] extraction incomplete", file=sys.stderr)
        return 1
    finally:
        tmp_path.unlink(missing_ok=True)

if __name__ == "__main__":
    sys.exit(main())
