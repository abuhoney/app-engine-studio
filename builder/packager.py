#!/usr/bin/env python3
"""
Bardom-builder — packager.py
============================
Final APK packaging: zipalign + apksigner.

Inputs:
  - project_dir  (the workspace project dir)
  - apk_path     (the unsigned APK from compiler.py)
  - target       ("debug" or "release")

Outputs:
  - <project_dir>/app/build/outputs/apk/<target>/<app_name>-<target>.apk
    (aligned + signed)

If the debug keystore is missing, we generate one on the fly via keytool
so the offline build never blocks on a missing keystore.
"""
import json
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
CONFIG_PATH = HERE / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

def resolve(p):
    return (REPO_ROOT / p).resolve()

def run(cmd, cwd=None, env=None, log_fn=None, timeout=300):
    if log_fn:
        log_fn("package", "ok", f"$ {' '.join(str(c) for c in cmd)}")
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 and log_fn:
            log_fn("package", "fail", f"exit {r.returncode}: {out[-800:]}")
        return r.returncode, out
    except subprocess.TimeoutExpired:
        if log_fn:
            log_fn("package", "fail", f"timeout after {timeout}s")
        return 124, "timeout"

def ensure_debug_keystore(log_fn=None):
    """Generate debug.keystore via keytool if missing."""
    ks_path = resolve(CONFIG["keystore"]["debug"])
    if ks_path.exists():
        return True, ks_path
    ks_path.parent.mkdir(parents=True, exist_ok=True)
    keytool = resolve(CONFIG["jdk"]["bin"]["keytool"])
    if not keytool.exists():
        # Try system keytool
        keytool = Path("/usr/bin/keytool")
    if not keytool.exists():
        return False, "keytool not found"
    cmd = [
        str(keytool),
        "-genkeypair",
        "-keystore", str(ks_path),
        "-storepass", CONFIG["keystore"]["debug_password"],
        "-alias", CONFIG["keystore"]["debug_alias"],
        "-keypass", CONFIG["keystore"]["debug_password"],
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-dname", CONFIG["keystore"]["debug_dname"],
    ]
    rc, out = run(cmd, log_fn=log_fn)
    if rc != 0:
        return False, f"keytool failed: {out}"
    return True, ks_path

def package_apk(project_dir, unsigned_apk, target="debug", build_log=None):
    """
    Returns (success, signed_apk_path_or_error).
    """
    project_dir = Path(project_dir)
    unsigned_apk = Path(unsigned_apk)
    if not unsigned_apk.exists():
        return False, f"unsigned APK not found: {unsigned_apk}"

    bt_path = resolve(CONFIG["sdk"]["build_tools"]["path"])
    zipalign = bt_path / "zipalign"
    apksigner = bt_path / "apksigner"

    out_dir = unsigned_apk.parent
    aligned_apk = out_dir / f"app-{target}-aligned.apk"
    signed_apk = out_dir / f"app-{target}-signed.apk"

    log_fn = build_log.append if build_log else None

    # 1. zipalign
    if zipalign.exists():
        rc, out = run([
            str(zipalign),
            "-f", "-p", "4",
            str(unsigned_apk),
            str(aligned_apk),
        ], log_fn=log_fn)
        if rc != 0:
            # Fall back to copying the unsigned APK
            if log_fn:
                log_fn("package", "warn", f"zipalign failed ({out[-300:]}); using unsigned APK")
            aligned_apk = unsigned_apk
    else:
        if log_fn:
            log_fn("package", "warn", "zipalign not found; skipping alignment")
        aligned_apk = unsigned_apk

    # 2. Sign
    ok, ks_result = ensure_debug_keystore(log_fn=log_fn)
    if not ok:
        return False, f"keystore setup failed: {ks_result}"
    ks_path = ks_result

    if apksigner.exists():
        rc, out = run([
            str(apksigner),
            "sign",
            "--ks", str(ks_path),
            "--ks-pass", f"pass:{CONFIG['keystore']['debug_password']}",
            "--ks-key-alias", CONFIG["keystore"]["debug_alias"],
            "--key-pass", f"pass:{CONFIG['keystore']['debug_password']}",
            "--out", str(signed_apk),
            str(aligned_apk),
        ], log_fn=log_fn)
        if rc != 0:
            return False, f"apksigner failed: {out}"
        final_apk = signed_apk
    else:
        # Fallback: use jarsigner (available with JDK)
        jarsigner = resolve(CONFIG["jdk"]["bin"]["jar"]).parent / "jarsigner"
        if not jarsigner.exists():
            jarsigner = Path("/usr/bin/jarsigner")
        if not jarsigner.exists():
            if log_fn:
                log_fn("package", "warn", "no signer available; returning aligned-but-unsigned APK")
            final_apk = aligned_apk
        else:
            rc, out = run([
                str(jarsigner),
                "-keystore", str(ks_path),
                "-storepass", CONFIG["keystore"]["debug_password"],
                "-keypass", CONFIG["keystore"]["debug_password"],
                "-signedjar", str(signed_apk),
                str(aligned_apk),
                CONFIG["keystore"]["debug_alias"],
            ], log_fn=log_fn)
            if rc != 0:
                return False, f"jarsigner failed: {out}"
            final_apk = signed_apk

    # 3. Verify
    if apksigner.exists() and final_apk != aligned_apk:
        rc, out = run([
            str(apksigner),
            "verify",
            "--print-certs",
            str(final_apk),
        ], log_fn=log_fn)
        if rc != 0 and log_fn:
            log_fn("package", "warn", f"verify returned non-zero: {out[-300:]}")

    # 4. Final rename — use project name if available
    project_name = project_dir.name.rsplit("_", 1)[0]  # strip timestamp suffix
    # Sanitize
    import re
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", project_name)
    final_named = out_dir / f"{safe_name}.apk"
    if final_named.exists():
        final_named.unlink()
    final_apk.rename(final_named)

    if build_log:
        size = final_named.stat().st_size
        build_log.append("package", "ok", f"final APK: {final_named} ({size} bytes)")

    return True, str(final_named)
