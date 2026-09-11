"""
config.py — Central configuration loader for the BardomPro Universal App Generator.

Loads every credential from .env (Telegram, GitHub, Render, AI, Firebase)
and exposes them as a singleton `Config` object. Also resolves the Android
SDK / JDK paths so the build pipeline works on any host.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


def _project_root() -> Path:
    """Return the directory that contains the .env file (project root)."""
    # engine/config.py -> engine/ -> project root
    here = Path(__file__).resolve()
    return here.parent.parent


def _load_env_file(env_path: Path) -> dict[str, str]:
    """Parse a .env file by hand (no python-dotenv dependency required)."""
    data: dict[str, str] = {}
    if not env_path.exists():
        return data
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # strip inline comments only if value is not quoted
        if value and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        data[key] = value
    return data


@dataclass
class TelegramConfig:
    api_id: str
    api_hash: str
    bot_token: str
    admin_chat_id: str
    bot_username: str

    @property
    def base_url(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}"


@dataclass
class GitHubConfig:
    repo: str           # owner/repo
    branch: str
    token: str

    @property
    def api_base(self) -> str:
        return f"https://api.github.com/repos/{self.repo}"

    @property
    def auth_header(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }


@dataclass
class RenderConfig:
    api_key: str
    service_id: str

    @property
    def auth_header(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }


@dataclass
class AIConfig:
    token: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int

    @property
    def auth_header(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }


@dataclass
class FirebaseConfig:
    api_key: str
    app_id: str
    auth_domain: str
    database_url: str
    project_id: str


@dataclass
class BuildConfig:
    """Resolved paths to Android SDK / JDK so the build pipeline is portable."""
    android_sdk: Path
    build_tools: Path
    platform_jar: Path
    java_home: Path
    min_sdk: int = 21
    target_sdk: int = 34

    @property
    def aapt2(self) -> Path: return self.build_tools / "aapt2"
    @property
    def aapt(self) -> Path:  return self.build_tools / "aapt"
    @property
    def d8(self) -> Path:    return self.build_tools / "d8"
    @property
    def zipalign(self) -> Path: return self.build_tools / "zipalign"
    @property
    def apksigner(self) -> Path: return self.build_tools / "apksigner"
    @property
    def javac(self) -> Path: return self.java_home / "bin" / "javac"
    @property
    def keytool(self) -> Path: return self.java_home / "bin" / "keytool"


@dataclass
class Config:
    """Singleton-like configuration object.

    Resolution order for SDK / JDK paths:
      1. ANDROID_HOME / JAVA_HOME environment variables
      2. sdk_config/paths.json (created by setup.sh)
      3. Sensible defaults under /home/z/my-project/android-sdk and
         /home/z/my-project/jdk/jdk-17.0.20+8 (the bundled environment)
    """
    project_root: Path
    env_path: Path
    engine_dir: str
    env: dict[str, str] = field(default_factory=dict)

    telegram: Optional[TelegramConfig] = None
    github: Optional[GitHubConfig] = None
    render: Optional[RenderConfig] = None
    ai: Optional[AIConfig] = None
    firebase: Optional[FirebaseConfig] = None
    build: Optional[BuildConfig] = None

    auto_push_github: bool = False
    require_100_test_pass: bool = True

    # Backend
    backend_url: str = ""
    backend_secret: str = ""
    node_env: str = "production"
    port: int = 3000

    # ----------------------------------------------------------------- #
    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Config":
        root = _project_root()
        env_path = env_path or root / ".env"
        env = _load_env_file(env_path)

        cfg = cls(
            project_root=root,
            env_path=env_path,
            engine_dir=env.get("ENGINE_DIR", "Bardom engine"),
            env=env,
        )

        # Telegram
        if env.get("BOT_TOKEN"):
            cfg.telegram = TelegramConfig(
                api_id=env.get("API_ID", ""),
                api_hash=env.get("API_HASH", ""),
                bot_token=env["BOT_TOKEN"],
                admin_chat_id=env.get("TELEGRAM_ADMIN_CHAT_ID", ""),
                bot_username=env.get("BOT_USERNAME", ""),
            )

        # GitHub
        if env.get("GITHUB_TOKEN"):
            cfg.github = GitHubConfig(
                repo=env.get("GITHUB_REPO", ""),
                branch=env.get("GITHUB_BRANCH", "main"),
                token=env["GITHUB_TOKEN"],
            )

        # Render
        if env.get("RENDER_API_KEY"):
            cfg.render = RenderConfig(
                api_key=env["RENDER_API_KEY"],
                service_id=env.get("RENDER_SERVICE_ID", ""),
            )

        # AI
        if env.get("AI_TOKEN"):
            cfg.ai = AIConfig(
                token=env["AI_TOKEN"],
                base_url=env.get("AI_BASE_URL",
                                 "https://openrouter.ai/api/v1/chat/completions"),
                model=env.get("AI_MODEL", "moonshotai/kimi-k2"),
                temperature=float(env.get("AI_TEMP", "0.3")),
                max_tokens=int(env.get("AI_MAX_TOKENS", "40000")),
            )

        # Firebase
        if env.get("FIREBASE_API_KEY"):
            cfg.firebase = FirebaseConfig(
                api_key=env["FIREBASE_API_KEY"],
                app_id=env.get("FIREBASE_APP_ID", ""),
                auth_domain=env.get("FIREBASE_AUTH_DOMAIN", ""),
                database_url=env.get("FIREBASE_DATABASE_URL", ""),
                project_id=env.get("FIREBASE_PROJECT_ID", ""),
            )

        # Backend
        cfg.backend_url = env.get("BACKEND_URL", "")
        cfg.backend_secret = env.get("BACKEND_SECRET", "")
        cfg.node_env = env.get("NODE_ENV", "production")
        cfg.port = int(env.get("PORT", "3000"))

        # Safety flags
        cfg.auto_push_github = env.get("AUTO_PUSH_GITHUB", "false").lower() == "true"
        cfg.require_100_test_pass = env.get("REQUIRE_100_TEST_PASS", "true").lower() == "true"

        # Build paths
        cfg.build = _resolve_build_config(root)
        return cfg

    # ----------------------------------------------------------------- #
    def summary(self) -> str:
        lines = [
            "BardomPro Universal App Generator — Configuration Summary",
            "=" * 60,
            f"  Project root   : {self.project_root}",
            f"  Engine dir     : {self.engine_dir}",
            f"  Telegram bot   : @{self.telegram.bot_username if self.telegram else 'NOT SET'}",
            f"  GitHub repo    : {self.github.repo if self.github else 'NOT SET'}",
            f"  Render service : {self.render.service_id if self.render else 'NOT SET'}",
            f"  AI model       : {self.ai.model if self.ai else 'NOT SET'}",
            f"  Firebase proj  : {self.firebase.project_id if self.firebase else 'NOT SET'}",
            f"  Auto-push      : {self.auto_push_github}",
            f"  Require 100 test: {self.require_100_test_pass}",
        ]
        if self.build:
            lines += [
                "",
                "  Build paths:",
                f"    Android SDK   : {self.build.android_sdk}",
                f"    Build tools   : {self.build.build_tools}",
                f"    Platform jar  : {self.build.platform_jar}",
                f"    JAVA_HOME     : {self.build.java_home}",
            ]
        return "\n".join(lines)


def _resolve_build_config(root: Path) -> BuildConfig:
    """Resolve Android SDK / JDK paths from env, config file, or defaults."""
    paths_file = root / "sdk_config" / "paths.json"
    saved: dict[str, str] = {}
    if paths_file.exists():
        try:
            saved = json.loads(paths_file.read_text())
        except Exception:
            saved = {}

    # 1. Environment variables (highest priority)
    sdk_str = os.environ.get("ANDROID_HOME") or saved.get("android_sdk") or ""
    java_str = os.environ.get("JAVA_HOME") or saved.get("java_home") or ""

    # 2. Defaults that work in the bundled environment
    if not sdk_str:
        default_sdk = Path("/home/z/my-project/android-sdk")
        if default_sdk.exists():
            sdk_str = str(default_sdk)
    if not java_str:
        default_jdk = Path("/home/z/my-project/jdk/jdk-17.0.20+8")
        if default_jdk.exists():
            java_str = str(default_jdk)

    if not sdk_str or not java_str:
        sys.stderr.write(
            "[Config] WARNING: Android SDK or JDK not found.\n"
            "         Run setup.sh to auto-detect, or set ANDROID_HOME / JAVA_HOME.\n"
        )
        # Return a stub so imports still succeed
        return BuildConfig(
            android_sdk=Path(sdk_str or "ANDROID_HOME_NOT_SET"),
            build_tools=Path("BUILD_TOOLS_NOT_SET"),
            platform_jar=Path("PLATFORM_JAR_NOT_SET"),
            java_home=Path(java_str or "JAVA_HOME_NOT_SET"),
        )

    sdk = Path(sdk_str)
    # Pick the highest build-tools version available
    bt_dir = sdk / "build-tools"
    if bt_dir.exists():
        bt_versions = sorted([p.name for p in bt_dir.iterdir() if p.is_dir()])
        bt_version = bt_versions[-1] if bt_versions else "34.0.0"
    else:
        bt_version = "34.0.0"
    build_tools = bt_dir / bt_version

    # Pick the highest platform available
    plat_dir = sdk / "platforms"
    if plat_dir.exists():
        plat_versions = sorted([p.name for p in plat_dir.iterdir() if p.is_dir()])
        plat_version = plat_versions[-1] if plat_versions else "android-34"
    else:
        plat_version = "android-34"
    platform_jar = plat_dir / plat_version / "android.jar"

    return BuildConfig(
        android_sdk=sdk,
        build_tools=build_tools,
        platform_jar=platform_jar,
        java_home=Path(java_str),
    )


# Singleton for convenience
_CONFIG: Optional[Config] = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = Config.load()
    return _CONFIG


if __name__ == "__main__":
    print(get_config().summary())
