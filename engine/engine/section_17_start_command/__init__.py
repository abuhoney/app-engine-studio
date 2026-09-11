"""
SECTION 17 — START COMMAND

Final assembly — runs after all previous sections complete.
Writes the final summary, the executable spec, and a START.md
that explains how to re-execute the engine.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict


class StartCommand:
    """Section 17 — start command and final assembly."""

    def __init__(self, ctx):
        self.ctx = ctx

    def run(self) -> None:
        # Write the final START.md
        start_md = self._build_start_md()
        self.ctx.vfs["START.md"] = start_md.encode("utf-8")
        self.ctx.vfs_meta["START.md"] = {
            "source": "section_17_start_command",
            "generatorKey": "export.docs_exporter",
        }

        # Write the engine state snapshot
        state = {
            "snapshot_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": self.ctx.summary(),
            "module_count": len(self.ctx.module_registry),
            "vfs_count": len(self.ctx.vfs),
            "audit_log_count": len(self.ctx.audit_log),
            "patches_count": len(self.ctx.patches),
            "errors_count": len(self.ctx.errors),
            "exports_count": len(self.ctx.exports),
        }
        self.ctx.vfs["_engine_state.json"] = json.dumps(state, indent=2).encode("utf-8")
        self.ctx.vfs_meta["_engine_state.json"] = {
            "source": "section_17_start_command",
            "generatorKey": "core.state_manager",
        }

        self.ctx.audit_log.append({
            "section": 17,
            "status": "ok",
            "message": "START command executed — engine state snapshot + START.md written",
        })

    def _build_start_md(self) -> str:
        s = self.ctx.summary()
        return f"""# Universal App Generator — START

Generated project: **{s['project_name']}**  
Package: `{s['package_name']}`  
Platform: `{s['platform']}`  

## Engine state

- VFS files: **{s['vfs_files']}**
- Modules registered: **{s['modules_registered']}**
- Audit log entries: **{s['audit_entries']}**
- Repair patches: **{s['patches_generated']}**
- Exports produced: **{s['exports_produced']}**
- Errors collected: **{s['errors_collected']}**
- Total duration: **{s['duration_s']:.2f}s**

## Sections executed (0 → 17)

The engine executed every section of the master prompt in order:
  - Section 0: Execution Command (orchestrator)
  - Section 1: Language & Output Rules
  - Section 2: Primary Mission
  - Section 3: Engineering Rules
  - Section 4: Partitioned Structure
  - Section 5: Global Architecture (VFS + module registry + profiles + self-healing)
  - Section 6: Line-by-line Audit & Repair
  - Section 7: Android Project Generation (multi-category, multi-profile)
  - Section 8: Runtime Governance (consent, RBAC, audit, ads, kill switch)
  - Section 9: Export & Transformation (ZIP/JSON/YAML/XML/patch/diagram/docs)
  - Section 10: Self-Renewal (CI/CD + Termux/Linux + recovery)
  - Section 11: Acceptance Checklist
  - Section 12: Function Keys Registry
  - Section 13: 20-step Execution Steps
  - Section 14: Final Output Structure
  - Section 15: Strict Prohibitions Enforcer
  - Section 16: Definition of Done Validator
  - Section 16A: HTML Engine Studio + Universal DB Engine
  - Section 17: START command (this file)

## How to re-build

```bash
# Linux / macOS
make

# Termux
bash build_termux.sh

# GitHub Actions
# Push to main branch — workflow at .github/workflows/build.yml runs automatically
```

## How to extend

Edit any of the per-section modules under `engine/section_XX_*/__init__.py`
and re-run:

```python
from Universal_App_Generator.engine.section_00_execution_command import ExecutionCommand
ctx = ExecutionCommand(prompt="your new prompt", project_name="My App").run()
```

The engine is self-healing — any errors are routed through
`ctx.record_error()` and recorded in `_engine_state.json` under `errors_count`.
"""
