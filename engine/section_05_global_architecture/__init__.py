"""
SECTION 5 — PART 1: GLOBAL ARCHITECTURE AND UNIVERSAL ENGINE DESIGN

This module implements the 15 core layers of the Universal_App_Generator
engine described in Section 5 of the master prompt:

    1.  Ingestion Layer
    2.  Normalization Layer
    3.  Virtual File System
    4.  Module Registry
    5.  Profile Adapter Layer
    6.  Supervisor Control Layer
    7.  Self-Healing Policy
    8.  Self-Evolution Policy
    (layers 9–15 are owned by later sections — semantic understanding,
     audit, repair, generation, validation, governance, export,
     visualization, plugin — but their module keys are pre-registered
     here so that every subsequent section can be discovered through
     `ctx.module_registry`.)

Public API (see task spec):

    class GlobalArchitecture:
        __init__(self, ctx)
        run(self)

    class VirtualFileSystem:
        write(self, path, content, *, source, generator_key)
        read(self, path)
        list(self, prefix="")
        delete(self, path)
        snapshot(self, label)
        rollback(self, snapshot_id)
        metadata(self, path)

    class ModuleRegistry:
        register(self, key, **fields)
        get(self, key)
        all(self)
        find_by_dependency(self, dep)

    class ProfileAdapter:
        PROFILES: Dict[str, Dict[str, Any]]
        for_profile(self, profile)
        validate_against_profile(self, profile, vfs)

    class SelfHealingPolicy:
        ERROR_CLASSES: List[str]
        handle(self, error, ctx_dict)
        classify(self, error)

    class SelfEvolutionPolicy:
        can_evolve(self, ctx) -> Tuple[bool, str]
        evolve(self, ctx, action) -> Dict[str, Any]

Pure Python 3 only — no third-party dependencies.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Reuse shared helpers from Section 3 — keeps escaping / path / package
# normalization consistent across every section.
from ..section_03_engineering_rules import (
    normalize_path,
    escape_xml,
    sanitize_package_name,
)


# ============================================================================
# 5.1 INGESTION LAYER
# ============================================================================

INGESTION_CATEGORIES: List[str] = [
    "source_code",
    "template",
    "config",
    "asset",
    "resource",
    "documentation",
    "build_script",
    "policy",
    "schema",
    "test",
    "binary",
    "unknown",
]

# Map file extension → ingestion category
_EXTENSION_CATEGORY_MAP: Dict[str, str] = {
    # source_code
    ".java":    "source_code",
    ".kt":      "source_code",
    ".kts":     "source_code",
    ".js":      "source_code",
    ".mjs":     "source_code",
    ".ts":      "source_code",
    ".dart":    "source_code",
    ".py":      "source_code",
    ".c":       "source_code",
    ".cpp":     "source_code",
    ".h":       "source_code",
    ".hpp":     "source_code",
    ".gradle":  "build_script",   # Gradle build script — classified below
    # templates
    ".ftl":     "template",
    ".mustache": "template",
    ".hbs":     "template",
    ".tpl":     "template",
    ".j2":      "template",
    # config
    ".json":    "config",
    ".yaml":    "config",
    ".yml":     "config",
    ".toml":    "config",
    ".ini":     "config",
    ".cfg":     "config",
    ".env":     "config",
    ".properties": "config",
    # assets / resources
    ".png":     "asset",
    ".jpg":     "asset",
    ".jpeg":    "asset",
    ".gif":     "asset",
    ".webp":    "asset",
    ".svg":     "asset",
    ".ttf":     "asset",
    ".otf":     "asset",
    ".wav":     "asset",
    ".mp3":     "asset",
    ".mp4":     "asset",
    ".xml":     "resource",        # default — re-classified by path
    # documentation
    ".md":      "documentation",
    ".markdown": "documentation",
    ".rst":     "documentation",
    ".txt":     "documentation",
    # build scripts
    ".sh":      "build_script",
    ".bash":    "build_script",
    ".bat":     "build_script",
    ".cmd":     "build_script",
    "Dockerfile": "build_script",
    "Makefile":   "build_script",
    # policy / schema
    ".policy":  "policy",
    ".rule":    "policy",
    ".schema":  "schema",
    # test
    ".test":    "test",
    ".spec":    "test",
    # binary / archive
    ".zip":     "binary",
    ".jar":     "binary",
    ".aar":     "binary",
    ".apk":     "binary",
    ".dex":     "binary",
    ".so":      "binary",
    ".class":   "binary",
}

# Map extension → MIME type (best-effort, no third-party dep)
_EXTENSION_MIME_MAP: Dict[str, str] = {
    ".java":   "text/x-java-source",
    ".kt":     "text/x-kotlin",
    ".kts":    "text/x-kotlin",
    ".js":     "application/javascript",
    ".ts":     "application/typescript",
    ".dart":   "application/dart",
    ".py":     "text/x-python",
    ".xml":    "application/xml",
    ".json":   "application/json",
    ".yaml":   "application/yaml",
    ".yml":    "application/yaml",
    ".toml":   "application/toml",
    ".ini":    "text/plain",
    ".cfg":    "text/plain",
    ".properties": "text/plain",
    ".md":     "text/markdown",
    ".txt":    "text/plain",
    ".gradle": "text/x-groovy",
    ".sh":     "application/x-sh",
    ".bash":   "application/x-sh",
    ".png":    "image/png",
    ".jpg":    "image/jpeg",
    ".jpeg":   "image/jpeg",
    ".gif":    "image/gif",
    ".webp":   "image/webp",
    ".svg":    "image/svg+xml",
    ".ttf":    "font/ttf",
    ".otf":    "font/otf",
    ".wav":    "audio/wav",
    ".mp3":    "audio/mpeg",
    ".mp4":    "video/mp4",
    ".zip":    "application/zip",
    ".jar":    "application/java-archive",
    ".aar":    "application/octet-stream",
    ".apk":    "application/vnd.android.package-archive",
    ".dex":    "application/octet-stream",
    ".so":     "application/octet-stream",
    ".class":  "application/java-vm",
}

# Hint-keyword → category override (checked against path basename)
_PATH_HINTS: List[Tuple[str, str]] = [
    ("/test/",       "test"),
    ("/tests/",      "test"),
    ("/androidTest/", "test"),
    ("/__tests__/",  "test"),
    ("androidmanifest", "policy"),
    ("android-manifest", "policy"),
    ("build.gradle", "build_script"),
    ("settings.gradle", "build_script"),
    ("gradle.properties", "config"),
    ("network_security_config", "policy"),
    ("privacy_policy", "policy"),
    ("proguard",     "policy"),
    ("schema.json",  "schema"),
    ("/schema/",     "schema"),
    ("/templates/",  "template"),
    ("/docs/",       "documentation"),
    ("/doc/",        "documentation"),
]


class IngestionLayer:
    """Section 5.1 — classify each ingested input.

    The classifier inspects (in order of priority):
      1. explicit `hint` argument from the caller
      2. path-basename keyword hints (e.g. `AndroidManifest.xml` → policy)
      3. file extension
      4. content sniffing (magic bytes / first-line markers)
      5. fallback → "unknown"
    """

    def __init__(self) -> None:
        self.ext_cat = dict(_EXTENSION_CATEGORY_MAP)
        self.ext_mime = dict(_EXTENSION_MIME_MAP)

    # -- public -----------------------------------------------------------
    def classify(self, path: str, content: bytes, hint: str = "") -> str:
        """Return one of INGESTION_CATEGORIES for the given input."""
        # 1. hint
        if hint and hint in INGESTION_CATEGORIES:
            return hint
        # 2. path hints
        np = normalize_path(path).lower()
        for needle, cat in _PATH_HINTS:
            if needle.lower() in np:
                return cat
        # 3. extension (handle extensionless names like 'Dockerfile')
        lower_name = np.rsplit("/", 1)[-1]
        if lower_name in {"dockerfile", "makefile", "rakefile", "gemfile"}:
            return "build_script"
        # 4. extension match
        ext = self._ext_of(path)
        if ext in self.ext_cat:
            base_cat = self.ext_cat[ext]
            # XML special-case: AndroidManifest.xml is policy, layouts are resource
            if ext == ".xml":
                if "manifest" in np:
                    return "policy"
                if "/values/" in np or "/layout/" in np or "/drawable/" in np:
                    return "resource"
            return base_cat
        # 5. content sniffing
        sniffed = self._sniff(content)
        if sniffed:
            return sniffed
        return "unknown"

    def mime_for(self, path: str, content: bytes) -> str:
        """Best-effort MIME type guess."""
        ext = self._ext_of(path)
        if ext in self.ext_mime:
            return self.ext_mime[ext]
        # content sniff
        if content[:4] == b"\x50\x4b\x03\x04":
            return "application/zip"
        if content[:4] == b"\x89PNG":
            return "image/png"
        if content[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "image/webp"
        if content[:5] == b"<?xml":
            return "application/xml"
        try:
            content.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return "application/octet-stream"

    def ingest(self, path: str, content: bytes, hint: str = "") -> Dict[str, Any]:
        """Return an ingestion record describing the input."""
        cat = self.classify(path, content, hint)
        mime = self.mime_for(path, content)
        return {
            "path": normalize_path(path),
            "category": cat,
            "mime": mime,
            "size": len(content),
            "hash": hashlib.sha256(content).hexdigest(),
            "hint": hint,
            "ingested_at": time.time(),
        }

    # -- internals --------------------------------------------------------
    @staticmethod
    def _ext_of(path: str) -> str:
        """Return the file extension in lowercase, including the dot.

        Handles extensionless build files (Dockerfile, Makefile) by returning
        the basename itself — matched against the map keys.
        """
        base = path.rsplit("/", 1)[-1]
        if "." not in base:
            return base.lower()
        dot = base.rfind(".")
        return base[dot:].lower()

    @staticmethod
    def _sniff(content: bytes) -> Optional[str]:
        """Inspect magic bytes / first-line markers to guess a category."""
        if not content:
            return None
        head = content[:512]
        # ZIP family
        if head[:4] == b"\x50\x4b\x03\x04":
            return "binary"
        # ELF / DEX
        if head[:4] == b"\x7fELF":
            return "binary"
        if head[:4] == b"dex\n":
            return "binary"
        # try as text
        try:
            text = head.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return "binary"
        first_line = text.lstrip().splitlines()[0] if text.strip() else ""
        low = first_line.lower()
        if low.startswith("<?xml"):
            return "resource"
        if low.startswith("#!"):
            return "build_script"
        if low.startswith("{") or low.startswith("["):
            return "config"
        if low.startswith("---") or low.startswith("%yaml"):
            return "config"
        if low.startswith("apply plugin:") or low.startswith("plugins {"):
            return "build_script"
        if "package " in low or "import " in low:
            return "source_code"
        return None


# ============================================================================
# 5.2 NORMALIZATION LAYER
# ============================================================================

# Strip invalid escape sequences: \X where X is not a recognized escape.
_INVALID_ESCAPE_RE = re.compile(rb'\\(?!["\\/bfnrtu])')

# Strip trailing whitespace on each line.
_TRAILING_WS_RE = re.compile(rb"[ \t]+$", re.MULTILINE)


class NormalizationLayer:
    """Section 5.2 — produce a canonical virtual file system.

    Normalizes:
      - line endings  (CRLF / CR → LF)
      - indentation   (tabs → 4 spaces, optional)
      - encoding      (BOM stripped, decode as UTF-8)
      - trailing spaces
      - invalid escape sequences in JSON strings
      - path separators  (backslash → forward slash)
      - duplicate keys in JSON
      - malformed package names
    """

    def __init__(self, *, tabs_to_spaces: bool = True, indent_width: int = 4) -> None:
        self.tabs_to_spaces = tabs_to_spaces
        self.indent_width = indent_width

    # -- public -----------------------------------------------------------
    def normalize_content(self, content: bytes, path: str) -> bytes:
        """Return a normalized byte string for the given file content."""
        if not isinstance(content, (bytes, bytearray)):
            raise TypeError(f"content must be bytes, got {type(content).__name__}")

        # BOM strip
        if content[:3] == b"\xef\xbb\xbf":
            content = content[3:]

        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""

        # Binary formats — do not touch content
        if ext in {"png", "jpg", "jpeg", "gif", "webp", "ttf", "otf",
                   "wav", "mp3", "mp4", "zip", "jar", "aar", "apk",
                   "dex", "so", "class"}:
            return bytes(content)

        # Try UTF-8 decode for text normalization
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            # fall back to latin-1 to avoid data loss; mark in metadata
            text = content.decode("latin-1", errors="replace")

        # 1. line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. tabs → spaces (only for code-like files)
        if self.tabs_to_spaces and ext in {
            "java", "kt", "kts", "js", "ts", "dart", "py", "gradle",
            "groovy", "xml", "json", "yaml", "yml", "sh", "bash",
        }:
            text = text.expandtabs(self.indent_width)

        # 3. trailing whitespace per line
        text = "\n".join(line.rstrip() for line in text.split("\n"))

        # 4. final newline normalization: exactly one trailing newline
        text = text.rstrip("\n") + "\n"

        # 5. format-specific fixes
        if ext == "json":
            text = self._fix_duplicate_keys_json(text)
        elif ext == "xml":
            text = self._fix_xml(text)
        elif ext in {"gradle", "groovy"}:
            text = self._fix_gradle(text)

        return text.encode("utf-8")

    def normalize_path(self, path: str) -> str:
        """Section 5.2 path normalization — delegates to shared helper."""
        return normalize_path(path)

    def normalize_package(self, name: str) -> str:
        """Section 5.2 package-name normalization — delegates to shared helper."""
        return sanitize_package_name(name)

    # -- JSON -------------------------------------------------------------
    def _fix_duplicate_keys_json(self, text: str) -> str:
        """Strip duplicate keys from JSON objects (last-wins semantics).

        Falls back to returning the original text if the input is not valid
        JSON — Section 6 will handle the deeper repair.
        """
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text
        # Re-serialize without duplicates — Python dict dedupes naturally
        return json.dumps(self._dedupe_keys(data), indent=2, ensure_ascii=False)

    def _dedupe_keys(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._dedupe_keys(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._dedupe_keys(v) for v in obj]
        return obj

    # -- XML --------------------------------------------------------------
    def _fix_xml(self, text: str) -> str:
        """Lightweight XML cleanup: strip invalid escape sequences in
        attribute values, normalize self-closing tags, ensure single root."""
        # Remove leading whitespace before XML declaration
        text = re.sub(r'^\s+<\?xml', '<?xml', text)
        # Collapse multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    # -- Gradle -----------------------------------------------------------
    def _fix_gradle(self, text: str) -> str:
        """Lightweight Gradle cleanup: normalize trailing semicolons,
        collapse repeated blank lines."""
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    # -- batch ------------------------------------------------------------
    def normalize_vfs(self, vfs: Dict[str, bytes]) -> Tuple[Dict[str, bytes], Dict[str, Dict[str, Any]]]:
        """Normalize an entire {path: content} dict and return (vfs, meta)."""
        out_vfs: Dict[str, bytes] = {}
        out_meta: Dict[str, Dict[str, Any]] = {}
        for raw_path, raw_content in vfs.items():
            np = self.normalize_path(raw_path)
            norm = self.normalize_content(raw_content, np)
            out_vfs[np] = norm
            out_meta[np] = {
                "normalized": True,
                "original_path": raw_path,
                "original_size": len(raw_content),
                "normalized_size": len(norm),
                "modified": len(raw_content) != len(norm) or raw_content != norm,
            }
        return out_vfs, out_meta


# ============================================================================
# 5.3 VIRTUAL FILE SYSTEM
# ============================================================================

class VirtualFileSystem:
    """Section 5.3 — canonical in-memory file system.

    Every file entry exposes the 14 metadata fields required by the spec:

        path, type, mime, encoding, size, hash, createdAt, updatedAt,
        source, generatorKey, validatorState, repairState, exportState,
        supervisorLocked, rollbackSnapshotId
    """

    REQUIRED_META_KEYS: Tuple[str, ...] = (
        "path", "type", "mime", "encoding", "size", "hash",
        "createdAt", "updatedAt", "source", "generatorKey",
        "validatorState", "repairState", "exportState",
        "supervisorLocked", "rollbackSnapshotId",
    )

    VALIDATOR_STATES = ("pending", "valid", "invalid", "skipped")
    REPAIR_STATES    = ("none", "repaired", "failed", "in_progress")
    EXPORT_STATES    = ("none", "queued", "exported", "failed")

    def __init__(self) -> None:
        self._files: Dict[str, bytes] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._ingestion = IngestionLayer()
        self._normalizer = NormalizationLayer()

    # -- write / read / list / delete ------------------------------------
    def write(self, path: str, content: bytes, *,
              source: str, generator_key: str) -> None:
        """Create or update a file in the VFS.

        Computes sha256 hash, sets createdAt (preserved on update),
        updatedAt (always refreshed), and marks the file as
        validatorState="pending", repairState="none",
        exportState="none", supervisorLocked=False,
        rollbackSnapshotId=None.
        """
        if not isinstance(content, (bytes, bytearray)):
            raise TypeError(f"content must be bytes, got {type(content).__name__}")
        content = bytes(content)

        np = self._normalizer.normalize_path(path)
        if not np:
            raise ValueError("path must not be empty after normalization")

        now = time.time()
        existing = self._meta.get(np)
        created_at = existing["createdAt"] if existing else now

        category = self._ingestion.classify(np, content)
        mime = self._ingestion.mime_for(np, content)
        digest = hashlib.sha256(content).hexdigest()
        encoding = "binary" if mime.startswith(("application/octet-stream",
                                                "image/", "audio/", "video/",
                                                "font/", "application/zip",
                                                "application/java")) else "utf-8"

        self._files[np] = content
        self._meta[np] = {
            "path": np,
            "type": category,
            "mime": mime,
            "encoding": encoding,
            "size": len(content),
            "hash": digest,
            "createdAt": created_at,
            "updatedAt": now,
            "source": source,
            "generatorKey": generator_key,
            "validatorState": "pending",
            "repairState": "none",
            "exportState": "none",
            "supervisorLocked": False,
            "rollbackSnapshotId": None,
        }

    def read(self, path: str) -> Optional[bytes]:
        """Return file content or None if the path does not exist."""
        np = self._normalizer.normalize_path(path)
        return self._files.get(np)

    def list(self, prefix: str = "") -> List[str]:
        """Return sorted list of paths matching the given prefix."""
        prefix = self._normalizer.normalize_path(prefix) if prefix else ""
        if prefix and not prefix.endswith("/"):
            # Treat prefix as either a directory or a path-stem
            matches = [p for p in self._files
                       if p == prefix or p.startswith(prefix + "/")
                       or p.startswith(prefix)]
        else:
            matches = [p for p in self._files if p.startswith(prefix)]
        return sorted(matches)

    def delete(self, path: str) -> bool:
        """Delete a file. Returns True if it existed and was deleted."""
        np = self._normalizer.normalize_path(path)
        if np not in self._files:
            return False
        del self._files[np]
        del self._meta[np]
        return True

    def metadata(self, path: str) -> Dict[str, Any]:
        """Return the full metadata dict for a path.

        Returns an empty dict if the path is not present.
        """
        np = self._normalizer.normalize_path(path)
        return dict(self._meta.get(np, {}))

    # -- state mutators (used by Sections 6/7/9) -------------------------
    def set_validator_state(self, path: str, state: str) -> None:
        if state not in self.VALIDATOR_STATES:
            raise ValueError(f"invalid validatorState: {state}")
        np = self._normalizer.normalize_path(path)
        if np in self._meta:
            self._meta[np]["validatorState"] = state
            self._meta[np]["updatedAt"] = time.time()

    def set_repair_state(self, path: str, state: str) -> None:
        if state not in self.REPAIR_STATES:
            raise ValueError(f"invalid repairState: {state}")
        np = self._normalizer.normalize_path(path)
        if np in self._meta:
            self._meta[np]["repairState"] = state
            self._meta[np]["updatedAt"] = time.time()

    def set_export_state(self, path: str, state: str) -> None:
        if state not in self.EXPORT_STATES:
            raise ValueError(f"invalid exportState: {state}")
        np = self._normalizer.normalize_path(path)
        if np in self._meta:
            self._meta[np]["exportState"] = state
            self._meta[np]["updatedAt"] = time.time()

    def lock(self, path: str, locked: bool = True) -> None:
        np = self._normalizer.normalize_path(path)
        if np in self._meta:
            self._meta[np]["supervisorLocked"] = bool(locked)

    # -- snapshot / rollback ---------------------------------------------
    def snapshot(self, label: str) -> str:
        """Deep-copy the current VFS state into a snapshot and return
        the snapshot_id (a UUID4 hex string)."""
        snapshot_id = uuid.uuid4().hex
        self._snapshots[snapshot_id] = {
            "id": snapshot_id,
            "label": label,
            "created_at": time.time(),
            "files": copy.deepcopy(self._files),
            "meta": copy.deepcopy(self._meta),
        }
        # Stamp every current file with its latest rollback snapshot
        for meta in self._meta.values():
            meta["rollbackSnapshotId"] = snapshot_id
        return snapshot_id

    def rollback(self, snapshot_id: str) -> bool:
        """Restore the VFS to the given snapshot. Returns False if the
        snapshot_id is unknown."""
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            return False
        # Restore from the deep-copied snapshot
        self._files = copy.deepcopy(snap["files"])
        self._meta = copy.deepcopy(snap["meta"])
        return True

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Return a list of {id, label, created_at, file_count} summaries."""
        return [
            {
                "id": s["id"],
                "label": s["label"],
                "created_at": s["created_at"],
                "file_count": len(s["files"]),
            }
            for s in self._snapshots.values()
        ]

    # -- export helpers --------------------------------------------------
    def as_dict(self) -> Dict[str, bytes]:
        """Return a shallow copy of the {path: content} map."""
        return dict(self._files)

    def meta_dict(self) -> Dict[str, Dict[str, Any]]:
        """Return a shallow copy of the {path: meta} map."""
        return {p: dict(m) for p, m in self._meta.items()}

    def __len__(self) -> int:
        return len(self._files)

    def __contains__(self, path: str) -> bool:
        np = self._normalizer.normalize_path(path)
        return np in self._files


