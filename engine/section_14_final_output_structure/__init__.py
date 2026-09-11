"""
SECTION 14 — REQUIRED FINAL OUTPUT STRUCTURE

Assembles the final output bundle in the structure required by Section 14:
  1. Executive summary
  2. Critical issues found
  3. High-priority issues found
  4. Medium-priority issues found
  5. Low-priority issues found
  6. Line-by-line audit table
  7. Exact repair patches
  8. Refactored modular code
  9. Universal profile design
 10. Governance middleware
 11. Self-healing logic
 12. Export pipelines
 13. Test suite
 14. Documentation
 15. Acceptance report
 16. Continuation instruction (if any)
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


class FinalOutputStructure:
    def __init__(self, ctx):
        self.ctx = ctx

    def run(self) -> None:
        # Assemble the final output bundle as a single JSON document
        bundle: Dict[str, Any] = {
            "1_executive_summary": self._executive_summary(),
            "2_critical_issues": self._issues_by_severity("critical"),
            "3_high_issues": self._issues_by_severity("high"),
            "4_medium_issues": self._issues_by_severity("medium"),
            "5_low_issues": self._issues_by_severity("low"),
            "6_audit_table": self._audit_table(),
            "7_repair_patches": self._patches(),
            "8_modular_code": {
                "module_count": len(self.ctx.module_registry),
                "modules": list(self.ctx.module_registry.keys())[:200],
            },
            "9_profile_design": {
                "platform": self.ctx.platform_profile,
                "supported_profiles": [
                    "sketchware_pro", "android_studio_native_java",
                    "android_studio_native_kotlin", "flutter",
                    "termux_cli", "linux_cli", "github_actions",
                    "cloud_build", "google_ai_studio_spec",
                ],
            },
            "10_governance_middleware": self.ctx.governance,
            "11_self_healing_logic": {
                "errors_collected": len(self.ctx.errors),
                "audit_log_entries": len(self.ctx.audit_log),
            },
            "12_export_pipelines": {
                "formats_available": list(self.ctx.exports.keys()),
            },
            "13_test_suite": self.ctx.test_results,
            "14_documentation": {
                "readme_present": "README.md" in self.ctx.vfs,
                "vfs_files": len(self.ctx.vfs),
            },
            "15_acceptance_report": self.ctx.test_results.get("overall_pass", False),
            "16_continuation_instruction": "[OUTPUT COMPLETE]",
            "metadata": self.ctx.summary(),
        }

        # Write the bundle into the VFS
        bundle_bytes = json.dumps(bundle, indent=2, default=str).encode("utf-8")
        self.ctx.vfs["_final_output_bundle.json"] = bundle_bytes
        self.ctx.vfs_meta["_final_output_bundle.json"] = {
            "source": "section_14_final_output_structure",
            "generatorKey": "export.orchestrator",
        }
        self.ctx.exports["final_output_bundle"] = bundle_bytes

        self.ctx.audit_log.append({
            "section": 14,
            "status": "ok",
            "bundle_size_bytes": len(bundle_bytes),
            "sections_in_bundle": len(bundle),
            "message": "Final output bundle assembled",
        })

    # -- Helpers ------------------------------------------------------------

    def _executive_summary(self) -> Dict[str, Any]:
        return {
            "project_name": self.ctx.project_name,
            "package_name": self.ctx.package_name,
            "platform": self.ctx.platform_profile,
            "vfs_files": len(self.ctx.vfs),
            "modules_registered": len(self.ctx.module_registry),
            "audit_entries": len(self.ctx.audit_log),
            "patches_generated": len(self.ctx.patches),
            "errors_collected": len(self.ctx.errors),
            "acceptance_pass": self.ctx.test_results.get("overall_pass", False),
        }

    def _issues_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        out = []
        for entry in self.ctx.audit_log:
            if entry.get("severity") == severity:
                out.append(entry)
        return out

    def _audit_table(self) -> List[Dict[str, Any]]:
        # Top 50 entries to keep bundle size manageable
        return self.ctx.audit_log[:50]

    def _patches(self) -> List[Dict[str, Any]]:
        return self.ctx.patches
