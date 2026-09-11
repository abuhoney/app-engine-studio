"""
apk_builder.py — Real APK build pipeline.

Pipeline (no Gradle):
    1. aapt2 compile   — compile res/ to .flat files
    2. aapt2 link      — link resources + AndroidManifest -> base.apk + R.java
    3. javac           — compile *.java (project + generated R.java) -> *.class
    4. d8              — dex *.class -> classes.dex
    5. zip             — merge classes.dex into base.apk -> unsigned.apk
    6. zipalign        — 4-byte align -> aligned.apk
    7. apksigner sign  — sign with keystore -> signed.apk
    8. apksigner verify

The keystore is generated on first run (25-year validity).
All paths come from engine.config.get_config().build so the pipeline is
portable across any host that has the Android SDK + JDK installed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import get_config, BuildConfig


@dataclass
class BuildResult:
    success: bool
    signed_apk: Optional[Path]
    unsigned_apk: Optional[Path]
    log: str
    elapsed_seconds: float
    error: Optional[str] = None


class ApkBuilder:
    """Drives the full aapt2 -> javac -> d8 -> apksigner pipeline."""

    def __init__(self, build: Optional[BuildConfig] = None,
                 keystore: Optional[Path] = None,
                 key_alias: str = "bardom-release",
                 store_pass: str = "bardom_release_2026",
                 key_pass: str = "bardom_release_2026"):
        self.cfg = build or get_config().build
        self.keystore = keystore
        self.key_alias = key_alias
        self.store_pass = store_pass
        self.key_pass = key_pass
        self._log_lines: list[str] = []

    # ----------------------------------------------------------------- #
    def _log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append(line)
        print(line, flush=True)

    def _run(self, cmd: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        self._log(f"$ {' '.join(str(c) for c in cmd)}")
        return subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            text=True,
        )

    # ----------------------------------------------------------------- #
    def _ensure_keystore(self) -> Path:
        """Generate a release keystore on first run (25-year validity)."""
        if self.keystore and self.keystore.exists():
            return self.keystore
        ks = self.keystore or Path.cwd() / "release.keystore"
        ks.parent.mkdir(parents=True, exist_ok=True)
        # If keystore already exists, reuse it (don't regenerate)
        if ks.exists():
            return ks
        self._log(f"Generating release keystore at {ks}")
        cmd = [
            str(self.cfg.java_home / "bin" / "keytool"),
            "-genkey", "-v",
            "-keystore", str(ks),
            "-alias", self.key_alias,
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "9125",
            "-storepass", self.store_pass,
            "-keypass", self.key_pass,
            "-noprompt",
            "-dname", "CN=BardomPro, OU=Universal App Generator, O=Bardom, "
                      "L=Riyadh, ST=Riyadh Province, C=SA",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, check=False,
                          input="")
        if r.returncode != 0:
            raise RuntimeError(f"keytool failed (rc={r.returncode}): "
                               f"stdout={r.stdout}\nstderr={r.stderr}")
        return ks

    # ----------------------------------------------------------------- #
    def build(self, project_dir: Path,
              out_apk: Optional[Path] = None) -> BuildResult:
        """Build a signed APK from a generated Android project tree."""
        t0 = time.time()
        self._log_lines.clear()
        # Always resolve to absolute paths so cwd changes don't break zip
        project_dir = Path(project_dir).resolve()
        if out_apk:
            out_apk = Path(out_apk).resolve()
        if not project_dir.exists():
            return BuildResult(False, None, None, "\n".join(self._log_lines),
                               0.0, f"Project dir not found: {project_dir}")

        try:
            # Setup dirs
            build_dir = project_dir / "build"
            gen_dir = build_dir / "gen"
            obj_dir = build_dir / "obj"
            apk_dir = build_dir / "apk"
            libs_dir = build_dir / "libs"
            for d in (gen_dir, obj_dir, apk_dir, libs_dir):
                d.mkdir(parents=True, exist_ok=True)

            res_dir = project_dir / "res"
            assets_dir = project_dir / "assets"
            manifest = project_dir / "AndroidManifest.xml"
            src_dir = project_dir / "src"

            # ---- Step 1: aapt2 compile ----------------------------------
            self._log("==== 1. Compile resources with aapt2 ====")
            compiled_zip = gen_dir / "compiled-res.zip"
            r = self._run([
                self.cfg.aapt2, "compile",
                "--dir", res_dir,
                "-o", compiled_zip,
            ])
            if r.returncode != 0:
                raise RuntimeError(f"aapt2 compile failed:\n{r.stderr}")
            self._log(r.stdout)

            # ---- Step 2: aapt2 link ------------------------------------
            self._log("==== 2. Link resources -> base.apk + R.java ====")
            base_apk = apk_dir / "base.apk"
            link_cmd = [
                self.cfg.aapt2, "link",
                "--manifest", manifest,
                "-I", self.cfg.platform_jar,
                "--java", gen_dir / "src",
                "--min-sdk-version", str(self.cfg.min_sdk),
                "--target-sdk-version", str(self.cfg.target_sdk),
                "--auto-add-overlay",
                "-o", base_apk,
            ]
            if assets_dir.exists() and any(assets_dir.iterdir()):
                link_cmd += ["-A", assets_dir]
            link_cmd.append(compiled_zip)
            r = self._run(link_cmd)
            if r.returncode != 0:
                raise RuntimeError(f"aapt2 link failed:\n{r.stderr}")
            self._log(r.stdout)

            # ---- Step 3: javac -----------------------------------------
            self._log("==== 3. Compile Java sources ====")
            java_files = []
            for d in [src_dir, gen_dir / "src"]:
                if d.exists():
                    java_files.extend([str(p) for p in d.rglob("*.java")])
            if not java_files:
                raise RuntimeError("No Java sources found to compile.")
            r = self._run([
                self.cfg.javac, "-nowarn", "-encoding", "UTF-8",
                "-classpath", self.cfg.platform_jar,
                "-d", obj_dir,
                *java_files,
            ])
            if r.returncode != 0:
                raise RuntimeError(f"javac failed:\n{r.stderr}\n{r.stdout}")
            self._log(r.stdout)

            # ---- Step 4: d8 dex ----------------------------------------
            self._log("==== 4. Dex (compile .class -> classes.dex) ====")
            class_files = [str(p) for p in obj_dir.rglob("*.class")]
            r = self._run([
                self.cfg.d8,
                "--min-api", str(self.cfg.min_sdk),
                "--lib", self.cfg.platform_jar,
                "--output", libs_dir,
                *class_files,
            ])
            if r.returncode != 0:
                raise RuntimeError(f"d8 failed:\n{r.stderr}")
            self._log(r.stdout)

            # ---- Step 5: merge dex into base.apk -----------------------
            self._log("==== 5. Build unsigned APK ====")
            unsigned_apk = apk_dir / "app-unsigned.apk"
            shutil.copy2(base_apk, unsigned_apk)
            # Add classes.dex (use absolute paths everywhere)
            dex_path = libs_dir / "classes.dex"
            if dex_path.exists():
                r = subprocess.run(
                    ["zip", "-j", "-0", str(unsigned_apk), "classes.dex"],
                    cwd=str(libs_dir), capture_output=True, text=True,
                    check=False, input="",
                )
                if r.returncode != 0:
                    raise RuntimeError(f"zip dex failed (rc={r.returncode}): "
                                       f"stdout={r.stdout}\nstderr={r.stderr}")
            # Re-add assets (preserve path) if any
            if assets_dir.exists():
                for asset in assets_dir.iterdir():
                    if asset.is_file():
                        r = subprocess.run(
                            ["zip", "-0", str(unsigned_apk), f"assets/{asset.name}"],
                            cwd=str(project_dir), capture_output=True,
                            text=True, check=False, input="",
                        )

            # ---- Step 6: zipalign --------------------------------------
            self._log("==== 6. Align APK with zipalign ====")
            aligned_apk = apk_dir / "app-aligned.apk"
            r = self._run([
                self.cfg.zipalign, "-f", "-p", "4",
                unsigned_apk, aligned_apk,
            ])
            if r.returncode != 0:
                raise RuntimeError(f"zipalign failed:\n{r.stderr}")

            # ---- Step 7: apksigner sign --------------------------------
            self._log("==== 7. Sign APK with release keystore ====")
            ks = self._ensure_keystore()
            signed_apk = out_apk or (apk_dir / "app-release.apk")
            signed_apk.parent.mkdir(parents=True, exist_ok=True)
            r = self._run([
                self.cfg.apksigner, "sign",
                "--ks", ks,
                "--ks-key-alias", self.key_alias,
                "--ks-pass", f"pass:{self.store_pass}",
                "--key-pass", f"pass:{self.key_pass}",
                "--out", signed_apk,
                aligned_apk,
            ])
            if r.returncode != 0:
                raise RuntimeError(f"apksigner sign failed:\n{r.stderr}")

            # ---- Step 8: verify ----------------------------------------
            self._log("==== 8. Verify signature ====")
            r = self._run([self.cfg.apksigner, "verify", "--verbose", signed_apk])
            if r.returncode != 0:
                raise RuntimeError(f"apksigner verify failed:\n{r.stderr}")
            self._log(r.stdout)

            elapsed = time.time() - t0
            self._log(f"==== DONE in {elapsed:.1f}s ====")
            self._log(f"Signed APK: {signed_apk}")
            return BuildResult(
                success=True,
                signed_apk=signed_apk,
                unsigned_apk=unsigned_apk,
                log="\n".join(self._log_lines),
                elapsed_seconds=elapsed,
            )

        except Exception as e:
            elapsed = time.time() - t0
            self._log(f"ERROR: {e}")
            return BuildResult(
                success=False,
                signed_apk=None,
                unsigned_apk=unsigned_apk if 'unsigned_apk' in locals() else None,
                log="\n".join(self._log_lines),
                elapsed_seconds=elapsed,
                error=str(e),
            )


# --------------------------------------------------------------------------- #
def build_apk(project_dir: Path, out_apk: Optional[Path] = None) -> BuildResult:
    """Convenience function."""
    return ApkBuilder().build(project_dir, out_apk)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m engine.apk_builder <project-dir> [out.apk]")
        sys.exit(1)
    proj = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    result = build_apk(proj, out)
    sys.exit(0 if result.success else 1)
