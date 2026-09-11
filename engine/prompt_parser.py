"""
prompt_parser.py — Read a prompt file line-by-line and build a FeatureManifest.

The prompt file can be either:
  - Plain text (one feature per line, or paragraph blocks)
  - Markdown (headings become feature groups)
  - YAML-ish (key: value pairs)

The parser is intentionally tolerant: it extracts whatever it can and produces
a normalized Feature list that the project_generator consumes.
"""
from __future__ import annotations

import re
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Feature:
    """One atomic feature extracted from the prompt."""
    id: str                       # e.g. "F-001"
    name: str                     # human-readable, e.g. "Login screen"
    description: str              # one-line description
    raw_line: str                 # the original prompt line
    category: str = "general"     # ui / data / network / system / ai / hardware
    priority: str = "normal"      # low / normal / high / critical
    template_hint: Optional[str] = None   # suggested template name
    extras: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FeatureManifest:
    """Result of parsing a prompt file."""
    source_path: Path
    title: str = "Universal Android App"
    package_name: str = "app.bardom.generated"
    app_name: str = "Generated App"
    version: str = "1.0.0"
    min_sdk: int = 21
    target_sdk: int = 34
    features: list[Feature] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source_path"] = str(self.source_path)
        d["features"] = [f.to_dict() for f in self.features]
        return d

    def to_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                        encoding="utf-8")


# --------------------------------------------------------------------------- #
# Category / template heuristics
# --------------------------------------------------------------------------- #
_CATEGORY_KEYWORDS = {
    "ui":        ["button", "screen", "page", "layout", "fragment", "activity",
                  "dialog", "menu", "toolbar", "navigation", "bottom-sheet",
                  "tab", "card", "list", "recycler", "form", "input", "field"],
    "data":      ["database", "sqlite", "room", "shared-preferences", "storage",
                  "file", "json", "csv", "cache", "model", "entity", "dao"],
    "network":   ["http", "rest", "api", "retrofit", "okhttp", "websocket",
                  "upload", "download", "firebase", "sync", "cloud"],
    "system":    ["permission", "service", "background", "notification", "alarm",
                  "boot", "widget", "foreground", "workmanager", "broadcast"],
    "ai":        ["ai", "llm", "chat", "kimi", "openrouter", "gpt", "vision",
                  "speech", "tts", "stt", "nlp", "embedding"],
    "hardware":  ["camera", "bluetooth", "gps", "location", "sensor", "accelerometer",
                  "gyroscope", "nfc", "qr", "barcode", "fingerprint", "biometric"],
}

_TEMPLATE_HINTS = {
    "webview":     ["webview", "website wrapper", "load url", "pwa"],
    "list_app":    ["list of", "recycler view", "show items"],
    "form_app":    ["form", "input fields", "submit"],
    "calculator":  ["calculator", "compute", "math"],
    "notes":       ["note", "memo", "todo", "task"],
    "qr_scanner":  ["qr", "barcode", "scan"],
    "camera_app":  ["camera", "take photo", "capture"],
    "location":    ["gps", "location", "map"],
    "chat_app":    ["chat", "messaging", "conversation"],
    "music_player":["music", "audio player", "mp3"],
    "video_player":["video", "player", "stream"],
    "auth_app":    ["login", "signup", "authentication"],
    "dashboard":   ["dashboard", "stats", "analytics"],
    "firebase_app":["firebase", "realtime database", "firestore"],
    "ai_chat":     ["ai chat", "kimi", "assistant"],
}

_PRIORITY_KEYWORDS = {
    "critical": ["must", "required", "critical", "essential", "mandatory"],
    "high":     ["should", "important", "high priority", "key feature"],
    "low":      ["optional", "nice to have", "low priority", "if possible"],
}


def _guess_category(text: str) -> str:
    t = text.lower()
    for cat, kws in _CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return cat
    return "general"


def _guess_template(text: str) -> Optional[str]:
    t = text.lower()
    for tmpl, kws in _TEMPLATE_HINTS.items():
        if any(kw in t for kw in kws):
            return tmpl
    return None


def _guess_priority(text: str) -> str:
    t = text.lower()
    for prio, kws in _PRIORITY_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return prio
    return "normal"


# --------------------------------------------------------------------------- #
# Public parser
# --------------------------------------------------------------------------- #
_META_RE = re.compile(
    r"^\s*(title|app[_ -]?name|package|version|min[_ -]?sdk|target[_ -]?sdk)\s*[:=]\s*(.+)$",
    re.IGNORECASE,
)


def parse_prompt_file(path: str | Path) -> FeatureManifest:
    """Parse a prompt file into a FeatureManifest.

    Accepts plain text or markdown. Lines starting with '#' are treated as
    section headings or app-level metadata. Blank lines separate features.
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    manifest = FeatureManifest(source_path=p, raw_text=raw)

    # 1. Extract app-level metadata from header comments
    for line in raw.splitlines():
        m = _META_RE.match(line)
        if not m:
            continue
        key = m.group(1).lower().replace(" ", "").replace("-", "").replace("_", "")
        val = m.group(2).strip().strip('"').strip("'")
        if key == "title":
            manifest.title = val
        elif key in ("appname", "app_name"):
            manifest.app_name = val
        elif key == "package":
            manifest.package_name = val
        elif key == "version":
            manifest.version = val
        elif key == "minsdk":
            try: manifest.min_sdk = int(val)
            except: pass
        elif key == "targetsdk":
            try: manifest.target_sdk = int(val)
            except: pass

    # 2. Extract feature lines (skip metadata, comments, blanks)
    feature_lines: list[str] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            # Markdown heading — treat as a feature group, but also check for metadata
            continue
        if _META_RE.match(line):
            continue
        feature_lines.append(line)

    # 3. Build Feature objects
    for idx, line in enumerate(feature_lines, start=1):
        fid = f"F-{idx:03d}"
        # Name = first 60 chars, cleaned
        name = line.split(":", 1)[0].strip() if ":" in line else line[:60]
        name = re.sub(r"\s+", " ", name)[:60]
        description = line
        category = _guess_category(line)
        template_hint = _guess_template(line)
        priority = _guess_priority(line)
        manifest.features.append(Feature(
            id=fid,
            name=name,
            description=description,
            raw_line=line,
            category=category,
            priority=priority,
            template_hint=template_hint,
        ))

    return manifest


def parse_prompt_text(text: str, source_name: str = "<inline>") -> FeatureManifest:
    """Parse a prompt given as a raw string (for the web UI / Telegram)."""
    tmp = Path("/tmp") / f"_prompt_{abs(hash(text))}.txt"
    tmp.write_text(text, encoding="utf-8")
    m = parse_prompt_file(tmp)
    m.source_path = Path(source_name)
    return m


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python prompt_parser.py <prompt-file>")
        sys.exit(1)
    m = parse_prompt_file(sys.argv[1])
    print(f"Title: {m.title}")
    print(f"Package: {m.package_name}")
    print(f"Features: {len(m.features)}")
    for f in m.features:
        print(f"  [{f.id}] ({f.category}/{f.priority}) {f.name}")
        if f.template_hint:
            print(f"        template hint: {f.template_hint}")
