#!/usr/bin/env python3
"""
fetch_gradle_wrapper.py — Cache gradle-wrapper.jar for offline builds.

Tries multiple sources:
  1. Existing gradle-wrapper.jar in the repo's android-project/
  2. The system gradle (gradle wrapper)
  3. Direct download from gradle.org
"""
import os
import sys
import shutil
import subprocess
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER_ROOT = HERE.parent
WRAPPER_DIR = BUILDER_ROOT / "gradle" / "wrapper"
WRAPPER_JAR = WRAPPER_DIR / "gradle-wrapper.jar"

REPO_ROOT = BUILDER_ROOT.parent
EXISTING_WRAPPER = REPO_ROOT / "android-project" / "gradle" / "wrapper" / "gradle-wrapper.jar"

URL = "https://raw.githubusercontent.com/gradle/gradle/v8.4.0/gradle/wrapper/gradle-wrapper.jar"

def main():
    WRAPPER_DIR.mkdir(parents=True, exist_ok=True)

    if WRAPPER_JAR.exists() and WRAPPER_JAR.stat().st_size > 1000:
        print(f"[fetch_gradle_wrapper] already cached ({WRAPPER_JAR.stat().st_size} bytes)")
        return 0

    # 1. Copy from existing android-project/
    if EXISTING_WRAPPER.exists() and EXISTING_WRAPPER.stat().st_size > 1000:
        shutil.copy2(EXISTING_WRAPPER, WRAPPER_JAR)
        print(f"[fetch_gradle_wrapper] copied from {EXISTING_WRAPPER}")
        return 0

    # 2. Use system gradle to generate one
    sys_gradle = shutil.which("gradle")
    if sys_gradle:
        tmp = BUILDER_ROOT / "tmp_gradle_init"
        tmp.mkdir(exist_ok=True)
        try:
            subprocess.run([sys_gradle, "wrapper", "--gradle-version", "8.4"],
                           cwd=str(tmp), check=True, capture_output=True, timeout=120)
            src = tmp / "gradle" / "wrapper" / "gradle-wrapper.jar"
            if src.exists() and src.stat().st_size > 1000:
                shutil.copy2(src, WRAPPER_JAR)
                shutil.rmtree(tmp, ignore_errors=True)
                print(f"[fetch_gradle_wrapper] generated via system gradle")
                return 0
        except Exception as e:
            print(f"[fetch_gradle_wrapper] system gradle failed: {e}")
        shutil.rmtree(tmp, ignore_errors=True)

    # 3. Direct download
    print(f"[fetch_gradle_wrapper] downloading from {URL}")
    try:
        urllib.request.urlretrieve(URL, WRAPPER_JAR)
        print(f"[fetch_gradle_wrapper] downloaded ({WRAPPER_JAR.stat().st_size} bytes)")
        return 0
    except Exception as e:
        print(f"[fetch_gradle_wrapper] download failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
