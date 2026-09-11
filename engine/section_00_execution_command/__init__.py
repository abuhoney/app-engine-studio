"""
SECTION 0 — EXECUTION COMMAND

Autonomous senior Android software architect, code auditor, repair engine,
build-system expert, privacy-safe telemetry designer, and self-healing code
transformation system.

This module is the top-level "execution command" entry-point. It receives a
project spec (prompt + optional inputs) and orchestrates the entire pipeline
defined across Sections 1..17 of the master prompt.
"""
from __future__ import annotations

import os
import sys
import time
import json
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


# ---------------------------------------------------------------------------
# Supported platforms (Section 0 spec)
# ---------------------------------------------------------------------------
SUPPORTED_PLATFORMS: List[str] = [
    "sketchware_pro",
    "android_studio_native_java",
    "android_studio_native_kotlin",
    "flutter",
    "react_native_optional",
    "kotlin_multiplatform_optional",
    "ndk_cpp_optional",
    "termux_cli",
    "linux_cli",
    "github_actions",
    "cloud_build",
    "google_ai_studio_spec",
    "stitch_export_optional",
    "custom_internal_engine",
]


SUPPORTED_OUTPUT_MODES: List[str] = [
    "txt", "markdown", "json", "yaml", "xml",
    "java", "kotlin", "dart", "gradle", "manifest",
    "zip", "patch", "ast", "diagram", "table", "executable_spec",
]


# ---------------------------------------------------------------------------
# ExecutionContext — shared state passed through every Section module
# ---------------------------------------------------------------------------
@dataclass
class ExecutionContext:
    """State object threaded through every Section 0..17 module."""

    # Inputs
    prompt: str = ""
    project_name: str = ""
    package_name: str = ""
    app_icon_path: Optional[str] = None
    platform_profile: str = "android_studio_native_java"
    output_mode: str = "zip"
    supervisor_mode: str = "silent"        # silent | explicit
    privacy_mode: str = "transparent"      # transparent | hidden
    workdir: str = "/tmp/bardom_engine"

    # Virtual File System — populated by Section 5
    vfs: Dict[str, bytes] = field(default_factory=dict)
    vfs_meta: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Module registry — populated by Section 12
    module_registry: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Audit log — populated by Section 6
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    # Repair patches — populated by Section 6
    patches: List[Dict[str, Any]] = field(default_factory=list)

    # Generated Android project — populated by Section 7
    android_project: Dict[str, Any] = field(default_factory=dict)

    # Governance policy — populated by Section 8
    governance: Dict[str, Any] = field(default_factory=dict)

    # Exports — populated by Section 9
    exports: Dict[str, Any] = field(default_factory=dict)

    # Test results — populated by Section 11
    test_results: Dict[str, Any] = field(default_factory=dict)

    # Errors collected (never crash, always route to recovery)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Telemetry / metrics
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    def record_error(self, section: str, error: Exception, context: str = "") -> None:
        """Route every exception through the self-healing pipeline (Rule 10)."""
        self.errors.append({
            "section": section,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "traceback": traceback.format_exc(),
            "timestamp": time.time(),
        })

    def summary(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "package_name": self.package_name,
            "platform": self.platform_profile,
            "vfs_files": len(self.vfs),
            "modules_registered": len(self.module_registry),
            "audit_entries": len(self.audit_log),
            "patches_generated": len(self.patches),
            "exports_produced": len(self.exports),
            "errors_collected": len(self.errors),
            "duration_s": (self.finished_at or time.time()) - self.started_at,
        }


