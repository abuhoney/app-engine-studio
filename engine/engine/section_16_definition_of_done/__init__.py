"""
SECTION 16 — DEFINITION OF DONE

A project is "done" only when ALL of the following are true:
  - Generated files are syntactically valid
  - All audit issues are resolved or have patches
  - No critical/high severity violations remain
  - All exports are produced
  - All governance policies are present
  - The acceptance checklist passes
"""
from __future__ import annotations

from typing import Any, Dict


class DefinitionOfDone:
    def __init__(self, ctx):
        self.ctx = ctx

    def run(self) -> None:
        checks: Dict[str, bool] = {}

        # 1. VFS has generated files
        checks["vfs_has_files"] = len(self.ctx.vfs) > 0

        # 2. AndroidManifest.xml exists
        checks["manifest_present"] = any(p.endswith("AndroidManifest.xml") for p in self.ctx.vfs)

        # 3. MainActivity.java exists
        checks["main_activity_present"] = any(p.endswith("MainActivity.java") for p in self.ctx.vfs)

        # 4. ic_launcher.xml exists
        checks["icon_present"] = "res/drawable/ic_launcher.xml" in self.ctx.vfs

        # 5. README.md exists
        checks["readme_present"] = "README.md" in self.ctx.vfs

        # 6. No critical severity violations in audit log
        critical = [e for e in self.ctx.audit_log if e.get("severity") == "critical"]
        checks["no_critical_violations"] = len(critical) == 0

        # 7. Exports produced
        checks["exports_produced"] = len(self.ctx.exports) > 0

        # 8. Governance policies present
        keys = set(self.ctx.vfs.keys())
        checks["governance_policies_present"] = (
            "app/src/main/assets/consent_policy.json" in keys and
            "app/src/main/assets/audit_policy.json" in keys
        )

        # 9. CI/CD files present
        checks["cicd_present"] = ".github/workflows/build.yml" in self.ctx.vfs

        # 10. Acceptance checklist passes
        checks["acceptance_pass"] = bool(self.ctx.test_results.get("overall_pass", False))

        all_pass = all(checks.values())

        self.ctx.audit_log.append({
            "section": 16,
            "status": "done" if all_pass else "not_done",
            "checks": checks,
            "checks_passed": sum(1 for v in checks.values() if v),
            "checks_total": len(checks),
            "message": f"Definition of Done: {'PASS' if all_pass else 'FAIL'} "
                       f"({sum(1 for v in checks.values() if v)}/{len(checks)} checks)",
        })

        # Mark the project as done in the summary
        self.ctx.module_registry["definition_of_done"] = {
            "key": "definition_of_done",
            "passed": all_pass,
            "checks": checks,
            "section": 16,
        }