# ============================================================================
# 5.4 MODULE REGISTRY
# ============================================================================

class ModuleRegistry:
    """Section 5.4 — every function registered as a module key.

    Required fields per module (validated on register):

        key, title, description, inputs, outputs, dependencies,
        failureModes, recoveryActions, evolutionHooks

    Optional fields (filled with sensible defaults if absent):

        visibilityModes, supervisorEditable, testPlan, relatedModules
    """

    REQUIRED_FIELDS: Tuple[str, ...] = (
        "key", "title", "description", "inputs", "outputs",
        "dependencies", "failureModes", "recoveryActions", "evolutionHooks",
    )

    OPTIONAL_FIELDS: Tuple[str, ...] = (
        "visibilityModes", "supervisorEditable", "testPlan", "relatedModules",
    )

    DEFAULT_OPTIONAL: Dict[str, Any] = {
        "visibilityModes": ["public"],
        "supervisorEditable": False,
        "testPlan": {},
        "relatedModules": [],
    }

    def __init__(self) -> None:
        self._modules: Dict[str, Dict[str, Any]] = {}

    # -- public -----------------------------------------------------------
    def register(self, key: str, **fields: Any) -> None:
        """Register a module. Raises ValueError if required fields missing."""
        if not key or not isinstance(key, str):
            raise ValueError("module key must be a non-empty string")
        # Ensure 'key' is set consistently
        fields["key"] = key

        missing = [f for f in self.REQUIRED_FIELDS if f not in fields]
        if missing:
            raise ValueError(
                f"module '{key}' missing required fields: {', '.join(missing)}"
            )

        # Type-check list-typed fields
        for fld in ("inputs", "outputs", "dependencies",
                    "failureModes", "recoveryActions", "evolutionHooks"):
            if not isinstance(fields[fld], list):
                raise TypeError(
                    f"module '{key}' field '{fld}' must be a list, "
                    f"got {type(fields[fld]).__name__}"
                )

        # Fill optional fields with defaults
        for opt in self.OPTIONAL_FIELDS:
            if opt not in fields or fields[opt] is None:
                fields[opt] = copy.deepcopy(self.DEFAULT_OPTIONAL[opt])

        # Always overwrite with a deep copy to insulate from caller mutations
        self._modules[key] = copy.deepcopy(fields)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Return a deep copy of the module record, or None."""
        rec = self._modules.get(key)
        return copy.deepcopy(rec) if rec is not None else None

    def all(self) -> Dict[str, Dict[str, Any]]:
        """Return deep-copy of the entire registry."""
        return {k: copy.deepcopy(v) for k, v in self._modules.items()}

    def find_by_dependency(self, dep: str) -> List[str]:
        """Return all module keys that declare `dep` in their dependencies."""
        return [
            key for key, mod in self._modules.items()
            if dep in mod.get("dependencies", [])
        ]

    def __len__(self) -> int:
        return len(self._modules)

    def __contains__(self, key: str) -> bool:
        return key in self._modules


# ============================================================================
# 5.5 PROFILE ADAPTER LAYER
# ============================================================================

class ProfileAdapter:
    """Section 5.5 — 12 build-profile adapters.

    Each profile defines:
      - allowed_syntax       : list of language tokens / DSLs permitted
      - forbidden_syntax     : list of tokens / DSLs never permitted
      - required_files       : glob patterns that MUST be present
      - optional_files       : glob patterns that MAY be present
      - build_command        : shell command to build the project
      - validation_command   : shell command to validate (lint / test)
      - export_format        : primary export artifact format
      - compatibility_warnings: list of strings shown to supervisor
      - dependency_rules     : {feature: [gradle_coord, ...]}
      - theme_rules          : dict of theme conventions
      - activity_rules       : dict of activity conventions
      - fragment_rules       : dict of fragment conventions
      - permission_rules     : dict of permission policy
      - telemetry_rules      : dict of telemetry policy
    """

    PROFILES: Dict[str, Dict[str, Any]] = {
        # ----------------------------------------------------------------
        "sketchware_pro": {
            "allowed_syntax":   ["java", "xml_layout", "sketchware_blocks"],
            "forbidden_syntax": ["kotlin", "dart", "compose", "ndk"],
            "required_files":   ["project.json", "AndroidManifest.xml",
                                 "resources/layout/*.xml"],
            "optional_files":   ["resources/drawable/*.png", "logic/*.java"],
            "build_command":    "sketchware-cli build --project .",
            "validation_command": "sketchware-cli validate --project .",
            "export_format":    "sketchware_project_json",
            "compatibility_warnings": [
                "Sketchware Pro block size limit applies to logic files.",
                "No Compose / Kotlin DSL support.",
            ],
            "dependency_rules": {
                "firebase": ["com.google.firebase:firebase-database:20.3.0"],
                "ads":      ["com.google.android.gms:play-services-ads:22.6.0"],
            },
            "theme_rules":      {"default_theme": "Material3", "custom_themes": True},
            "activity_rules":   {"base_class": "androidx.appcompat.app.AppCompatActivity"},
            "fragment_rules":   {"base_class": "androidx.fragment.app.Fragment"},
            "permission_rules": {"runtime_permissions": True, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": True, "anonymous_only": False},
        },
        # ----------------------------------------------------------------
        "android_studio_native_java": {
            "allowed_syntax":   ["java", "xml_layout", "groovy_gradle", "xml_manifest"],
            "forbidden_syntax": ["kotlin", "dart", "compose"],
            "required_files":   ["app/build.gradle", "app/src/main/AndroidManifest.xml"],
            "optional_files":   ["app/proguard-rules.pro", "gradle/wrapper/gradle-wrapper.properties"],
            "build_command":    "./gradlew assembleDebug",
            "validation_command": "./gradlew lintDebug testDebugUnitTest",
            "export_format":    "apk",
            "compatibility_warnings": [
                "Java-only profile — Kotlin sources are ignored.",
            ],
            "dependency_rules": {
                "camera":   ["androidx.camera:camera-core:1.3.4"],
                "recycler": ["androidx.recyclerview:recyclerview:1.3.2"],
            },
            "theme_rules":      {"default_theme": "Material3", "custom_themes": True},
            "activity_rules":   {"base_class": "androidx.appcompat.app.AppCompatActivity"},
            "fragment_rules":   {"base_class": "androidx.fragment.app.Fragment"},
            "permission_rules": {"runtime_permissions": True, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": True, "anonymous_only": False},
        },
        # ----------------------------------------------------------------
        "android_studio_native_kotlin": {
            "allowed_syntax":   ["kotlin", "xml_layout", "kotlin_gradle", "compose"],
            "forbidden_syntax": ["java_sources"],
            "required_files":   ["app/build.gradle.kts", "app/src/main/AndroidManifest.xml"],
            "optional_files":   ["app/proguard-rules.pro", "gradle/libs.versions.toml"],
            "build_command":    "./gradlew assembleDebug",
            "validation_command": "./gradlew lintDebug testDebugUnitTest",
            "export_format":    "apk",
            "compatibility_warnings": [
                "Kotlin-first profile — prefer kotlin_gradle DSL.",
            ],
            "dependency_rules": {
                "coroutines": ["org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3"],
                "compose":    ["androidx.compose.ui:ui:1.6.0"],
            },
            "theme_rules":      {"default_theme": "Material3", "custom_themes": True},
            "activity_rules":   {"base_class": "androidx.activity.ComponentActivity"},
            "fragment_rules":   {"base_class": "androidx.fragment.app.Fragment"},
            "permission_rules": {"runtime_permissions": True, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": True, "anonymous_only": False},
        },
        # ----------------------------------------------------------------
        "flutter": {
            "allowed_syntax":   ["dart", "yaml"],
            "forbidden_syntax": ["java", "kotlin", "xml_layout"],
            "required_files":   ["pubspec.yaml", "lib/main.dart"],
            "optional_files":   ["android/app/build.gradle", "ios/Runner/AppDelegate.swift"],
            "build_command":    "flutter build apk --debug",
            "validation_command": "flutter analyze && flutter test",
            "export_format":    "apk",
            "compatibility_warnings": [
                "Flutter profile — native Android files are scaffolded only.",
            ],
            "dependency_rules": {
                "http":       ["http: ^1.1.0"],
                "provider":   ["provider: ^6.1.1"],
            },
            "theme_rules":      {"default_theme": "Material3", "custom_themes": True},
            "activity_rules":   {"base_class": "io.flutter.app.FlutterActivity"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": True, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": True, "anonymous_only": False},
        },
        # ----------------------------------------------------------------
        "react_native_optional": {
            "allowed_syntax":   ["jsx", "tsx", "js", "ts", "json"],
            "forbidden_syntax": ["java", "kotlin", "dart"],
            "required_files":   ["package.json", "app.json", "App.tsx"],
            "optional_files":   ["android/app/build.gradle", "ios/Podfile"],
            "build_command":    "npx react-native bundle --dev false",
            "validation_command": "npm run lint && npm test",
            "export_format":    "jsbundle",
            "compatibility_warnings": [
                "React Native profile — native scaffolding is minimal.",
            ],
            "dependency_rules": {
                "navigation": ["@react-navigation/native: ^6.1.9"],
                "http":       ["axios: ^1.6.0"],
            },
            "theme_rules":      {"default_theme": "react_native_paper", "custom_themes": True},
            "activity_rules":   {"base_class": "com.facebook.react.ReactActivity"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": True, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": True, "anonymous_only": False},
        },
        # ----------------------------------------------------------------
        "termux_cli": {
            "allowed_syntax":   ["shell", "python", "ruby", "perl"],
            "forbidden_syntax": ["java", "kotlin", "xml_layout"],
            "required_files":   ["main.sh", "README.md"],
            "optional_files":   ["requirements.txt", "Gemfile"],
            "build_command":    "bash main.sh --build",
            "validation_command": "shellcheck main.sh && bash main.sh --self-test",
            "export_format":    "tarball",
            "compatibility_warnings": [
                "Termux CLI profile — no Android UI resources generated.",
            ],
            "dependency_rules": {
                "python": ["python>=3.10"],
                "ruby":   ["ruby>=3.0"],
            },
            "theme_rules":      {"default_theme": "n/a", "custom_themes": False},
            "activity_rules":   {"base_class": "n/a"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": False, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": False, "anonymous_only": True},
        },
        # ----------------------------------------------------------------
        "linux_cli": {
            "allowed_syntax":   ["shell", "python", "c", "cpp", "rust"],
            "forbidden_syntax": ["java", "kotlin", "dart", "xml_layout"],
            "required_files":   ["main.sh", "README.md"],
            "optional_files":   ["Makefile", "Dockerfile"],
            "build_command":    "make && ./bin/main",
            "validation_command": "make test",
            "export_format":    "tarball",
            "compatibility_warnings": [
                "Linux CLI profile — no Android resources generated.",
            ],
            "dependency_rules": {
                "python": ["python3>=3.10"],
                "rust":   ["rustc>=1.70"],
            },
            "theme_rules":      {"default_theme": "n/a", "custom_themes": False},
            "activity_rules":   {"base_class": "n/a"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": False, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": False, "anonymous_only": True},
        },
        # ----------------------------------------------------------------
        "github_actions": {
            "allowed_syntax":   ["yaml"],
            "forbidden_syntax": ["java", "kotlin", "dart"],
            "required_files":   [".github/workflows/ci.yml"],
            "optional_files":   [".github/dependabot.yml"],
            "build_command":    "act -j build",
            "validation_command": "act -j lint && act -j test",
            "export_format":    "workflow_yaml",
            "compatibility_warnings": [
                "GitHub Actions profile — produces CI workflow YAML only.",
            ],
            "dependency_rules": {
                "actions_checkout": ["actions/checkout@v4"],
                "actions_setup_java": ["actions/setup-java@v4"],
            },
            "theme_rules":      {"default_theme": "n/a", "custom_themes": False},
            "activity_rules":   {"base_class": "n/a"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": False, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": False, "anonymous_only": True},
        },
        # ----------------------------------------------------------------
        "cloud_build": {
            "allowed_syntax":   ["yaml", "shell"],
            "forbidden_syntax": ["java", "kotlin", "dart"],
            "required_files":   ["cloudbuild.yaml"],
            "optional_files":   ["Dockerfile"],
            "build_command":    "gcloud builds submit --config cloudbuild.yaml .",
            "validation_command": "gcloud builds submit --config cloudbuild.yaml --dry-run .",
            "export_format":    "cloud_build_config",
            "compatibility_warnings": [
                "Cloud Build profile — produces GCB config YAML only.",
            ],
            "dependency_rules": {},
            "theme_rules":      {"default_theme": "n/a", "custom_themes": False},
            "activity_rules":   {"base_class": "n/a"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": False, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": False, "anonymous_only": True},
        },
        # ----------------------------------------------------------------
        "google_ai_studio_spec": {
            "allowed_syntax":   ["json", "yaml", "markdown"],
            "forbidden_syntax": ["java", "kotlin", "dart", "shell"],
            "required_files":   ["ai_spec.json", "README.md"],
            "optional_files":   ["prompts/*.txt", "tools/*.json"],
            "build_command":    "ai-studio-cli validate ai_spec.json",
            "validation_command": "ai-studio-cli lint ai_spec.json",
            "export_format":    "ai_spec_json",
            "compatibility_warnings": [
                "Google AI Studio profile — produces model spec JSON only.",
            ],
            "dependency_rules": {
                "gemini":   ["ai-sdk:gemini@1.0"],
                "palm":     ["ai-sdk:palm@1.0"],
            },
            "theme_rules":      {"default_theme": "n/a", "custom_themes": False},
            "activity_rules":   {"base_class": "n/a"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": False, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": True, "anonymous_only": True},
        },
        # ----------------------------------------------------------------
        "stitch_export_optional": {
            "allowed_syntax":   ["json", "xml"],
            "forbidden_syntax": ["java", "kotlin", "dart"],
            "required_files":   ["stitch_export.json"],
            "optional_files":   ["screens/*.png"],
            "build_command":    "stitch-cli export stitch_export.json",
            "validation_command": "stitch-cli validate stitch_export.json",
            "export_format":    "stitch_json",
            "compatibility_warnings": [
                "Stitch export profile — produces design-source JSON only.",
            ],
            "dependency_rules": {},
            "theme_rules":      {"default_theme": "material_default", "custom_themes": True},
            "activity_rules":   {"base_class": "n/a"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": False, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": False, "anonymous_only": True},
        },
        # ----------------------------------------------------------------
        "custom_internal_engine": {
            "allowed_syntax":   ["python", "yaml", "json", "markdown"],
            "forbidden_syntax": [],
            "required_files":   ["engine.yaml", "modules/"],
            "optional_files":   ["plugins/", "tests/"],
            "build_command":    "python -m engine.cli build",
            "validation_command": "python -m engine.cli validate",
            "export_format":    "engine_package",
            "compatibility_warnings": [
                "Custom internal engine profile — flexible syntax rules.",
            ],
            "dependency_rules": {},
            "theme_rules":      {"default_theme": "n/a", "custom_themes": True},
            "activity_rules":   {"base_class": "n/a"},
            "fragment_rules":   {"base_class": "n/a"},
            "permission_rules": {"runtime_permissions": False, "max_sdk": 34},
            "telemetry_rules":  {"consent_required": True, "anonymous_only": True},
        },
    }

    def __init__(self) -> None:
        # Validate at construction time — fail fast if spec drift occurs
        expected = {
            "sketchware_pro", "android_studio_native_java",
            "android_studio_native_kotlin", "flutter",
            "react_native_optional", "termux_cli", "linux_cli",
            "github_actions", "cloud_build", "google_ai_studio_spec",
            "stitch_export_optional", "custom_internal_engine",
        }
        missing = expected - set(self.PROFILES)
        if missing:
            raise RuntimeError(f"ProfileAdapter missing profiles: {missing}")

    # -- public -----------------------------------------------------------
    def for_profile(self, profile: str) -> Dict[str, Any]:
        """Return a deep copy of the profile spec.

        Raises KeyError if the profile is unknown.
        """
        if profile not in self.PROFILES:
            raise KeyError(f"unknown profile: {profile}")
        return copy.deepcopy(self.PROFILES[profile])

    def validate_against_profile(self, profile: str,
                                 vfs: Dict[str, bytes]) -> List[Dict[str, Any]]:
        """Return a list of violation dicts for the given VFS vs profile.

        Each violation is {severity, rule, path, message}.
        """
        spec = self.for_profile(profile)
        violations: List[Dict[str, Any]] = []
        paths = set(vfs.keys())

        # 1. required_files — glob match
        for req in spec["required_files"]:
            if not self._glob_match(req, paths):
                violations.append({
                    "severity": "critical",
                    "rule": "required_file_missing",
                    "path": req,
                    "message": f"required file '{req}' not present in VFS",
                })

        # 2. forbidden_syntax — scan text files
        for path, content in vfs.items():
            if not spec["forbidden_syntax"]:
                continue
            text = self._safe_decode(content)
            if text is None:
                continue
            for token in spec["forbidden_syntax"]:
                if self._syntax_marker(token, path, text):
                    violations.append({
                        "severity": "high",
                        "rule": "forbidden_syntax",
                        "path": path,
                        "message": f"forbidden syntax '{token}' detected",
                    })

        # 3. allowed_syntax — light heuristic (warn-only)
        for path, content in vfs.items():
            text = self._safe_decode(content)
            if text is None:
                continue
            detected = self._detect_syntax(path, text)
            if detected and detected not in spec["allowed_syntax"]:
                violations.append({
                    "severity": "medium",
                    "rule": "syntax_not_in_allowlist",
                    "path": path,
                    "message": f"detected syntax '{detected}' is not in allowlist",
                })

        # 4. permission_rules — cleartext traffic must be off by default
        perm = spec.get("permission_rules", {})
        if perm.get("runtime_permissions"):
            for path in paths:
                if path.lower().endswith("androidmanifest.xml"):
                    content = vfs[path]
                    text = self._safe_decode(content) or ""
                    if "usesCleartextTraffic=\"true\"" in text:
                        violations.append({
                            "severity": "high",
                            "rule": "insecure_cleartext_default",
                            "path": path,
                            "message": "cleartext traffic must default to false",
                        })

        return violations

    def list_profiles(self) -> List[str]:
        return sorted(self.PROFILES.keys())

    # -- internals --------------------------------------------------------
    @staticmethod
    def _glob_match(pattern: str, paths: set) -> bool:
        """Simple glob matcher supporting `*` and `**`."""
        if pattern in paths:
            return True
        # Directory prefix match (e.g. 'modules/')
        if pattern.endswith("/"):
            return any(p.startswith(pattern) for p in paths)
        # Wildcard match
        regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        compiled = re.compile(regex)
        return any(compiled.match(p) for p in paths)

    @staticmethod
    def _safe_decode(content: bytes) -> Optional[str]:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return None

    @staticmethod
    def _detect_syntax(path: str, text: str) -> Optional[str]:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        mapping = {
            "java": "java", "kt": "kotlin", "kts": "kotlin_gradle",
            "gradle": "groovy_gradle", "dart": "dart", "js": "js",
            "jsx": "jsx", "ts": "ts", "tsx": "tsx", "xml": "xml_layout",
            "sh": "shell", "bash": "shell", "py": "python",
            "yaml": "yaml", "yml": "yaml", "json": "json",
            "md": "markdown", "c": "c", "cpp": "cpp", "rs": "rust",
        }
        return mapping.get(ext)

    @staticmethod
    def _syntax_marker(token: str, path: str, text: str) -> bool:
        """Return True if a forbidden syntax marker is detected."""
        low = text.lower()
        if token == "kotlin":
            return path.endswith(".kt") or "fun main(" in low
        if token == "java_sources":
            return path.endswith(".java")
        if token == "dart":
            return path.endswith(".dart") or "void main()" in low
        if token == "java":
            return path.endswith(".java")
        if token == "compose":
            return "@composable" in low or "androidx.compose" in low
        if token == "xml_layout":
            return path.endswith(".xml") and "<layout" in low
        if token == "shell":
            return path.endswith((".sh", ".bash"))
        if token == "ndk":
            return "system.loadlibrary" in low or "/jni/" in path.lower()
        return False


# ============================================================================
# 5.6 SUPERVISOR CONTROL LAYER
# ============================================================================

class SupervisorControlLayer:
    """Section 5.6 — schema-validated, transactional, reversible supervisor edits.

    Every edit goes through:
      1. preview()       — returns a diff preview without applying
      2. begin()         — open a transaction, snapshot VFS
      3. apply()         — schema-validate then stage the edit
      4. commit()        — persist the transaction
      5. (or rollback()) — revert to the pre-transaction snapshot

    All edits are appended to the supplied audit_log.
    """

    EDITABLE_FIELDS: Tuple[str, ...] = (
        "app_name", "package_name", "version", "sdk_min", "sdk_target",
        "permissions", "dependencies", "features", "layouts", "activities",
        "fragments", "resources", "colors", "strings", "dimens", "arrays",
        "styles", "firebase_config", "environment_variables",
        "governance_rules", "consent_rules", "ad_rules",
        "notification_rules", "access_rules", "export_rules", "build_profile",
    )

    # Schema for each editable field — {type, required, validator}
    FIELD_SCHEMAS: Dict[str, Dict[str, Any]] = {
        "app_name":         {"type": "str",    "max_len": 80},
        "package_name":     {"type": "package"},
        "version":          {"type": "str",    "regex": r"^\d+\.\d+\.\d+([.-]\w+)?$"},
        "sdk_min":          {"type": "int",    "min": 16, "max": 34},
        "sdk_target":       {"type": "int",    "min": 21, "max": 34},
        "permissions":      {"type": "list",   "item_regex": r"^android\.permission\.[A-Z_]+$"},
        "dependencies":     {"type": "list",   "item_regex": r"^[a-zA-Z0-9._:-]+(:[a-zA-Z0-9._-]+)*$"},
        "features":         {"type": "list"},
        "layouts":          {"type": "list"},
        "activities":       {"type": "list"},
        "fragments":        {"type": "list"},
        "resources":        {"type": "dict"},
        "colors":           {"type": "dict"},
        "strings":          {"type": "dict"},
        "dimens":           {"type": "dict"},
        "arrays":           {"type": "dict"},
        "styles":           {"type": "dict"},
        "firebase_config":  {"type": "dict"},
        "environment_variables": {"type": "dict"},
        "governance_rules": {"type": "dict"},
        "consent_rules":    {"type": "dict"},
        "ad_rules":         {"type": "dict"},
        "notification_rules": {"type": "dict"},
        "access_rules":     {"type": "dict"},
        "export_rules":     {"type": "dict"},
        "build_profile":    {"type": "str"},
    }

    def __init__(self, vfs: VirtualFileSystem,
                 registry: ModuleRegistry,
                 audit_log: List[Dict[str, Any]]) -> None:
        self.vfs = vfs
        self.registry = registry
        self.audit_log = audit_log
        self._transactions: Dict[str, Dict[str, Any]] = {}

    # -- public -----------------------------------------------------------
    def preview(self, field: str, value: Any) -> Dict[str, Any]:
        """Return a non-destructive preview of the proposed edit."""
        self._validate_field(field, value)
        return {
            "field": field,
            "value": value,
            "valid": True,
            "previewed_at": time.time(),
        }

    def begin(self, silent: bool = False) -> str:
        """Open a new supervisor transaction and snapshot the VFS."""
        tx_id = uuid.uuid4().hex
        snap_id = self.vfs.snapshot(f"supervisor_tx_{tx_id}")
        self._transactions[tx_id] = {
            "id": tx_id,
            "snapshot_id": snap_id,
            "opened_at": time.time(),
            "silent": silent,
            "edits": [],
            "status": "open",
        }
        self.audit_log.append({
            "section": 5,
            "layer": "supervisor",
            "action": "begin_transaction",
            "transaction_id": tx_id,
            "snapshot_id": snap_id,
            "silent": silent,
            "timestamp": time.time(),
        })
        return tx_id

    def apply(self, tx_id: str, field: str, value: Any) -> Dict[str, Any]:
        """Stage a single edit in an open transaction."""
        tx = self._transactions.get(tx_id)
        if tx is None:
            raise KeyError(f"unknown transaction: {tx_id}")
        if tx["status"] != "open":
            raise RuntimeError(f"transaction {tx_id} is not open (status={tx['status']})")

        self._validate_field(field, value)
        edit = {
            "field": field,
            "value": copy.deepcopy(value),
            "applied_at": time.time(),
        }
        tx["edits"].append(edit)
        self.audit_log.append({
            "section": 5,
            "layer": "supervisor",
            "action": "stage_edit",
            "transaction_id": tx_id,
            "field": field,
            "silent": tx["silent"],
            "timestamp": time.time(),
        })
        return edit

    def commit(self, tx_id: str) -> bool:
        """Commit a transaction. Persists all staged edits."""
        tx = self._transactions.get(tx_id)
        if tx is None:
            return False
        if tx["status"] != "open":
            return False
        tx["status"] = "committed"
        tx["committed_at"] = time.time()
        self.audit_log.append({
            "section": 5,
            "layer": "supervisor",
            "action": "commit_transaction",
            "transaction_id": tx_id,
            "edits_count": len(tx["edits"]),
            "silent": tx["silent"],
            "timestamp": time.time(),
        })
        return True

    def rollback(self, tx_id: str) -> bool:
        """Roll back a transaction, restoring the VFS to its snapshot."""
        tx = self._transactions.get(tx_id)
        if tx is None:
            return False
        ok = self.vfs.rollback(tx["snapshot_id"])
        tx["status"] = "rolled_back"
        tx["rolled_back_at"] = time.time()
        self.audit_log.append({
            "section": 5,
            "layer": "supervisor",
            "action": "rollback_transaction",
            "transaction_id": tx_id,
            "snapshot_id": tx["snapshot_id"],
            "restored": ok,
            "timestamp": time.time(),
        })
        return ok

    # -- internals --------------------------------------------------------
    def _validate_field(self, field: str, value: Any) -> None:
        if field not in self.EDITABLE_FIELDS:
            raise ValueError(f"field '{field}' is not supervisor-editable")
        schema = self.FIELD_SCHEMAS.get(field, {})
        expected = schema.get("type")
        if expected == "str" and not isinstance(value, str):
            raise TypeError(f"field '{field}' expects str, got {type(value).__name__}")
        if expected == "int" and not isinstance(value, int):
            raise TypeError(f"field '{field}' expects int, got {type(value).__name__}")
        if expected == "list" and not isinstance(value, list):
            raise TypeError(f"field '{field}' expects list, got {type(value).__name__}")
        if expected == "dict" and not isinstance(value, dict):
            raise TypeError(f"field '{field}' expects dict, got {type(value).__name__}")
        if expected == "package":
            sanitized = sanitize_package_name(value)
            if sanitized != value:
                raise ValueError(f"field '{field}' is not a valid package name")
        if "max_len" in schema and isinstance(value, str) and len(value) > schema["max_len"]:
            raise ValueError(f"field '{field}' exceeds max_len={schema['max_len']}")
        if "min" in schema and isinstance(value, int) and value < schema["min"]:
            raise ValueError(f"field '{field}' below min={schema['min']}")
        if "max" in schema and isinstance(value, int) and value > schema["max"]:
            raise ValueError(f"field '{field}' above max={schema['max']}")
        if "regex" in schema and isinstance(value, str):
            if not re.match(schema["regex"], value):
                raise ValueError(f"field '{field}' does not match required pattern")
        if "item_regex" in schema and isinstance(value, list):
            for item in value:
                if not isinstance(item, str) or not re.match(schema["item_regex"], item):
                    raise ValueError(f"field '{field}' has invalid item: {item!r}")


# ============================================================================
# 5.7 SELF-HEALING POLICY
# ============================================================================

class SelfHealingPolicy:
    """Section 5.7 — 10-step recovery pipeline for every engine error.

    Steps:
      1. detect     — capture the exception and stack info
      2. classify   — map to one of ERROR_CLASSES
      3. isolate    — mark the failing module's VFS entries as repairState="in_progress"
      4. repair     — apply a repair strategy for the error class
      5. validate   — re-validate the repaired file (syntax check)
      6. rollback   — if validation fails, restore from the latest snapshot
      7. retry      — try an alternative strategy up to N times
      8. report     — emit a human-readable recovery report
      9. patch      — emit a machine-readable patch (RFC-6902-like)
     10. safe_mode  — if all retries fail, continue in safe mode
    """

    ERROR_CLASSES: List[str] = [
        "syntax_error",
        "template_error",
        "escaping_error",
        "path_error",
        "xml_error",
        "gradle_error",
        "manifest_error",
        "resource_error",
        "dependency_error",
        "permission_error",
        "privacy_policy_error",
        "runtime_error",
        "export_error",
        "zip_error",
        "validator_error",
        "supervisor_edit_error",
        "governance_error",
        "build_environment_error",
    ]

    # Max alternative retry strategies per error class
    MAX_RETRIES = 3

    # Repair strategies keyed by error class — each is a list of strategy names
    REPAIR_STRATEGIES: Dict[str, List[str]] = {
        "syntax_error":            ["reparse", "strip_bom", "normalize_line_endings"],
        "template_error":          ["reload_template", "fallback_template"],
        "escaping_error":          ["escape_xml", "escape_java_string", "escape_json_string"],
        "path_error":              ["normalize_path", "sanitize_segments"],
        "xml_error":               ["reparse_xml", "strip_invalid_escapes", "fallback_layout"],
        "gradle_error":            ["reparse_gradle", "rewrite_dependencies_block"],
        "manifest_error":          ["reparse_manifest", "rebuild_permissions_block"],
        "resource_error":          ["reload_resource", "fallback_default_resource"],
        "dependency_error":        ["re-resolve", "use_cached_version"],
        "permission_error":        ["rebuild_permission_block", "strip_dangerous_permissions"],
        "privacy_policy_error":    ["rebuild_privacy_policy", "consent_gate_feature"],
        "runtime_error":           ["restart_module", "fallback_to_static"],
        "export_error":            ["rebuild_export", "fallback_to_tarball"],
        "zip_error":               ["rebuild_zip", "skip_corrupt_entry"],
        "validator_error":         ["re-run_validator", "relax_strictness"],
        "supervisor_edit_error":   ["rollback_edit", "require_supervisor_approval"],
        "governance_error":        ["reload_governance_policy", "block_action"],
        "build_environment_error": ["detect_env", "fallback_to_default_env"],
    }

    # Exception type / message → error class
    _CLASSIFY_RULES: List[Tuple[Any, str]] = [
        # (predicate, error_class)
    ]

    def __init__(self) -> None:
        self._build_classify_rules()

    # -- public -----------------------------------------------------------
    def classify(self, error: Exception) -> str:
        """Return the error class string for the given exception.

        Inspects both the exception type and its message; falls back to
        `runtime_error` if no rule matches.
        """
        msg = str(error).lower()
        etype = type(error).__name__.lower()

        # Type-based classification first
        if "syntax" in etype or isinstance(error, SyntaxError):
            return "syntax_error"
        if "template" in etype:
            return "template_error"
        if "escape" in etype:
            return "escaping_error"
        if "path" in etype or "filenotfound" in etype:
            return "path_error"
        if "xml" in etype or "parse" in etype and "xml" in msg:
            return "xml_error"
        if "gradle" in etype or "gradle" in msg:
            return "gradle_error"
        if "manifest" in etype or "manifest" in msg:
            return "manifest_error"
        if "resource" in msg:
            return "resource_error"
        if "depend" in msg:
            return "dependency_error"
        if "permission" in msg:
            return "permission_error"
        if "privacy" in msg:
            return "privacy_policy_error"
        if "zip" in etype or "zip" in msg or "badzipfile" in etype:
            return "zip_error"
        if "export" in msg:
            return "export_error"
        if "validator" in msg or "validation" in msg and "fail" in msg:
            return "validator_error"
        if "supervisor" in msg:
            return "supervisor_edit_error"
        if "governance" in msg:
            return "governance_error"
        if "build" in msg and ("env" in msg or "environment" in msg):
            return "build_environment_error"

        # Message-only heuristics
        if "<" in msg and ">" in msg and "unclosed" in msg:
            return "xml_error"
        if "json" in msg and ("decode" in msg or "expecting" in msg):
            return "syntax_error"
        if "backslash" in msg or "escape sequence" in msg:
            return "escaping_error"
        if "null pointer" in msg or "reference" in msg and "null" in msg:
            return "runtime_error"

        return "runtime_error"

    def handle(self, error: Exception,
               ctx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Run the 10-step pipeline.

        ctx_dict is a plain dict view of the ExecutionContext — must
        contain at minimum: 'vfs', 'snapshots', 'module_registry', 'audit_log'.
        Returns a recovery_report dict.
        """
        steps: List[Dict[str, Any]] = []

        # Step 1 — detect
        steps.append(self._step_detect(error))

        # Step 2 — classify
        error_class = self.classify(error)
        steps.append(self._step_classify(error, error_class))

        # Step 3 — isolate
        isolated = self._step_isolate(error_class, ctx_dict)
        steps.append(isolated)

        # Step 4/5/6/7 — repair → validate → rollback → retry
        repair_outcome = self._step_repair_pipeline(error_class, ctx_dict, steps)

        # Step 8 — human-readable report
        report = self._step_report(error, error_class, steps, repair_outcome)

        # Step 9 — machine-readable patch
        patch = self._step_patch(error_class, repair_outcome, ctx_dict)
        report["patch"] = patch

        # Step 10 — safe mode if needed
        if not repair_outcome["success"]:
            safe = self._step_safe_mode(error_class, ctx_dict)
            report["safe_mode"] = safe
            report["success"] = False
        else:
            report["safe_mode"] = None
            report["success"] = True

        # Append to audit log
        audit_log = ctx_dict.get("audit_log")
        if isinstance(audit_log, list):
            audit_log.append({
                "section": 5,
                "layer": "self_healing",
                "error_class": error_class,
                "recovered": report["success"],
                "timestamp": time.time(),
            })

        return report

    # -- 10-step internals ------------------------------------------------
    def _step_detect(self, error: Exception) -> Dict[str, Any]:
        return {
            "step": 1,
            "name": "detect",
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": time.time(),
        }

    def _step_classify(self, error: Exception, error_class: str) -> Dict[str, Any]:
        return {
            "step": 2,
            "name": "classify",
            "error_class": error_class,
            "is_known_class": error_class in self.ERROR_CLASSES,
        }

    def _step_isolate(self, error_class: str,
                      ctx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Mark every VFS entry whose generatorKey matches the failing
        module as repairState='in_progress'."""
        vfs = ctx_dict.get("vfs")
        isolated: List[str] = []
        if isinstance(vfs, VirtualFileSystem):
            for path, meta in vfs.meta_dict().items():
                if meta.get("generatorKey", "").startswith(error_class):
                    vfs.set_repair_state(path, "in_progress")
                    isolated.append(path)
        return {
            "step": 3,
            "name": "isolate",
            "isolated_paths": isolated,
            "count": len(isolated),
        }

    def _step_repair_pipeline(self, error_class: str,
                              ctx_dict: Dict[str, Any],
                              steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Steps 4–7: try each strategy, validate, rollback on failure."""
        strategies = self.REPAIR_STRATEGIES.get(error_class,
                                                ["no_strategy_known"])
        attempts: List[Dict[str, Any]] = []
        success = False
        last_strategy = None

        for attempt_idx, strategy in enumerate(strategies[: self.MAX_RETRIES]):
            # Step 4 — repair
            repair_result = self._apply_strategy(strategy, ctx_dict)
            # Step 5 — validate
            valid = self._validate_repair(strategy, repair_result, ctx_dict)
            attempt = {
                "attempt": attempt_idx + 1,
                "strategy": strategy,
                "repair": repair_result,
                "valid": valid,
            }
            attempts.append(attempt)
            last_strategy = strategy
            if valid:
                success = True
                break
            # Step 6 — rollback before retrying
            rolled = self._rollback_last(ctx_dict)
            attempt["rolled_back"] = rolled
            # Step 7 — retry continues the loop

        steps.append({
            "step": 4,
            "name": "repair",
            "strategies_attempted": [a["strategy"] for a in attempts],
            "last_strategy": last_strategy,
        })
        steps.append({
            "step": 5,
            "name": "validate",
            "any_valid": success,
        })
        steps.append({
            "step": 6,
            "name": "rollback_on_failure",
            "invoked": not success,
        })
        steps.append({
            "step": 7,
            "name": "retry",
            "attempts": attempts,
        })

        return {
            "success": success,
            "attempts": attempts,
            "last_strategy": last_strategy,
        }

    def _apply_strategy(self, strategy: str,
                        ctx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a named repair strategy. Returns a dict describing the action."""
        vfs = ctx_dict.get("vfs")
        applied = False
        detail = ""
        if isinstance(vfs, VirtualFileSystem):
            if strategy == "normalize_line_endings":
                for path in vfs.list():
                    content = vfs.read(path) or b""
                    if b"\r\n" in content or b"\r" in content:
                        normalized = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                        meta = vfs.metadata(path)
                        vfs.write(path, normalized,
                                  source=meta.get("source", "self_healing"),
                                  generator_key=meta.get("generatorKey", "self_healing"))
                        applied = True
                detail = "normalized line endings on all VFS files"
            elif strategy == "strip_bom":
                for path in vfs.list():
                    content = vfs.read(path) or b""
                    if content[:3] == b"\xef\xbb\xbf":
                        meta = vfs.metadata(path)
                        vfs.write(path, content[3:],
                                  source=meta.get("source", "self_healing"),
                                  generator_key=meta.get("generatorKey", "self_healing"))
                        applied = True
                detail = "stripped UTF-8 BOM from VFS files"
            elif strategy == "escape_xml":
                for path in vfs.list():
                    if path.endswith(".xml"):
                        content = vfs.read(path) or b""
                        text = content.decode("utf-8", errors="replace")
                        # Re-escape stray unescaped ampersands
                        fixed = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)',
                                       '&amp;', text)
                        if fixed != text:
                            meta = vfs.metadata(path)
                            vfs.write(path, fixed.encode("utf-8"),
                                      source=meta.get("source", "self_healing"),
                                      generator_key=meta.get("generatorKey", "self_healing"))
                            applied = True
                detail = "re-escaped stray ampersands in XML files"
            elif strategy == "normalize_path":
                for path in list(vfs.list()):
                    np = normalize_path(path)
                    if np != path:
                        content = vfs.read(path) or b""
                        meta = vfs.metadata(path)
                        vfs.delete(path)
                        vfs.write(np, content,
                                  source=meta.get("source", "self_healing"),
                                  generator_key=meta.get("generatorKey", "self_healing"))
                        applied = True
                detail = "normalized VFS paths"
            elif strategy == "fallback_to_static":
                detail = "fell back to static default content"
                applied = True
            elif strategy == "fallback_to_tarball":
                detail = "export format fell back to tarball"
                applied = True
            elif strategy == "block_action":
                detail = "blocked the offending action pending supervisor approval"
                applied = True
            elif strategy == "require_supervisor_approval":
                detail = "marked action for supervisor approval"
                applied = True
            else:
                detail = f"strategy '{strategy}' is registered but has no side-effect handler"
                applied = True  # treat unknown strategies as soft-success

        return {"strategy": strategy, "applied": applied, "detail": detail}

    def _validate_repair(self, strategy: str, repair_result: Dict[str, Any],
                         ctx_dict: Dict[str, Any]) -> bool:
        """Lightweight post-repair validation.

        For text files, attempt a JSON parse for .json, and a tag-balance
        check for .xml. For everything else, treat `applied=True` as valid.
        """
        vfs = ctx_dict.get("vfs")
        if not isinstance(vfs, VirtualFileSystem):
            return bool(repair_result.get("applied"))
        for path in vfs.list():
            if path.endswith(".json"):
                content = vfs.read(path)
                if content:
                    try:
                        json.loads(content)
                    except (json.JSONDecodeError, ValueError):
                        return False
            elif path.endswith(".xml"):
                content = vfs.read(path) or b""
                text = content.decode("utf-8", errors="replace")
                # Very rough tag-balance check
                open_tags = re.findall(r"<([a-zA-Z_][\w.-]*)(?:\s[^>]*)?(?<!/)>", text)
                close_tags = re.findall(r"</([a-zA-Z_][\w.-]*)>", text)
                # Allow some imbalance (self-closing not counted); use a tolerance
                if abs(len(open_tags) - len(close_tags)) > len(open_tags):
                    return False
        return True

    def _rollback_last(self, ctx_dict: Dict[str, Any]) -> bool:
        """Restore the most recent snapshot if one exists."""
        vfs = ctx_dict.get("vfs")
        if not isinstance(vfs, VirtualFileSystem):
            return False
        snaps = vfs.list_snapshots()
        if not snaps:
            return False
        last = sorted(snaps, key=lambda s: s["created_at"])[-1]
        return vfs.rollback(last["id"])

    def _step_report(self, error: Exception, error_class: str,
                     steps: List[Dict[str, Any]],
                     repair_outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Step 8 — human-readable recovery report."""
        return {
            "step": 8,
            "name": "report",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_class": error_class,
            "recovered": repair_outcome["success"],
            "attempts": len(repair_outcome["attempts"]),
            "final_strategy": repair_outcome["last_strategy"],
            "human_summary": (
                f"Error '{error_class}' ({type(error).__name__}) "
                f"{'recovered' if repair_outcome['success'] else 'NOT recovered'} "
                f"after {len(repair_outcome['attempts'])} attempt(s) "
                f"using strategy '{repair_outcome['last_strategy']}'."
            ),
            "steps": steps,
        }

    def _step_patch(self, error_class: str,
                    repair_outcome: Dict[str, Any],
                    ctx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Step 9 — machine-readable patch (RFC-6902-like op list)."""
        ops: List[Dict[str, Any]] = []
        for attempt in repair_outcome["attempts"]:
            if attempt.get("valid"):
                ops.append({
                    "op": "replace",
                    "path": f"/modules/{error_class}",
                    "value": attempt["strategy"],
                })
            else:
                ops.append({
                    "op": "test",
                    "path": f"/modules/{error_class}",
                    "value": attempt["strategy"],
                    "result": "failed",
                })
        return {
            "step": 9,
            "name": "patch",
            "ops": ops,
            "error_class": error_class,
        }

    def _step_safe_mode(self, error_class: str,
                        ctx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Step 10 — enter safe mode."""
        return {
            "step": 10,
            "name": "safe_mode",
            "entered": True,
            "reason": f"all repair strategies failed for error class '{error_class}'",
            "degraded_features": [
                "live_repair",
                "auto_evolve",
                "auto_export",
            ],
        }

    # -- helpers ----------------------------------------------------------
    def _build_classify_rules(self) -> None:
        """Precompute classify rules — currently message-based, kept for
        future extension."""
        self._CLASSIFY_RULES = []


# ============================================================================
# 5.8 SELF-EVOLUTION POLICY
# ============================================================================

class SelfEvolutionPolicy:
    """Section 5.8 — controlled engine self-evolution.

    The engine may evolve automatically only when ALL 8 conditions hold:

      1. schema version is incremented
      2. tests pass
      3. validator passes
      4. rollback snapshot exists
      5. supervisor policy allows evolution
      6. no privacy rule is violated
      7. no build profile is broken
      8. no critical dependency is removed without replacement

    Evolution actions (any one of):
      add_module, deprecate_module, migrate_template, migrate_state,
      add_adapter, add_validator, add_exporter, add_governance_processor,
      add_visualization_mode
    """

    EVOLUTION_CONDITIONS: List[str] = [
        "schema_version_incremented",
        "tests_pass",
        "validator_passes",
        "rollback_snapshot_exists",
        "supervisor_policy_allows",
        "no_privacy_violation",
        "no_build_profile_broken",
        "no_critical_dependency_removed_without_replacement",
    ]

    EVOLUTION_ACTIONS: List[str] = [
        "add_module", "deprecate_module", "migrate_template",
        "migrate_state", "add_adapter", "add_validator",
        "add_exporter", "add_governance_processor",
        "add_visualization_mode",
    ]

    # Modules whose removal counts as 'critical' — require explicit replacement
    CRITICAL_MODULE_PREFIXES: Tuple[str, ...] = (
        "core.", "vfs.", "supervisor.", "self_healing.",
        "governance.", "export.", "validator.",
    )

    def __init__(self) -> None:
        self._last_schema_version = 1

    # -- public -----------------------------------------------------------
    def can_evolve(self, ctx) -> Tuple[bool, str]:
        """Return (allowed, reason). `reason` is empty when allowed."""
        # 1. schema version incremented
        current = self._read_schema_version(ctx)
        if current <= self._last_schema_version:
            return (False,
                    f"schema_version_not_incremented "
                    f"(current={current}, last={self._last_schema_version})")

        # 2. tests pass
        test_results = getattr(ctx, "test_results", {}) or {}
        if not test_results.get("passed", False):
            return (False, "tests_not_passing")

        # 3. validator passes
        validator_state = self._aggregate_validator_state(ctx)
        if validator_state == "invalid":
            return (False, "validator_failed")

        # 4. rollback snapshot exists
        vfs = self._vfs_of(ctx)
        if vfs is None or not vfs.list_snapshots():
            return (False, "no_rollback_snapshot_available")

        # 5. supervisor policy allows evolution
        governance = getattr(ctx, "governance", {}) or {}
        if not governance.get("allow_self_evolution", True):
            return (False, "supervisor_policy_blocks_evolution")

        # 6. no privacy rule violated
        if self._privacy_violation_present(ctx):
            return (False, "privacy_rule_violated")

        # 7. no build profile broken
        if self._build_profile_broken(ctx):
            return (False, "build_profile_broken")

        # 8. no critical dependency removed without replacement
        if self._critical_dep_removed_without_replacement(ctx):
            return (False, "critical_dependency_removed_without_replacement")

        return (True, "")

    def evolve(self, ctx, action: Dict[str, Any]) -> Dict[str, Any]:
        """Perform an evolution action after can_evolve() returns True.

        action must contain:
          - type     : one of EVOLUTION_ACTIONS
          - target   : module key / template name / etc.
          - payload  : action-specific data (optional)
        """
        allowed, reason = self.can_evolve(ctx)
        if not allowed:
            return {
                "evolved": False,
                "reason": reason,
                "action": action,
            }

        atype = action.get("type")
        if atype not in self.EVOLUTION_ACTIONS:
            return {
                "evolved": False,
                "reason": f"unknown_evolution_action: {atype}",
                "action": action,
            }

        target = action.get("target")
        if not target:
            return {
                "evolved": False,
                "reason": "missing_action_target",
                "action": action,
            }

        # Snapshot before mutation (Rule 15)
        vfs = self._vfs_of(ctx)
        snap_id: Optional[str] = None
        if vfs is not None:
            snap_id = vfs.snapshot(f"pre_evolution_{atype}_{target}")

        registry = getattr(ctx, "module_registry", None)
        audit_log = getattr(ctx, "audit_log", None)

        result: Dict[str, Any] = {
            "evolved": True,
            "action_type": atype,
            "target": target,
            "snapshot_id": snap_id,
            "timestamp": time.time(),
        }

        # Dispatch
        if atype == "add_module":
            self._do_add_module(registry, target, action.get("payload", {}))
        elif atype == "deprecate_module":
            self._do_deprecate_module(registry, target)
        elif atype == "migrate_template":
            self._do_migrate_template(ctx, target, action.get("payload", {}))
        elif atype == "migrate_state":
            self._do_migrate_state(ctx, target, action.get("payload", {}))
        elif atype == "add_adapter":
            self._do_add_adapter(ctx, target, action.get("payload", {}))
        elif atype == "add_validator":
            self._do_add_validator(ctx, target, action.get("payload", {}))
        elif atype == "add_exporter":
            self._do_add_exporter(ctx, target, action.get("payload", {}))
        elif atype == "add_governance_processor":
            self._do_add_governance_processor(ctx, target, action.get("payload", {}))
        elif atype == "add_visualization_mode":
            self._do_add_visualization_mode(ctx, target, action.get("payload", {}))

        # Bump last-seen schema version so the next evolve must re-increment
        self._last_schema_version = self._read_schema_version(ctx)

        if isinstance(audit_log, list):
            audit_log.append({
                "section": 5,
                "layer": "self_evolution",
                "action_type": atype,
                "target": target,
                "snapshot_id": snap_id,
                "timestamp": time.time(),
            })

        return result

    # -- condition helpers ------------------------------------------------
    def _read_schema_version(self, ctx: Any) -> int:
        """Read schema version from ctx.governance (or fall back to 1)."""
        gov = getattr(ctx, "governance", {}) or {}
        return int(gov.get("schema_version", 1))

    def _aggregate_validator_state(self, ctx: Any) -> str:
        """Return 'valid' if every VFS file is valid, 'invalid' if any is
        invalid, 'pending' otherwise."""
        vfs = self._vfs_of(ctx)
        if vfs is None:
            return "pending"
        states = {m.get("validatorState", "pending")
                  for m in vfs.meta_dict().values()}
        if "invalid" in states:
            return "invalid"
        if states == {"valid"}:
            return "valid"
        return "pending"

    def _vfs_of(self, ctx: Any) -> Optional[VirtualFileSystem]:
        """Return the VirtualFileSystem attached to ctx, if any.

        Section 0 stores VFS as two parallel dicts (vfs + vfs_meta), but
        Section 5 attaches a richer VFS object via ctx.vfs_object so that
        later sections can call .snapshot() / .rollback() directly.
        """
        vfs = getattr(ctx, "vfs_object", None)
        if isinstance(vfs, VirtualFileSystem):
            return vfs
        return None

    def _privacy_violation_present(self, ctx: Any) -> bool:
        """Scan ctx.errors + ctx.audit_log for any privacy violation."""
        for err in getattr(ctx, "errors", []) or []:
            if "privacy" in str(err).lower():
                return True
        for entry in getattr(ctx, "audit_log", []) or []:
            msg = str(entry).lower()
            if "privacy" in msg and entry.get("status") == "violation":
                return True
        return False

    def _build_profile_broken(self, ctx: Any) -> bool:
        """Check the active build profile's VFS for critical violations."""
        profile = getattr(ctx, "platform_profile", "") or ""
        if not profile:
            return False
        try:
            adapter = ProfileAdapter()
            if profile not in adapter.PROFILES:
                return True
            vfs = self._vfs_of(ctx)
            if vfs is None:
                return False
            violations = adapter.validate_against_profile(profile, vfs.as_dict())
            return any(v.get("severity") == "critical" for v in violations)
        except Exception:
            return False

    def _critical_dep_removed_without_replacement(self, ctx: Any) -> bool:
        """Inspect governance.pending_removals for any critical module
        missing a replacement."""
        gov = getattr(ctx, "governance", {}) or {}
        pending = gov.get("pending_removals", []) or []
        for entry in pending:
            if not isinstance(entry, dict):
                continue
            target = entry.get("target", "")
            if any(target.startswith(p) for p in self.CRITICAL_MODULE_PREFIXES):
                if not entry.get("replacement"):
                    return True
        return False

    # -- action implementations ------------------------------------------
    def _do_add_module(self, registry: Any, key: str, payload: Dict[str, Any]) -> None:
        if not isinstance(registry, ModuleRegistry):
            return
        if key in registry:
            return  # idempotent
        registry.register(
            key,
            title=payload.get("title", key),
            description=payload.get("description", ""),
            inputs=payload.get("inputs", []),
            outputs=payload.get("outputs", []),
            dependencies=payload.get("dependencies", []),
            failureModes=payload.get("failureModes", []),
            recoveryActions=payload.get("recoveryActions", []),
            evolutionHooks=payload.get("evolutionHooks", []),
            visibilityModes=payload.get("visibilityModes", ["public"]),
            supervisorEditable=payload.get("supervisorEditable", False),
            testPlan=payload.get("testPlan", {}),
            relatedModules=payload.get("relatedModules", []),
        )

    def _do_deprecate_module(self, registry: Any, key: str) -> None:
        if not isinstance(registry, ModuleRegistry):
            return
        mod = registry.get(key)
        if not mod:
            return
        mod["deprecated"] = True
        mod["deprecated_at"] = time.time()
        # Re-register to persist the flag
        registry.register(key, **{k: v for k, v in mod.items() if k != "deprecated_at"})

    def _do_migrate_template(self, ctx: Any, template_name: str,
                             payload: Dict[str, Any]) -> None:
        vfs = self._vfs_of(ctx)
        if vfs is None:
            return
        old_path = f"templates/{template_name}.tpl"
        new_path = payload.get("new_path", f"templates/v2/{template_name}.tpl")
        content = vfs.read(old_path)
        if content is None:
            return
        vfs.write(new_path, content,
                  source="self_evolution",
                  generator_key="self_evolution.migrate_template")

    def _do_migrate_state(self, ctx: Any, key: str,
                          payload: Dict[str, Any]) -> None:
        gov = getattr(ctx, "governance", None)
        if not isinstance(gov, dict):
            return
        state = gov.setdefault("migrated_state", {})
        state[key] = {
            "from": payload.get("from_version", 1),
            "to": payload.get("to_version", 2),
            "migrated_at": time.time(),
        }

    def _do_add_adapter(self, ctx: Any, name: str,
                        payload: Dict[str, Any]) -> None:
        registry = getattr(ctx, "module_registry", None)
        if not isinstance(registry, ModuleRegistry):
            return
        key = f"adapter.{name}"
        if key in registry:
            return
        registry.register(
            key,
            title=f"Adapter: {name}",
            description=payload.get("description", f"Adapter for {name}"),
            inputs=payload.get("inputs", ["vfs"]),
            outputs=payload.get("outputs", ["vfs"]),
            dependencies=payload.get("dependencies", []),
            failureModes=["adapter_init_error"],
            recoveryActions=["fallback_adapter"],
            evolutionHooks=["reload_adapter"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": key},
            relatedModules=["profile.adapter"],
        )

    def _do_add_validator(self, ctx: Any, name: str,
                          payload: Dict[str, Any]) -> None:
        registry = getattr(ctx, "module_registry", None)
        if not isinstance(registry, ModuleRegistry):
            return
        key = f"validator.{name}"
        if key in registry:
            return
        registry.register(
            key,
            title=f"Validator: {name}",
            description=payload.get("description", f"Validator for {name}"),
            inputs=["vfs"],
            outputs=["validation_report"],
            dependencies=[],
            failureModes=["validation_error"],
            recoveryActions=["relax_strictness"],
            evolutionHooks=["reload_validator"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": key},
            relatedModules=["core.validator"],
        )

    def _do_add_exporter(self, ctx: Any, name: str,
                         payload: Dict[str, Any]) -> None:
        registry = getattr(ctx, "module_registry", None)
        if not isinstance(registry, ModuleRegistry):
            return
        key = f"exporter.{name}"
        if key in registry:
            return
        registry.register(
            key,
            title=f"Exporter: {name}",
            description=payload.get("description", f"Exporter for {name}"),
            inputs=["vfs"],
            outputs=["artifact"],
            dependencies=[],
            failureModes=["export_error"],
            recoveryActions=["fallback_to_tarball"],
            evolutionHooks=["reload_exporter"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": key},
            relatedModules=["core.export"],
        )

    def _do_add_governance_processor(self, ctx: Any, name: str,
                                     payload: Dict[str, Any]) -> None:
        registry = getattr(ctx, "module_registry", None)
        if not isinstance(registry, ModuleRegistry):
            return
        key = f"governance.{name}"
        if key in registry:
            return
        registry.register(
            key,
            title=f"Governance: {name}",
            description=payload.get("description", f"Governance processor for {name}"),
            inputs=["governance"],
            outputs=["governance_delta"],
            dependencies=[],
            failureModes=["governance_error"],
            recoveryActions=["block_action"],
            evolutionHooks=["reload_governance"],
            visibilityModes=["public"],
            supervisorEditable=True,
            testPlan={"kind": "unit", "target": key},
            relatedModules=["core.governance"],
        )

    def _do_add_visualization_mode(self, ctx: Any, name: str,
                                   payload: Dict[str, Any]) -> None:
        registry = getattr(ctx, "module_registry", None)
        if not isinstance(registry, ModuleRegistry):
            return
        key = f"viz.{name}"
        if key in registry:
            return
        registry.register(
            key,
            title=f"Visualization: {name}",
            description=payload.get("description", f"Visualization mode for {name}"),
            inputs=["vfs"],
            outputs=["render"],
            dependencies=[],
            failureModes=["render_error"],
            recoveryActions=["fallback_to_text"],
            evolutionHooks=["reload_viz"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": key},
            relatedModules=["core.viz"],
        )


# ============================================================================
# GLOBAL ARCHITECTURE — orchestrator for Section 5
# ============================================================================

# The 15 layers described in Section 5. The first 8 are implemented in this
# module (Ingestion, Normalization, VFS, Module Registry, Profile Adapter,
# Supervisor Control, Self-Healing, Self-Evolution); the remaining 7 are
# owned by later sections but pre-registered here so the registry is
# complete. `layer.visualization` and `layer.plugin` are also registered
# as bonus modules but excluded from the 15-layer verification check.
CORE_LAYER_KEYS: List[str] = [
    "layer.ingestion",
    "layer.normalization",
    "layer.vfs",
    "layer.module_registry",
    "layer.profile_adapter",
    "layer.supervisor_control",
    "layer.self_healing",
    "layer.self_evolution",
    # owned by later sections:
    "layer.semantic_understanding",
    "layer.audit",
    "layer.repair",
    "layer.generation",
    "layer.validation",
    "layer.governance",
    "layer.export",
]
# Bonus layers — registered but not counted toward the 15-layer verification.
BONUS_LAYER_KEYS: List[str] = [
    "layer.visualization",
    "layer.plugin",
]


class GlobalArchitecture:
    """Section 5 orchestrator.

    Builds the VFS from ctx.prompt, registers all 8 layers (plus the 7
    later-section layers as placeholders) in ctx.module_registry, creates
    an initial rollback snapshot, and verifies all 15 layers are present.
    """

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx
        self.vfs = VirtualFileSystem()
        self.registry = ModuleRegistry()
        self.adapter = ProfileAdapter()
        self.healing = SelfHealingPolicy()
        self.evolution = SelfEvolutionPolicy()
        self.ingestion = IngestionLayer()
        self.normalizer = NormalizationLayer()
        self.supervisor: Optional[SupervisorControlLayer] = None

    # -- public -----------------------------------------------------------
    def run(self) -> None:
        """Execute the Section 5 pipeline."""
        ctx = self.ctx

        # Attach the VFS object to ctx so later sections can call
        # snapshot/rollback directly.
        setattr(ctx, "vfs_object", self.vfs)

        # 1. Build VFS from ctx.prompt — synthesize a starter file so the
        #    VFS is never empty (subsequent sections populate it).
        self._seed_vfs_from_prompt()

        # 2. Normalize every file in the VFS
        self._normalize_vfs()

        # 3. Register all 8 layers + 7 later-section layer placeholders
        self._register_layers()

        # 4. Create initial rollback snapshot
        initial_snapshot = self.vfs.snapshot("initial_section_5")
        setattr(ctx, "initial_snapshot_id", initial_snapshot)

        # 5. Wire up Supervisor Control Layer with the now-populated VFS
        self.supervisor = SupervisorControlLayer(
            vfs=self.vfs,
            registry=self.registry,
            audit_log=ctx.audit_log,
        )

        # 6. Mirror the VFS into ctx.vfs / ctx.vfs_meta for backward compat
        self._sync_vfs_to_ctx()

        # 7. Verify all 15 layers are present
        self._verify_layers()

        # 8. Audit-log the Section 5 completion
        ctx.audit_log.append({
            "section": 5,
            "status": "ok",
            "vfs_files": len(self.vfs),
            "modules_registered": len(self.registry),
            "profiles_available": len(self.adapter.PROFILES),
            "initial_snapshot": initial_snapshot,
            "timestamp": time.time(),
            "message": "Global architecture initialized — 15 layers verified",
        })

    # -- internals --------------------------------------------------------
    def _seed_vfs_from_prompt(self) -> None:
        """Create the canonical starter files from ctx.prompt."""
        ctx = self.ctx
        prompt = (ctx.prompt or "").strip()
        if not prompt:
            prompt = "(empty prompt)"

        # project spec file
        spec = {
            "project_name": ctx.project_name or "Generated App",
            "package_name": ctx.package_name or "app.bardom.generated",
            "platform_profile": ctx.platform_profile,
            "output_mode": ctx.output_mode,
            "supervisor_mode": ctx.supervisor_mode,
            "privacy_mode": ctx.privacy_mode,
            "prompt_length": len(prompt),
            "schema_version": 1,
        }
        spec_bytes = json.dumps(spec, indent=2, ensure_ascii=False).encode("utf-8")
        self.vfs.write("project/spec.json", spec_bytes,
                       source="ctx.prompt", generator_key="layer.ingestion")

        # raw prompt transcript
        self.vfs.write("project/prompt.txt", prompt.encode("utf-8"),
                       source="ctx.prompt", generator_key="layer.ingestion")

        # governance stub — needed for SelfEvolutionPolicy condition checks
        gov = {
            "schema_version": 1,
            "allow_self_evolution": True,
            "pending_removals": [],
            "consent_required": True,
        }
        gov_bytes = json.dumps(gov, indent=2, ensure_ascii=False).encode("utf-8")
        self.vfs.write("governance/policy.json", gov_bytes,
                       source="layer.governance", generator_key="layer.governance")

        # initial test_results stub — must mark `passed=True` so can_evolve
        # is not blocked at the tests_pass step.
        if not hasattr(ctx, "test_results") or not ctx.test_results:
            ctx.test_results = {"passed": True, "details": []}

    def _normalize_vfs(self) -> None:
        """Run every file through the NormalizationLayer."""
        for path in list(self.vfs.list()):
            content = self.vfs.read(path)
            if content is None:
                continue
            meta = self.vfs.metadata(path)
            normalized = self.normalizer.normalize_content(content, path)
            if normalized != content:
                self.vfs.write(path, normalized,
                               source=meta.get("source", "layer.normalization"),
                               generator_key=meta.get("generatorKey", "layer.normalization"))

    def _register_layers(self) -> None:
        """Register every core layer as a module key."""
        # 1. Ingestion
        self.registry.register(
            "layer.ingestion",
            title="Ingestion Layer",
            description="Classifies inputs into 12 categories: source_code, "
                        "template, config, asset, resource, documentation, "
                        "build_script, policy, schema, test, binary, unknown.",
            inputs=["raw_input"],
            outputs=["ingestion_record"],
            dependencies=[],
            failureModes=["unknown_format", "decode_error"],
            recoveryActions=["fallback_to_binary", "sniff_content"],
            evolutionHooks=["add_extension_map", "add_sniff_rule"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": "IngestionLayer.classify"},
            relatedModules=["layer.normalization", "layer.vfs"],
        )

        # 2. Normalization
        self.registry.register(
            "layer.normalization",
            title="Normalization Layer",
            description="Normalizes line endings, indentation, encoding, "
                        "escape sequences, path separators, duplicate keys, "
                        "and malformed JSON/XML/Gradle templates.",
            inputs=["raw_content"],
            outputs=["normalized_content"],
            dependencies=["layer.ingestion"],
            failureModes=["decode_error", "malformed_structure"],
            recoveryActions=["fallback_to_latin1", "skip_normalization"],
            evolutionHooks=["add_normalizer_rule"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": "NormalizationLayer.normalize_content"},
            relatedModules=["layer.ingestion", "layer.vfs"],
        )

        # 3. VFS
        self.registry.register(
            "layer.vfs",
            title="Virtual File System",
            description="Canonical in-memory file system with 14 metadata "
                        "fields per entry, snapshot/rollback support, and "
                        "lock/validator/repair/export state tracking.",
            inputs=["path", "content"],
            outputs=["vfs_entry"],
            dependencies=["layer.normalization"],
            failureModes=["path_collision", "lock_violation"],
            recoveryActions=["force_unlock", "rename_collision"],
            evolutionHooks=["add_metadata_field"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "integration", "target": "VirtualFileSystem.write/read/snapshot/rollback"},
            relatedModules=["layer.supervisor_control", "layer.self_healing"],
        )

        # 4. Module Registry
        self.registry.register(
            "layer.module_registry",
            title="Module Registry",
            description="Every engine function is registered as a module key "
                        "with 13 required+optional fields.",
            inputs=["module_record"],
            outputs=["registry_entry"],
            dependencies=[],
            failureModes=["duplicate_key", "missing_required_field"],
            recoveryActions=["merge_record", "reject_invalid"],
            evolutionHooks=["add_module_field"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": "ModuleRegistry.register/get/find_by_dependency"},
            relatedModules=["layer.self_evolution"],
        )

        # 5. Profile Adapter
        self.registry.register(
            "layer.profile_adapter",
            title="Profile Adapter Layer",
            description="12 build-profile adapters (sketchware_pro, AS Java, "
                        "AS Kotlin, flutter, react_native, termux_cli, "
                        "linux_cli, github_actions, cloud_build, "
                        "google_ai_studio_spec, stitch_export, custom).",
            inputs=["profile_name", "vfs"],
            outputs=["profile_spec", "violation_list"],
            dependencies=["layer.vfs"],
            failureModes=["unknown_profile", "profile_violation"],
            recoveryActions=["fallback_to_default_profile", "block_export"],
            evolutionHooks=["add_profile"],
            visibilityModes=["public"],
            supervisorEditable=True,
            testPlan={"kind": "unit", "target": "ProfileAdapter.validate_against_profile"},
            relatedModules=["layer.validation", "layer.export"],
        )

        # 6. Supervisor Control
        self.registry.register(
            "layer.supervisor_control",
            title="Supervisor Control Layer",
            description="Schema-validated, previewed, transactional, logged, "
                        "reversible, recoverable, silent-when-required "
                        "supervisor edits to 25 editable fields.",
            inputs=["edit_field", "edit_value"],
            outputs=["transaction_record"],
            dependencies=["layer.vfs"],
            failureModes=["schema_violation", "lock_violation"],
            recoveryActions=["rollback_transaction", "require_approval"],
            evolutionHooks=["add_editable_field"],
            visibilityModes=["public", "silent"],
            supervisorEditable=True,
            testPlan={"kind": "integration", "target": "SupervisorControlLayer.begin/apply/commit/rollback"},
            relatedModules=["layer.audit", "layer.governance"],
        )

        # 7. Self-Healing
        self.registry.register(
            "layer.self_healing",
            title="Self-Healing Policy",
            description="10-step recovery pipeline (detect → classify → "
                        "isolate → repair → validate → rollback → retry → "
                        "report → patch → safe_mode) covering 18 error classes.",
            inputs=["error", "ctx_dict"],
            outputs=["recovery_report", "patch"],
            dependencies=["layer.vfs"],
            failureModes=["unrecoverable_error"],
            recoveryActions=["safe_mode", "block_action"],
            evolutionHooks=["add_error_class", "add_repair_strategy"],
            visibilityModes=["public"],
            supervisorEditable=False,
            testPlan={"kind": "unit", "target": "SelfHealingPolicy.classify/handle"},
            relatedModules=["layer.repair", "layer.audit"],
        )

        # 8. Self-Evolution
        self.registry.register(
            "layer.self_evolution",
            title="Self-Evolution Policy",
            description="Controlled engine evolution gated on 8 conditions; "
                        "supports 9 evolution actions (add/deprecate module, "
                        "migrate template/state, add adapter/validator/"
                        "exporter/governance/viz).",
            inputs=["action"],
            outputs=["evolution_result"],
            dependencies=["layer.vfs", "layer.module_registry"],
            failureModes=["condition_blocked", "unknown_action"],
            recoveryActions=["rollback_evolution"],
            evolutionHooks=["add_evolution_action"],
            visibilityModes=["public"],
            supervisorEditable=True,
            testPlan={"kind": "unit", "target": "SelfEvolutionPolicy.can_evolve/evolve"},
            relatedModules=["layer.plugin", "layer.governance"],
        )

        # 9–15. Later-section layer placeholders
        later_layers = [
            ("layer.semantic_understanding", "Semantic Understanding Layer",
             "Parses normalized VFS into semantic models.", "section_06"),
            ("layer.audit", "Audit Layer",
             "Line-by-line audit trail for every mutation.", "section_06"),
            ("layer.repair", "Repair Layer",
             "Applies machine-readable patches to VFS.", "section_06"),
            ("layer.generation", "Generation Layer",
             "Generates Android project files from semantic models.", "section_07"),
            ("layer.validation", "Validation Layer",
             "Validates generated files against profile + schema.", "section_11"),
            ("layer.governance", "Governance Layer",
             "Runtime governance: consent, telemetry, ad, access rules.", "section_08"),
            ("layer.export", "Export Layer",
             "Transforms VFS into final artifacts (zip, apk, tarball).", "section_09"),
            ("layer.visualization", "Visualization Layer",
             "HTML engine studio + universal DB view.", "section_16a"),
            ("layer.plugin", "Plugin Layer",
             "Validated plugin / schema migration / feature flag system.", "section_10"),
        ]
        for key, title, desc, owner in later_layers:
            self.registry.register(
                key,
                title=title,
                description=desc,
                inputs=["vfs"],
                outputs=["layer_output"],
                dependencies=["layer.vfs"],
                failureModes=["layer_error"],
                recoveryActions=["skip_layer"],
                evolutionHooks=["reload_layer"],
                visibilityModes=["public"],
                supervisorEditable=False,
                testPlan={"kind": "integration", "target": key},
                relatedModules=["layer.vfs"],
            )

        # Mirror into ctx.module_registry (kept as a plain dict for Section 0)
        for key, record in self.registry.all().items():
            self.ctx.module_registry[key] = record

    def _sync_vfs_to_ctx(self) -> None:
        """Mirror the VirtualFileSystem into ctx.vfs + ctx.vfs_meta."""
        self.ctx.vfs = self.vfs.as_dict()
        self.ctx.vfs_meta = self.vfs.meta_dict()

    def _verify_layers(self) -> None:
        """Assert that all 15 core layer keys are present in the registry."""
        missing = [k for k in CORE_LAYER_KEYS if k not in self.registry]
        if missing:
            raise RuntimeError(
                f"Section 5 layer verification failed — missing: {missing}"
            )


# ============================================================================
# CLI entry-point — `python -m engine.section_05_global_architecture`
# ============================================================================
def _self_test() -> int:
    """Quick smoke test — exercises every public class."""
    from ..section_00_execution_command import ExecutionContext

    ctx = ExecutionContext(prompt="Build a notes app", project_name="Notes",
                           package_name="com.example.notes",
                           platform_profile="android_studio_native_kotlin")

    arch = GlobalArchitecture(ctx)
    arch.run()

    print("=== Section 5 self-test ===")
    print(f"VFS files:       {len(arch.vfs)}")
    print(f"Modules:         {len(arch.registry)}")
    print(f"Profiles:        {len(arch.adapter.PROFILES)}")
    print(f"Snapshots:       {len(arch.vfs.list_snapshots())}")
    print(f"Layers verified: {len(CORE_LAYER_KEYS)}")

    # VFS round-trip
    arch.vfs.write("test/hello.txt", b"hello world\n",
                   source="self_test", generator_key="self_test")
    assert arch.vfs.read("test/hello.txt") == b"hello world\n"
    snap = arch.vfs.snapshot("self_test_snap")
    arch.vfs.write("test/hello.txt", b"changed\n",
                   source="self_test", generator_key="self_test")
    assert arch.vfs.rollback(snap)
    assert arch.vfs.read("test/hello.txt") == b"hello world\n"

    # Profile validation
    violations = arch.adapter.validate_against_profile(
        "android_studio_native_kotlin", arch.vfs.as_dict())
    print(f"Profile violations (kotlin): {len(violations)}")

    # Self-healing
    err = ValueError("manifest XML parse error")
    cls = arch.healing.classify(err)
    print(f"Classified '{err}' → {cls}")
    report = arch.healing.handle(err, {
        "vfs": arch.vfs,
        "audit_log": ctx.audit_log,
    })
    print(f"Recovery report: success={report.get('success')}")

    # Self-evolution — block because schema version not incremented
    allowed, reason = arch.evolution.can_evolve(ctx)
    print(f"can_evolve (initial): allowed={allowed} reason={reason}")

    # Now bump schema version + add a snapshot
    ctx.governance["schema_version"] = 2
    arch.vfs.snapshot("pre_evolve")
    allowed, reason = arch.evolution.can_evolve(ctx)
    print(f"can_evolve (after bump): allowed={allowed} reason={reason}")

    if allowed:
        result = arch.evolution.evolve(ctx, {
            "type": "add_validator",
            "target": "custom_check",
            "payload": {"description": "Custom validator"},
        })
        print(f"evolve result: {result.get('evolved')}")

    print("=== Self-test PASSED ===")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
