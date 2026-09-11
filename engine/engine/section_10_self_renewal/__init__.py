"""
SECTION 10 — SELF-RENEWAL, SELF-RECOVERY, AUTO-EVOLUTION, TESTING,
CI/CD, TERMUX/LINUX, GITHUB/CLOUD, AND FAILURE RECOVERY

Implements the CI/CD + self-renewal layer.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List


CI_PIPELINES_SUPPORTED: List[str] = [
    "github_actions", "gitlab_ci", "bitbucket_pipelines",
    "circle_ci", "travis_ci", "jenkins", "termux_sh", "linux_makefile",
]


class SelfRenewal:
    """Section 10 — CI/CD + self-recovery + auto-evolution."""

    def __init__(self, ctx):
        self.ctx = ctx

    def run(self) -> None:
        # 1. Generate a default GitHub Actions workflow for the project
        workflow = self.generate_github_actions_workflow()
        self.ctx.vfs[".github/workflows/build.yml"] = workflow.encode("utf-8")

        # 2. Generate a Termux build.sh
        termux_sh = self.generate_termux_build_sh()
        self.ctx.vfs["build_termux.sh"] = termux_sh.encode("utf-8")

        # 3. Generate a Linux Makefile
        makefile = self.generate_makefile()
        self.ctx.vfs["Makefile"] = makefile.encode("utf-8")

        # 4. Generate a test runner
        test_runner = self.generate_test_runner()
        self.ctx.vfs["tests/run_tests.sh"] = test_runner.encode("utf-8")

        # 5. Generate a recovery script
        recovery = self.generate_recovery_script()
        self.ctx.vfs["scripts/recover.sh"] = recovery.encode("utf-8")

        # 6. Register self-healing keys
        keys = [
            "self_healing.error_classifier", "self_healing.retry_manager",
            "self_healing.fallback_manager", "self_healing.snapshot_manager",
            "self_healing.rollback_manager", "self_healing.safe_mode_manager",
            "self_healing.patch_queue", "self_healing.recovery_reporter",
            "evolution.plugin_loader", "evolution.schema_migrator",
            "evolution.feature_flag_loader", "evolution.template_migrator",
            "evolution.module_upgrader", "evolution.compatibility_guard",
        ]
        for k in keys:
            self.ctx.module_registry[k] = {
                "key": k, "section": 10,
                "title": k.split(".")[-1].replace("_", " ").title(),
            }

        self.ctx.audit_log.append({
            "section": 10,
            "status": "ok",
            "ci_pipelines_supported": CI_PIPELINES_SUPPORTED,
            "files_added": [".github/workflows/build.yml", "build_termux.sh",
                            "Makefile", "tests/run_tests.sh", "scripts/recover.sh"],
            "message": "CI/CD + self-renewal pipeline files generated",
        })

    # -- File generators ----------------------------------------------------

    def generate_github_actions_workflow(self) -> str:
        return f"""name: Build APK

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  workflow_dispatch:
    inputs:
      build_id:
        description: 'Build ID'
        required: false
        default: 'manual'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      - name: Set up Android SDK
        uses: android-actions/setup-android@v3
        with:
          sdk-platform: '34'
          sdk-build-tools: '34.0.0'
      - name: Build with aapt2 + d8 + apksigner
        run: |
          mkdir -p build/obj build/apk
          # Compile resources
          aapt2 compile --dir res -o build/compiled-res.zip
          # Link resources -> base.apk + R.java
          aapt2 link --manifest AndroidManifest.xml \\
            -I $ANDROID_HOME/platforms/android-34/android.jar \\
            --java build/gen \\
            --min-sdk-version 24 --target-sdk-version 34 \\
            -o build/apk/base.apk build/compiled-res.zip
          # Compile Java
          find build/gen src -name '*.java' > sources.txt
          javac -nowarn -encoding UTF-8 \\
            -classpath $ANDROID_HOME/platforms/android-34/android.jar \\
            -d build/obj @sources.txt
          # Dex
          jar cf build/obj/classes.jar -C build/obj .
          d8 --release --min-api 24 \\
            --lib $ANDROID_HOME/platforms/android-34/android.jar \\
            --output build/obj build/obj/classes.jar
          # Package
          cp build/apk/base.apk build/apk/unsigned.apk
          zip -j build/apk/unsigned.apk build/obj/classes.dex
          # Align
          zipalign -f 4 build/apk/unsigned.apk build/apk/aligned.apk
          # Sign (debug keystore generated if none provided)
          if [ ! -f debug.keystore ]; then
            keytool -genkeypair -v -keystore debug.keystore \\
              -storepass android -keypass android -alias androiddebugkey \\
              -keyalg RSA -keysize 2048 -validity 9125 \\
              -dname "CN=Android Debug,O=Android,C=US"
          fi
          apksigner sign --ks debug.keystore \\
            --ks-pass pass:android --key-pass pass:android \\
            --out app-release.apk build/apk/aligned.apk
          apksigner verify --verbose app-release.apk
      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: app-release-apk
          path: app-release.apk