# ---------------------------------------------------------------------------
# ExecutionCommand — the top-level orchestrator
# ---------------------------------------------------------------------------
class ExecutionCommand:
    """
    The autonomous architect described in Section 0.

    Calling `.run()` executes Sections 1..17 in order, threading a single
    ExecutionContext through every module. Errors are never raised to the
    caller — they are routed to the self-healing layer (Rule 10) and recorded
    in ctx.errors.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.ctx = ExecutionContext(**kwargs)
        self._steps: List[Dict[str, Any]] = []

    # -- public API --------------------------------------------------------

    def run(self) -> ExecutionContext:
        """Execute the entire Section 0..17 pipeline."""
        # Local imports keep import time low and avoid circulars.
        from ..section_01_language_rules import LanguageRules
        from ..section_02_primary_mission import PrimaryMission
        from ..section_03_engineering_rules import EngineeringRules
        from ..section_04_partitioned_structure import PartitionedStructure
        from ..section_05_global_architecture import GlobalArchitecture
        from ..section_06_line_audit_repair import LineAuditRepair
        from ..section_07_android_project_generation import AndroidProjectGeneration
        from ..section_08_runtime_governance import RuntimeGovernance
        from ..section_09_export_transformation import ExportTransformation
        from ..section_10_self_renewal import SelfRenewal
        from ..section_11_acceptance_checklist import AcceptanceChecklist
        from ..section_12_function_keys import FunctionKeys
        from ..section_13_execution_steps import ExecutionSteps
        from ..section_14_final_output_structure import FinalOutputStructure
        from ..section_15_strict_prohibitions import StrictProhibitions
        from ..section_16_definition_of_done import DefinitionOfDone
        from ..section_16a_html_engine_studio import HtmlEngineStudio
        from ..section_17_start_command import StartCommand

        steps: List[Dict[str, Any]] = [
            {"section": 1,  "name": "Language & Output Rules",           "runner": LanguageRules(self.ctx)},
            {"section": 2,  "name": "Primary Mission",                    "runner": PrimaryMission(self.ctx)},
            {"section": 3,  "name": "Engineering Rules",                  "runner": EngineeringRules(self.ctx)},
            {"section": 4,  "name": "Partitioned Structure",              "runner": PartitionedStructure(self.ctx)},
            {"section": 5,  "name": "Global Architecture & VFS",          "runner": GlobalArchitecture(self.ctx)},
            {"section": 6,  "name": "Line-by-Line Audit & Repair",        "runner": LineAuditRepair(self.ctx)},
            {"section": 7,  "name": "Android Project Generation",         "runner": AndroidProjectGeneration(self.ctx)},
            {"section": 8,  "name": "Runtime Governance",                 "runner": RuntimeGovernance(self.ctx)},
            {"section": 9,  "name": "Export & Transformation",            "runner": ExportTransformation(self.ctx)},
            {"section": 10, "name": "Self-Renewal & CI/CD",               "runner": SelfRenewal(self.ctx)},
            {"section": 11, "name": "Acceptance Checklist",               "runner": AcceptanceChecklist(self.ctx)},
            {"section": 12, "name": "Function Keys Registry",             "runner": FunctionKeys(self.ctx)},
            {"section": 13, "name": "Execution Steps (20-step)",          "runner": ExecutionSteps(self.ctx)},
            {"section": 14, "name": "Final Output Structure",             "runner": FinalOutputStructure(self.ctx)},
            {"section": 15, "name": "Strict Prohibitions Enforcer",       "runner": StrictProhibitions(self.ctx)},
            {"section": 16, "name": "Definition of Done Validator",       "runner": DefinitionOfDone(self.ctx)},
            {"section": 16, "name": "HTML Engine Studio & Universal DB",  "runner": HtmlEngineStudio(self.ctx)},
            {"section": 17, "name": "Start Command (final assembly)",     "runner": StartCommand(self.ctx)},
        ]

        for step in steps:
            try:
                step["runner"].run()
                step["status"] = "ok"
            except Exception as exc:
                step["status"] = "error"
                step["error"] = str(exc)
                self.ctx.record_error(f"section_{step['section']}", exc, step["name"])
                # Rule 10: never crash — continue to next section in safe mode
                continue
            self._steps.append(step)

        self.ctx.finished_at = time.time()
        return self.ctx

    def steps_summary(self) -> List[Dict[str, Any]]:
        return [
            {"section": s["section"], "name": s["name"], "status": s.get("status", "?")}
            for s in self._steps
        ]


# ---------------------------------------------------------------------------
# CLI entry-point — `python -m engine.section_00_execution_command "prompt"`
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Usage: python -m engine.section_00_execution_command '<prompt>' [--name NAME] "
              "[--platform android_studio_native_java]")
        return 2

    prompt = argv[0]
    name = "Generated App"
    platform = "android_studio_native_java"
    for i, arg in enumerate(argv[1:], 1):
        if arg == "--name" and i + 1 < len(argv):
            name = argv[i + 1]
        elif arg == "--platform" and i + 1 < len(argv):
            platform = argv[i + 1]

    cmd = ExecutionCommand(prompt=prompt, project_name=name, platform_profile=platform)
    ctx = cmd.run()

    print("\n=== Execution Summary ===")
    print(json.dumps(ctx.summary(), indent=2))
    print("\n=== Steps ===")
    for s in cmd.steps_summary():
        print(f"  [{s['status']}] Section {s['section']}: {s['name']}")

    return 0 if not ctx.errors else 1


if __name__ == "__main__":
    sys.exit(main())
