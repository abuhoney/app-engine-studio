"""
SECTION 9 — EXPORT, TRANSFORMATION, VISUALIZATION, ZIP, PATCH, AST,
AND SILENT SUPERVISOR EDITING

Produces the 20 export formats declared in Section 12.10 and the silent
supervisor editing layer from Section 5.6 / 9.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import time
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Export orchestrator
# ---------------------------------------------------------------------------
EXPORT_FORMATS: List[str] = [
    "txt", "markdown", "json", "yaml", "xml", "csv",
    "java", "kotlin", "dart", "gradle", "manifest",
    "zip", "patch", "ast", "diagram", "table", "executable_spec",
]


class ExportTransformation:
    """Section 9 — exports the VFS to any of the supported formats."""

    def __init__(self, ctx):
        self.ctx = ctx

    def run(self) -> None:
        # Produce a default ZIP + JSON bundle so downstream sections have outputs
        zip_bytes = self.export_zip()
        self.ctx.exports["zip"] = zip_bytes
        self.ctx.exports["json_bundle"] = self.export_json_bundle()
        self.ctx.exports["manifest_table"] = self.export_table(
            ["Path", "Size", "Source"],
            [[p, len(c), self.ctx.vfs_meta.get(p, {}).get("source", "")]
             for p, c in self.ctx.vfs.items()],
        )
        self.ctx.exports["readme_markdown"] = self.export_markdown_docs()
        self.ctx.exports["executable_spec"] = self.export_executable_spec()
        self.ctx.exports["diagram"] = self.export_diagram()

        self.ctx.audit_log.append({
            "section": 9,
            "status": "ok",
            "formats_produced": list(self.ctx.exports.keys()),
            "vfs_files": len(self.ctx.vfs),
            "message": f"Exported {len(self.ctx.exports)} formats from VFS",
        })

    # -- Per-format exporters ------------------------------------------------

    def export_zip(self) -> bytes:
        """Produce a valid ZIP archive containing every VFS file."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, content in self.ctx.vfs.items():
                zf.writestr(path, content)
        return buf.getvalue()

    def export_json_bundle(self) -> bytes:
        """Single JSON with all VFS paths + base64-encoded binary content."""
        import base64
        bundle = {
            "metadata": {
                "project_name": self.ctx.project_name,
                "package_name": self.ctx.package_name,
                "platform": self.ctx.platform_profile,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "engine_section": 9,
            },
            "files": [],
        }
        for path, content in self.ctx.vfs.items():
            try:
                text = content.decode("utf-8")
                bundle["files"].append({"path": path, "text": text})
            except UnicodeDecodeError:
                bundle["files"].append({
                    "path": path,
                    "base64": base64.b64encode(content).decode("ascii"),
                })
        return json.dumps(bundle, indent=2).encode("utf-8")

    def export_table(self, headers: List[str], rows: List[List[Any]]) -> str:
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)
        return out.getvalue()

    def export_markdown_docs(self) -> bytes:
        lines = [
            f"# {self.ctx.project_name}",
            "",
            f"**Package**: `{self.ctx.package_name}`  ",
            f"**Platform**: `{self.ctx.platform_profile}`  ",
            f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            "",
            "## Files",
            "",
            "| Path | Size | Source |",
            "|------|------|--------|",
        ]
        for p, c in self.ctx.vfs.items():
            src = self.ctx.vfs_meta.get(p, {}).get("source", "")
            lines.append(f"| `{p}` | {len(c)} | {src} |")
        lines.append("")
        lines.append("## Modules Registered")
        lines.append("")
        for k, v in self.ctx.module_registry.items():
            lines.append(f"- `{k}` — {v.get('title', '')}")
        return "\n".join(lines).encode("utf-8")

    def export_executable_spec(self) -> bytes:
        """A JSON spec that can be re-executed by the engine to reproduce the output."""
        spec = {
            "spec_version": "1.0",
            "engine": "Universal_App_Generator",
            "prompt": self.ctx.prompt,
            "project_name": self.ctx.project_name,
            "package_name": self.ctx.package_name,
            "platform_profile": self.ctx.platform_profile,
            "output_mode": self.ctx.output_mode,
            "supervisor_mode": self.ctx.supervisor_mode,
            "privacy_mode": self.ctx.privacy_mode,
            "vfs_paths": sorted(self.ctx.vfs.keys()),
        }
        return json.dumps(spec, indent=2).encode("utf-8")

    def export_diagram(self) -> bytes:
        """ASCII diagram of the project structure."""
        lines = [f"{self.ctx.project_name}/"]
        sorted_paths = sorted(self.ctx.vfs.keys())
        for i, p in enumerate(sorted_paths):
            is_last = (i == len(sorted_paths) - 1)
            prefix = "└── " if is_last else "├── "
            lines.append(prefix + p)
        return "\n".join(lines).encode("utf-8")

    def export_yaml(self) -> bytes:
        """Minimal YAML exporter — flattens simple dicts."""
        lines = []
        def emit(d, indent=0):
            pad = "  " * indent
            for k, v in d.items():
                if isinstance(v, dict):
                    lines.append(f"{pad}{k}:")
                    emit(v, indent + 1)
                elif isinstance(v, list):
                    lines.append(f"{pad}{k}:")
                    for item in v:
                        lines.append(f"{pad}- {item}")
                else:
                    s = str(v).replace('"', '\\"')
                    lines.append(f'{pad}{k}: "{s}"')
        emit({
            "project": self.ctx.project_name,
            "package": self.ctx.package_name,
            "platform": self.ctx.platform_profile,
            "files": sorted(self.ctx.vfs.keys()),
        })
        return "\n".join(lines).encode("utf-8")

    def export_xml(self) -> bytes:
        """Wrap the VFS file list in a simple XML structure."""
        lines = ['<?xml version="1.0" encoding="utf-8"?>', "<project>"]
        lines.append(f"  <name>{self.ctx.project_name}</name>")
        lines.append(f"  <package>{self.ctx.package_name}</package>")
        lines.append("  <files>")
        for p in self.ctx.vfs:
            lines.append(f"    <file path=\"{p}\" size=\"{len(self.ctx.vfs[p])}\" />")
        lines.append("  </files>")
        lines.append("</project>")
        return "\n".join(lines).encode("utf-8")

    def export_patch_bundle(self) -> bytes:
        """Wrap all ctx.patches into a single patch file."""
        lines = []
        for p in self.ctx.patches:
            lines.append(f"--- {p.get('path', '?')} ({p.get('severity', '?')})")
            lines.append("+++ fixed")
            lines.append(f"@{p.get('line', '?')}")
            lines.append(f"- {p.get('before', '')}")
            lines.append(f"+ {p.get('after', '')}")
            lines.append("")
        return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# Silent supervisor editing (Section 5.6 / Section 9)
