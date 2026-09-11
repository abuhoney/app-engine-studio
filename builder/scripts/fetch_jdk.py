#!/usr/bin/env python3
"""
fetch_jdk.py — Download & cache Temurin JDK 17 for offline builds.

Caches to: Bardom-builder/jdk/
Sets up:   Bardom-builder/jdk/bin/{javac,java,jar,keytool}

If a system JDK 17 is already available, symlinks to it instead of downloading.
"""
import os
import sys
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILDER_ROOT = HERE.parent
JDK_ROOT = BUILDER_ROOT / "jdk"

URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.9%2B9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.9_9.tar.gz"

def system_javac():
    """Return path to system javac if it's version 17+."""
    for cand in ("/usr/bin/javac", "/usr/lib/jvm/java-17-openjdk-amd64/bin/javac"):
        if Path(cand).exists():
            try:
                r = subprocess.run([cand, "-version"], capture_output=True, text=True, timeout=5)
                # stderr format: javac 17.0.9
                first = (r.stderr or r.stdout).strip().splitlines()[0]
                ver = first.split()[1] if len(first.split()) > 1 else ""
                if ver.startswith("17."):
                    return cand
            except Exception:
                pass
    return None

def main():
    JDK_ROOT.mkdir(parents=True, exist_ok=True)
    bin_dir = JDK_ROOT / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    # Already cached?
    if (bin_dir / "javac").exists() and (bin_dir / "java").exists():
        print(f"[fetch_jdk] already cached at {JDK_ROOT}")
        return 0

    # Try system JDK first
    sys_javac = system_javac()
    if sys_javac:
        sys_bin = Path(sys_javac).parent
        print(f"[fetch_jdk] using system JDK at {sys_bin}")
        for tool in ("javac", "java", "jar", "keytool"):
            src = sys_bin / tool
            dst = bin_dir / tool
            if src.exists():
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                dst.symlink_to(src)
                if tool in ("javac", "java", "jar", "keytool"):
                    dst.chmod(0o755)
        return 0

    # Download Temurin
    print(f"[fetch_jdk] downloading from {URL}")
    tgz_path = JDK_ROOT / "jdk.tar.gz"
    try:
        urllib.request.urlretrieve(URL, tgz_path)
    except Exception as e:
        print(f"[fetch_jdk] download failed: {e}", file=sys.stderr)
        return 1

    print(f"[fetch_jdk] extracting...")
    with tarfile.open(tgz_path) as t:
        t.extractall(JDK_ROOT)

    # Find extracted dir (jdk-17.0.9+9)
    extracted = [d for d in JDK_ROOT.iterdir() if d.is_dir() and d.name.startswith("jdk-")]
    if not extracted:
        print(f"[fetch_jdk] no extracted dir found", file=sys.stderr)
        return 1
    real_jdk = extracted[0]
    real_bin = real_jdk / "bin"

    # Symlink tools into our bin/
    for tool in ("javac", "java", "jar", "keytool"):
        src = real_bin / tool
        dst = bin_dir / tool
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(src)
        dst.chmod(0o755)

    tgz_path.unlink()
    print(f"[fetch_jdk] done — tools at {bin_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
