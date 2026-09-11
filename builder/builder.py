#!/usr/bin/env python3
"""
Bardom-builder — builder.py
============================
The brain of the offline-capable APK builder.

Flow:
  1. validate_input(project_spec)
  2. prepare_workspace(project_id, spec)
  3. ensure_tools()              ← fetches SDK/JDK/Gradle if missing, then caches for offline use
  4. copy_template(target_dir)
  5. inject_user_code(target_dir, spec)
  6. compiler.compile(target_dir)   ← javac + aapt2 + d8
  7. packager.package(target_dir)   ← zipalign + apksigner
  8. verify_apk(apk_path)
  9. deliver(apk_path, destination)

The builder is intentionally tool-agnostic: every tool path is resolved via
config.json. If a tool is missing, the corresponding fetch script downloads
and caches it under Bardom-builder/sdk|jdk|gradle/, so subsequent builds are
fully offline.

This module is import-safe: it can be invoked from Python (by the Telegram
bot backend, or by the GitHub Actions workflow) or run directly from CLI:

    python3 builder.py --project-name myapp --html webapp.html --target debug

It also writes a per-project build_log.json so the bot's monitoring loop
can report progress back to the admin.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import hashlib
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"

# When this script is committed inside abuhoney/bardom, the repo root is HERE/..
# When run inside Bardom-builder/, the repo root is HERE/..
# Both cases: resolve relative to HERE/.. so paths like "Bardom-builder/sdk/..."
# are interpreted as <repo>/Bardom-builder/sdk/...
REPO_ROOT = HERE.parent

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

def resolve(path_str):
    """Resolve a config path string to an absolute path under REPO_ROOT."""
    return (REPO_ROOT / path_str).resolve()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log(msg, level="INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    return line

class BuildLog:
    """Per-project build log written to disk so the bot can poll progress."""
    def __init__(self, project_dir):
        self.path = Path(project_dir) / "build_log.json"
        self.entries = []
        self.start = time.time()
        self.status = "initialized"

    def append(self, step, status, detail=""):
        entry = {
            "step": step,
            "status": status,
            "detail": detail,
            "elapsed_seconds": round(time.time() - self.start, 2),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.entries.append(entry)
        log(f"{step}: {status} — {detail}", level=status.upper() if status != "ok" else "INFO")
        self.flush()

    def flush(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({
                "status": self.status,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.start)),
                "entries": self.entries,
            }, f, indent=2)

    def set_status(self, s):
        self.status = s
        self.flush()

# ---------------------------------------------------------------------------
# Tool verification & fetching
# ---------------------------------------------------------------------------
def verify_tool(path_str, name):
    p = resolve(path_str)
    if p.exists():
        return True
    log(f"Tool missing: {name} at {p}", level="WARN")
    return False

def ensure_tools(build_log):
    """Verify all tools exist; for any missing, invoke the matching fetch script."""
    build_log.append("ensure_tools", "ok", "verifying tool availability")

    sdk = CONFIG["sdk"]
    jdk = CONFIG["jdk"]
    gradle = CONFIG["gradle"]

    missing = []

    # JDK
    if not verify_tool(jdk["bin"]["javac"], "javac"):
        missing.append("jdk")

    # Gradle wrapper
    if not verify_tool(gradle["wrapper"]["jar"], "gradle-wrapper.jar"):
        missing.append("gradle-wrapper")

    # SDK build-tools (aapt2, d8, zipalign, apksigner)
    bt_path = resolve(sdk["build_tools"]["path"])
    bt_ok = all((bt_path / b).exists() for b in sdk["build_tools"]["binaries"])
    if not bt_ok:
        missing.append("build-tools")

    # android.jar
    if not (resolve(sdk["platforms"]["android_34"]["path"]) / "android.jar").exists():
        missing.append("platform-34")

    if missing:
        build_log.append("ensure_tools", "ok", f"missing: {','.join(missing)} — fetching")
        for m in missing:
            fetch_script = HERE / "scripts" / f"fetch_{m.replace('-', '_').replace('.', '_')}.py"
            if fetch_script.exists():
                build_log.append("fetch_tools", "ok", f"running {fetch_script.name}")
                r = subprocess.run([sys.executable, str(fetch_script)],
                                   cwd=str(REPO_ROOT), capture_output=True, text=True)
                if r.returncode != 0:
                    build_log.append("fetch_tools", "fail", f"{fetch_script.name}: {r.stderr[-500:]}")
                    return False
            else:
                # No fetch script — try to use system-installed equivalent
                build_log.append("fetch_tools", "warn", f"no fetch script for {m}, trying system fallback")
        # Re-verify
        still_missing = []
        if not verify_tool(jdk["bin"]["javac"], "javac"): still_missing.append("jdk")
        if not verify_tool(gradle["wrapper"]["jar"], "gradle-wrapper.jar"): still_missing.append("gradle-wrapper")
        if not all((bt_path / b).exists() for b in sdk["build_tools"]["binaries"]): still_missing.append("build-tools")
        if not (resolve(sdk["platforms"]["android_34"]["path"]) / "android.jar").exists(): still_missing.append("platform-34")
        if still_missing:
            build_log.append("ensure_tools", "fail", f"still missing after fetch: {still_missing}")
            return False

    build_log.append("ensure_tools", "ok", "all tools verified")
    return True

# ---------------------------------------------------------------------------
# Workspace preparation
# ---------------------------------------------------------------------------
def prepare_workspace(project_id):
    ws_root = resolve(CONFIG["workspace"]["root"])
    ws_root.mkdir(parents=True, exist_ok=True)
    project_dir = ws_root / project_id
    if project_dir.exists():
        # Clean previous attempt
        shutil.rmtree(project_dir, ignore_errors=True)
    project_dir.mkdir(parents=True)
    return project_dir

# ---------------------------------------------------------------------------
# Template copying
# ---------------------------------------------------------------------------
def copy_template(target_dir, build_log):
    template_dir = resolve(CONFIG["templates"]["app_template"])
    if not template_dir.exists():
        build_log.append("copy_template", "fail", f"template missing: {template_dir}")
        return False
    build_log.append("copy_template", "ok", f"copying {template_dir} → {target_dir}")
    shutil.copytree(template_dir, target_dir, dirs_exist_ok=True)
    return True

# ---------------------------------------------------------------------------
# User code injection
# ---------------------------------------------------------------------------
ANDROID_NS = "http://schemas.android.com/apk/res/android"

DEFAULT_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:label="{app_label}"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:allowBackup="true"
        android:largeHeap="true"
        android:hardwareAccelerated="true"
        android:theme="@style/Theme.Unified"
        android:usesCleartextTraffic="true"
        android:requestLegacyExternalStorage="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

DEFAULT_MAIN_ACTIVITY = """package {package_base};

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {{
    private WebView webView;
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        try {{
            webView = new WebView(this);
            setContentView(webView);
            WebSettings s = webView.getSettings();
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            s.setAllowFileAccess(true);
            s.setAllowContentAccess(true);
            s.setLoadWithOverviewMode(true);
            s.setUseWideViewPort(true);
            s.setSupportZoom(true);
            s.setBuiltInZoomControls(true);
            s.setDisplayZoomControls(false);
            s.setMediaPlaybackRequiresUserGesture(false);
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            webView.setWebViewClient(new WebViewClient());
            webView.loadUrl("file:///android_asset/webapp.html");
        }} catch (Exception e) {{
            throw new RuntimeException(e);
        }}
    }}
    @Override
    public void onBackPressed() {{
        if (webView != null && webView.canGoBack()) {{
            webView.goBack();
        }} else {{
            super.onBackPressed();
        }}
    }}
}}
"""

def inject_user_code(target_dir, spec, build_log):
    """
    spec keys:
      - app_name (label)         e.g. "My App"
      - package_name             e.g. "com.example.myapp"
      - version_name             e.g. "1.0.0"
      - version_code             e.g. "1"
      - html_content (bytes)     the WebView payload
      - main_activity_java (str, optional) — override default
      - manifest_xml (str, optional) — override default
      - resources (dict, optional) — extra res files to write
    """
    pkg = spec.get("package_name", "com.bardom.unified")
    pkg_base = pkg
    pkg_path = pkg.replace(".", "/")

    src_main = Path(target_dir) / "app" / "src" / "main"
    java_dir = src_main / "java" / pkg_path
    java_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = src_main / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # AndroidManifest.xml
    manifest = spec.get("manifest_xml") or DEFAULT_MANIFEST.format(
        package_name=pkg,
        version_code=spec.get("version_code", "1"),
        version_name=spec.get("version_name", "1.0.0"),
        app_label=spec.get("app_name", "Unified App"),
    )
    (src_main / "AndroidManifest.xml").write_text(manifest, encoding="utf-8")
    build_log.append("inject_user_code", "ok", f"manifest written (package={pkg})")

    # MainActivity.java
    main_java = spec.get("main_activity_java") or DEFAULT_MAIN_ACTIVITY.format(package_base=pkg_base)
    (java_dir / "MainActivity.java").write_text(main_java, encoding="utf-8")
    build_log.append("inject_user_code", "ok", f"MainActivity.java written (package={pkg_base})")

    # webapp.html (the user's HTML payload)
    html = spec.get("html_content")
    if html is None:
        # Default to whatever is in the template
        default_html = src_main / "assets" / "webapp.html"
        if default_html.exists():
            build_log.append("inject_user_code", "ok", "using template webapp.html (no override)")
        else:
            (assets_dir / "webapp.html").write_text(
                "<!DOCTYPE html><html><body><h1>Hello from Bardom-builder</h1></body></html>",
                encoding="utf-8")
            build_log.append("inject_user_code", "warn", "no html_content provided, wrote placeholder")
    else:
        if isinstance(html, str):
            html = html.encode("utf-8")
        (assets_dir / "webapp.html").write_bytes(html)
        build_log.append("inject_user_code", "ok", f"webapp.html written ({len(html)} bytes)")

    # Extra resources
    for rel_path, content in (spec.get("resources") or {}).items():
        target = src_main / "res" / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        build_log.append("inject_user_code", "ok", f"resource written: {rel_path}")

    # build.gradle for the app module
    app_gradle = f"""plugins {{
    id 'com.android.application'
}}

