#!/usr/bin/env python3
"""
Bardom-builder — compiler.py
============================
Resolves the build-tool paths from config.json and runs them in order:
  1. aapt2 compile  — compile resources/*.xml to compiled/*.flat
  2. aapt2 link     — link flats + android.jar → base.apk (resources-only) + R.java
  3. javac          — compile *.java (including R.java) against android.jar → *.class
  4. d8             — convert *.class → classes.dex
  5. merge dex into the resources-only APK → unsigned APK

If gradle is available and preferred (the default), we instead delegate to
`./gradlew assembleDebug` which does all of the above internally. The
explicit tool-by-tool path is the fallback used when Gradle cannot reach
the internet to download the Android Gradle Plugin.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
CONFIG_PATH = HERE / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

def resolve(p):
    return (REPO_ROOT / p).resolve()

def run(cmd, cwd=None, env=None, log_fn=None, timeout=600):
    """Run a command, streaming output. Returns (returncode, stdout+stderr)."""
    if log_fn:
        log_fn("compile", "ok", f"$ {' '.join(str(c) for c in cmd)}")
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0 and log_fn:
            log_fn("compile", "fail", f"exit {r.returncode}: {out[-1000:]}")
        return r.returncode, out
    except subprocess.TimeoutExpired:
        if log_fn:
            log_fn("compile", "fail", f"timeout after {timeout}s")
        return 124, "timeout"

def compile_project(project_dir, target="debug", build_log=None):
    """
    Returns (success, apk_path_or_error_message).
    """
    project_dir = Path(project_dir)
    build_gradle = project_dir / "build.gradle"
    gradlew = project_dir / "gradlew"

    # ---------------- Path A: Gradle (preferred) ----------------
    if gradlew.exists() and build_gradle.exists():
        if build_log:
            build_log.append("compile", "ok", "path A: gradle-based build")

        # Prefer the cached gradle-wrapper.jar if present
        cached_wrapper = resolve(CONFIG["gradle"]["wrapper"]["jar"])
        target_wrapper = project_dir / "gradle" / "wrapper" / "gradle-wrapper.jar"
        if cached_wrapper.exists() and not target_wrapper.exists():
            target_wrapper.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(cached_wrapper, target_wrapper)

        # JAVA_HOME from config (or fall back to system)
        jdk_bin = resolve(CONFIG["jdk"]["bin"]["javac"]).parent
        java_home = jdk_bin.parent
        env = os.environ.copy()
        env["JAVA_HOME"] = str(java_home)
        env["PATH"] = str(jdk_bin) + ":" + env["PATH"]
        # Offline hint — but allow online if needed
        env["GRADLE_OPTS"] = "-Dorg.gradle.daemon=false -Dorg.gradle.caching=true"

        task = "assembleRelease" if target == "release" else "assembleDebug"
        cmd = ["./gradlew", task, "--stacktrace", "--no-daemon"]
        rc, out = run(cmd, cwd=str(project_dir), env=env, log_fn=build_log.append if build_log else None, timeout=900)

        if rc != 0:
            # Gradle failed — try the offline flag as a last resort
            if build_log:
                build_log.append("compile", "warn", "gradle online failed, retrying offline")
            cmd2 = ["./gradlew", task, "--offline", "--stacktrace", "--no-daemon"]
            rc, out = run(cmd2, cwd=str(project_dir), env=env, log_fn=build_log.append if build_log else None, timeout=900)

        if rc != 0:
            return False, f"gradle {task} failed: {out[-500:]}"

        # Find APK
        apk = find_apk(project_dir, target)
        if apk:
            if build_log:
                build_log.append("compile", "ok", f"APK produced: {apk}")
            return True, str(apk)
        return False, f"no APK found after gradle {task}"

    # ---------------- Path B: raw tool-by-tool fallback ----------------
    if build_log:
        build_log.append("compile", "ok", "path B: raw tool-by-tool build (offline)")

    sdk = CONFIG["sdk"]
    jdk = CONFIG["jdk"]
    bt_path = resolve(sdk["build_tools"]["path"])
    android_jar = resolve(sdk["platforms"]["android_34"]["path"]) / "android.jar"
    javac = resolve(jdk["bin"]["javac"])

    src_main = project_dir / "app" / "src" / "main"
    res_dir = src_main / "res"
    manifest = src_main / "AndroidManifest.xml"
    java_src = src_main / "java"

    # Build directories
    build_dir = project_dir / "app" / "build"
    intermediates = build_dir / "intermediates"
    compiled_res_dir = intermediates / "compiled_res"
    generated_java = intermediates / "generated" / "r"
    classes_dir = intermediates / "javac" / target
    dex_dir = intermediates / "dex"
    outputs = build_dir / "outputs" / "apk" / target
    for d in (compiled_res_dir, generated_java, classes_dir, dex_dir, outputs):
        d.mkdir(parents=True, exist_ok=True)

    # 1. aapt2 compile
    aapt2 = bt_path / "aapt2"
    flats = []
    if res_dir.exists():
        for res_file in res_dir.rglob("*"):
            if res_file.is_file():
                rel = res_file.relative_to(res_dir)
                out_flat = compiled_res_dir / (str(rel).replace("/", "_").replace(".", "_") + ".flat")
                rc, out = run([str(aapt2), "compile", "-o", str(out_flat), str(res_file)],
                              log_fn=build_log.append if build_log else None)
                if rc != 0:
                    return False, f"aapt2 compile failed: {out}"
                flats.append(out_flat)

    # 2. aapt2 link
    apk_resources = outputs / "resources.apk"
    rc, out = run([
        str(aapt2), "link",
        "-I", str(android_jar),
        "--manifest", str(manifest),
        "-o", str(apk_resources),
        "--java", str(generated_java),
        "--auto-add-overlay",
    ] + [str(f) for f in flats],
        log_fn=build_log.append if build_log else None)
    if rc != 0:
        return False, f"aapt2 link failed: {out}"

    # 3. javac
    java_files = list(java_src.rglob("*.java")) + list(generated_java.rglob("*.java"))
    if not java_files:
        return False, "no .java files to compile"
    rc, out = run([
        str(javac),
        "-source", "17", "-target", "17",
        "-bootclasspath", str(android_jar),
        "-classpath", str(android_jar),
        "-d", str(classes_dir),
    ] + [str(f) for f in java_files],
        log_fn=build_log.append if build_log else None, timeout=300)
    if rc != 0:
        return False, f"javac failed: {out}"

    # 4. d8 (dex)
    d8 = bt_path / "d8"
    class_files = list(classes_dir.rglob("*.class"))
    rc, out = run([
        str(d8),
        "--lib", str(android_jar),
        "--output", str(dex_dir),
    ] + [str(f) for f in class_files],
        log_fn=build_log.append if build_log else None, timeout=300)
    if rc != 0:
        return False, f"d8 failed: {out}"

    # 5. merge dex into resources APK
    classes_dex = dex_dir / "classes.dex"
    if not classes_dex.exists():
        return False, "classes.dex not produced"

    # Use Python's zipfile to merge — keeps the offline story simple
    import zipfile
    import shutil
    final_apk = outputs / f"app-{target}.apk"
    shutil.copy2(apk_resources, final_apk)
    with zipfile.ZipFile(final_apk, "a") as z:
        z.write(classes_dex, "classes.dex")

    if build_log:
        build_log.append("compile", "ok", f"APK produced (offline path): {final_apk}")
    return True, str(final_apk)

def find_apk(project_dir, target):
    """Look in standard Gradle output locations."""
    candidates = [
        project_dir / "app" / "build" / "outputs" / "apk" / target / f"app-{target}.apk",
        project_dir / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk",
        project_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Last resort: glob
    for c in (project_dir / "app" / "build" / "outputs").rglob("*.apk"):
        return c
    return None