"""

    def generate_termux_build_sh(self) -> str:
        return """#!/data/data/com.termux/files/usr/bin/bash
# Termux build script — install deps + build APK
set -e

echo "=== Installing build deps ==="
pkg install -y openjdk-17 android-tools aapt apksigner zip

export ANDROID_HOME=$PREFIX/share/android-sdk
mkdir -p $ANDROID_HOME/platforms/android-34
# (User must place android.jar at $ANDROID_HOME/platforms/android-34/)

echo "=== Building APK ==="
mkdir -p build/obj build/apk

aapt2 compile --dir res -o build/compiled-res.zip
aapt2 link --manifest AndroidManifest.xml \\
  -I $ANDROID_HOME/platforms/android-34/android.jar \\
  --java build/gen --min-sdk-version 24 --target-sdk-version 34 \\
  -o build/apk/base.apk build/compiled-res.zip

find build/gen src -name '*.java' > sources.txt
javac -nowarn -encoding UTF-8 \\
  -classpath $ANDROID_HOME/platforms/android-34/android.jar \\
  -d build/obj @sources.txt

jar cf build/obj/classes.jar -C build/obj .
d8 --release --min-api 24 \\
  --lib $ANDROID_HOME/platforms/android-34/android.jar \\
  --output build/obj build/obj/classes.jar

cp build/apk/base.apk build/apk/unsigned.apk
zip -j build/apk/unsigned.apk build/obj/classes.dex
zipalign -f 4 build/apk/unsigned.apk build/apk/aligned.apk

if [ ! -f debug.keystore ]; then
  keytool -genkeypair -v -keystore debug.keystore \\
    -storepass android -keypass android -alias androiddebugkey \\
    -keyalg RSA -keysize 2048 -validity 9125 \\
    -dname "CN=Android Debug,O=Android,C=US"
fi
apksigner sign --ks debug.keystore \\
  --ks-pass pass:android --key-pass pass:android \\
  --out app-release.apk build/apk/aligned.apk

echo "=== APK: app-release.apk ==="
ls -lh app-release.apk
"""

    def generate_makefile(self) -> str:
        return """# Makefile for Linux/macOS build
ANDROID_HOME ?= $(HOME)/Android/Sdk
PLATFORM_JAR = $(ANDROID_HOME)/platforms/android-34/android.jar
BT = $(ANDROID_HOME)/build-tools/34.0.0

.PHONY: all clean
all: app-release.apk

clean:
\trm -rf build/ app-release.apk

app-release.apk: clean
\tmkdir -p build/obj build/apk
\t$(BT)/aapt2 compile --dir res -o build/compiled-res.zip
\t$(BT)/aapt2 link --manifest AndroidManifest.xml \\
\t  -I $(PLATFORM_JAR) --java build/gen \\
\t  --min-sdk-version 24 --target-sdk-version 34 \\
\t  -o build/apk/base.apk build/compiled-res.zip
\tfind build/gen src -name '*.java' > sources.txt
\tjavac -nowarn -encoding UTF-8 -classpath $(PLATFORM_JAR) -d build/obj @sources.txt
\tjar cf build/obj/classes.jar -C build/obj .
\t$(BT)/d8 --release --min-api 24 --lib $(PLATFORM_JAR) \\
\t  --output build/obj build/obj/classes.jar
\tcp build/apk/base.apk build/apk/unsigned.apk
\tzip -j build/apk/unsigned.apk build/obj/classes.dex
\t$(BT)/zipalign -f 4 build/apk/unsigned.apk build/apk/aligned.apk
\t$(BT)/apksigner sign --ks debug.keystore \\
\t  --ks-pass pass:android --key-pass pass:android \\
\t  --out app-release.apk build/apk/aligned.apk
\t@echo "Built: app-release.apk"
"""

    def generate_test_runner(self) -> str:
        return """#!/bin/bash
# Run all Python tests in tests/ directory
set -e
cd "$(dirname "$0")/.."
python3 -m pytest tests/ -v "$@"
"""

    def generate_recovery_script(self) -> str:
        return """#!/bin/bash
# Recovery script — restores the project from the latest rollback snapshot
set -e
SNAPSHOT_DIR="${SNAPSHOT_DIR:-./.snapshots}"
LATEST=$(ls -t $SNAPSHOT_DIR/snapshot_*.json 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
  echo "No snapshot found in $SNAPSHOT_DIR"
  exit 1
fi

echo "Restoring from: $LATEST"
python3 -c "
import json, sys, os
with open('$LATEST') as f:
    snap = json.load(f)
for path, content_b64 in snap.get('vfs', {}).items():
    import base64
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'wb') as out:
        out.write(base64.b64decode(content_b64))
    print(f'  restored: {path}')
"
echo "Recovery complete."
"""