android {{
    namespace '{pkg}'
    compileSdk 34

    defaultConfig {{
        applicationId "{pkg}"
        minSdk 21
        targetSdk 34
        versionCode {spec.get("version_code", "1")}
        versionName "{spec.get("version_name", "1.0.0")}"
    }}

    buildTypes {{
        release {{
            minifyEnabled false
        }}
        debug {{
            minifyEnabled false
        }}
    }}

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
}}

dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.webkit:webkit:1.9.0'
}}
"""
    (Path(target_dir) / "app" / "build.gradle").write_text(app_gradle, encoding="utf-8")

    # settings.gradle
    settings_gradle = """pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "%s"
include ':app'
""" % spec.get("app_name", "Unified App").replace('"', '')
    (Path(target_dir) / "settings.gradle").write_text(settings_gradle, encoding="utf-8")

    # Top-level build.gradle
    (Path(target_dir) / "build.gradle").write_text(
        "plugins {\n    id 'com.android.application' version '8.1.4' apply false\n}\n",
        encoding="utf-8")

    # gradle.properties (offline)
    gradle_props = CONFIG["gradle"]["properties"]
    props_lines = []
    for k, v in gradle_props.items():
        if k == "path": continue
        props_lines.append(f"{k}={v}")
    (Path(target_dir) / "gradle.properties").write_text("\n".join(props_lines) + "\n", encoding="utf-8")

    # gradle-wrapper.properties
    wrapper_dir = Path(target_dir) / "gradle" / "wrapper"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    wrapper_props = f"""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.4-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