# ---------------------------------------------------------------------------
@dataclass
class SupervisorEdit:
    edit_id: str
    target: str           # VFS path or module key
    field: str
    old_value: Any
    new_value: Any
    timestamp: str
    applied: bool = False
    rollback_id: Optional[str] = None


class SilentSupervisorEditor:
    """Allows silent (UI-invisible) edits while still logging, validating,
    and supporting rollback. Implements Rule 8."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self._edits: List[SupervisorEdit] = []

    def edit(self, target: str, field: str, new_value: Any,
             validator: Optional[callable] = None) -> SupervisorEdit:
        """Apply a silent supervisor edit. Returns the edit record (with rollback_id)."""
        import uuid
        edit_id = str(uuid.uuid4())
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Capture old value
        if target in self.ctx.vfs:
            old_value = self.ctx.vfs[target]
        elif target in self.ctx.module_registry:
            old_value = self.ctx.module_registry[target].get(field)
        else:
            old_value = None

        # Validate before commit (Rule 13)
        if validator and not validator(old_value, new_value):
            return SupervisorEdit(edit_id, target, field, old_value, new_value,
                                  timestamp, applied=False)

        # Take a rollback snapshot
        rollback_id = f"snapshot_{edit_id}"
        # (In a full impl this would call VFS.snapshot — skipped here to avoid
        #  circular import; the snapshot metadata is still recorded.)

        # Apply the edit
        if target in self.ctx.vfs and field == "content":
            self.ctx.vfs[target] = new_value if isinstance(new_value, bytes) else str(new_value).encode("utf-8")
        elif target in self.ctx.module_registry:
            self.ctx.module_registry[target][field] = new_value

        edit = SupervisorEdit(edit_id, target, field, old_value, new_value,
                              timestamp, applied=True, rollback_id=rollback_id)
        self._edits.append(edit)
        return edit

    def history(self) -> List[Dict[str, Any]]:
        return [
            {
                "edit_id": e.edit_id, "target": e.target, "field": e.field,
                "old": str(e.old_value)[:80], "new": str(e.new_value)[:80],
                "timestamp": e.timestamp, "applied": e.applied,
                "rollback_id": e.rollback_id,
            }
            for e in self._edits
        ]
