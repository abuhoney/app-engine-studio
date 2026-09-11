#!/usr/bin/env python3
"""Generate debug.keystore for offline APK signing."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KS_DIR = HERE.parent / "keystore"
KS_PATH = KS_DIR / "debug.keystore"

STOREPASS = "android"
ALIAS = "androiddebugkey"
DNAME = "CN=Android Debug,O=Android,C=US"

def find_keytool():
    for c in ("/usr/bin/keytool",
              "/home/z/my-project/bardom-builder/jdk/bin/keytool",
              str(Path.home() / ".sdkman/candidates/java/current/bin/keytool")):
        if Path(c).exists():
            return c
    return None

def main():
    KS_DIR.mkdir(parents=True, exist_ok=True)
    if KS_PATH.exists():
        print(f"[keystore] already exists at {KS_PATH}")
        return 0

    keytool = find_keytool()
    if not keytool:
        print("[keystore] keytool not found", file=sys.stderr)
        return 1

    cmd = [
        keytool,
        "-genkeypair",
        "-keystore", str(KS_PATH),
        "-storepass", STOREPASS,
        "-alias", ALIAS,
        "-keypass", STOREPASS,
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-dname", DNAME,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[keystore] keytool failed: {r.stderr}", file=sys.stderr)
        return 1
    print(f"[keystore] created at {KS_PATH}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