networkTimeout=10000
validateDistributionUrl=true
"""
    (wrapper_dir / "gradle-wrapper.properties").write_text(wrapper_props, encoding="utf-8")

    # Copy gradle-wrapper.jar from our cache
    cached_wrapper = resolve(CONFIG["gradle"]["wrapper"]["jar"])
    if cached_wrapper.exists():
        shutil.copy2(cached_wrapper, wrapper_dir / "gradle-wrapper.jar")
        build_log.append("inject_user_code", "ok", "gradle-wrapper.jar copied from cache")
    else:
        build_log.append("inject_user_code", "warn", "gradle-wrapper.jar missing — gradle will download on first run")

    # gradlew script
    gradlew_script = """#!/usr/bin/env sh
# Gradle wrapper bootstrap
DIR="$(cd "$(dirname "$0")" && pwd)"
exec java -classpath "$DIR/gradle/wrapper/gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain "$@"
"""
    gradlew_path = Path(target_dir) / "gradlew"
    gradlew_path.write_text(gradlew_script, encoding="utf-8")
    gradlew_path.chmod(0o755)

    # Copy debug keystore if present
    ks_path = resolve(CONFIG["keystore"]["debug"])
    if ks_path.exists():
        ks_target = Path(target_dir) / "app" / "debug.keystore"
        shutil.copy2(ks_path, ks_target)

    return True

# ---------------------------------------------------------------------------
# Build orchestration
# ---------------------------------------------------------------------------
def build(project_id, spec, target="debug", build_log=None):
    """Main entry point. Returns (success, apk_path_or_error)."""
    if build_log is None:
        project_dir = prepare_workspace(project_id)
        build_log = BuildLog(project_dir)
    else:
        project_dir = Path(build_log.path).parent

    build_log.set_status("running")

    try:
        # 1. ensure tools
        if not ensure_tools(build_log):
            build_log.set_status("failed")
            return False, "tool verification failed"

        # 2. copy template
        if not copy_template(project_dir, build_log):
            build_log.set_status("failed")
            return False, "template copy failed"

        # 3. inject user code
        if not inject_user_code(project_dir, spec, build_log):
            build_log.set_status("failed")
            return False, "code injection failed"

        # 4. compile
        from compiler import compile_project
        compile_ok, apk_unsigned = compile_project(project_dir, target, build_log)
        if not compile_ok:
            build_log.set_status("failed")
            return False, f"compile failed: {apk_unsigned}"

        # 5. package (zipalign + sign)
        from packager import package_apk
        pkg_ok, apk_final = package_apk(project_dir, apk_unsigned, target, build_log)
        if not pkg_ok:
            build_log.set_status("failed")
            return False, f"packaging failed: {apk_final}"

        # 6. verify
        if not Path(apk_final).exists():
            build_log.set_status("failed")
            return False, f"final APK not found: {apk_final}"

        size = Path(apk_final).stat().st_size
        build_log.append("verify_apk", "ok", f"APK ready: {apk_final} ({size} bytes)")
        build_log.set_status("success")
        return True, apk_final

    except Exception as e:
        tb = traceback.format_exc()
        build_log.append("build", "fail", f"exception: {e}\n{tb[-500:]}")
        build_log.set_status("failed")
        return False, str(e)

# ---------------------------------------------------------------------------
# Pattern learning
# ---------------------------------------------------------------------------
PATTERN_HASH_FIELDS = ("package_name", "version_name", "app_name")

def pattern_hash(spec):
    """A stable hash of the user-code shape (not the HTML payload itself)."""
    h = hashlib.sha256()
    for f in PATTERN_HASH_FIELDS:
        h.update(str(spec.get(f, "")).encode())
    html = spec.get("html_content", b"")
    if isinstance(html, str): html = html.encode()
    # Hash only first 4KB + last 1KB + length to ignore trivial payload changes
    h.update(str(len(html)).encode())
    h.update(html[:4096])
    if len(html) > 5120:
        h.update(html[-1024:])
    return h.hexdigest()

def load_patterns():
    patterns_dir = REPO_ROOT.parent / CONFIG["github"]["patterns_dir"]
    if not patterns_dir.exists():
        return {}
    out = {}
    for p in patterns_dir.rglob("*.json"):
        try:
            with open(p) as f:
                data = json.load(f)
            ph = data.get("pattern_hash")
            if ph:
                out[ph] = data
        except Exception:
            pass
    return out

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--html", help="Path to HTML payload file")
    ap.add_argument("--package", default="com.bardom.unified")
    ap.add_argument("--version-name", default="1.0.0")
    ap.add_argument("--version-code", default="1")
    ap.add_argument("--target", choices=["debug", "release"], default="debug")
    args = ap.parse_args()

    html = b""
    if args.html:
        with open(args.html, "rb") as f:
            html = f.read()

    spec = {
        "app_name": args.project_name,
        "package_name": args.package,
        "version_name": args.version_name,
        "version_code": args.version_code,
        "html_content": html,
    }

    project_id = f"{args.project_name}_{int(time.time())}"
    ok, result = build(project_id, spec, target=args.target)
    if ok:
        print(f"\n✅ APK built: {result}")
    else:
        print(f"\n❌ Build failed: {result}")
        sys.exit(1)

if __name__ == "__main__":
    main()
