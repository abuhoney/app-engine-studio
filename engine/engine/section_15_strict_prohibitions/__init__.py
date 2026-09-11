"""
SECTION 15 — STRICT PROHIBITIONS

Enforces the strict prohibitions from Section 15 of the master prompt.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


# Prohibition patterns — each is a (rule_name, regex, severity, action) tuple
PROHIBITIONS: List[Dict[str, Any]] = [
    {
        "name": "no_hidden_tracking",
        "pattern": r"(?:covert|stealth|hidden|secret|undeclared)[_ ]*(?:tracking|logging|surveillance|logger)",
        "severity": "critical",
        "action": "block_file",
        "description": "No hidden tracking, covert surveillance, or secret button logging",
    },
    {
        "name": "no_obfuscated_data_collection",
        "pattern": r"obfuscate[_ ]*(?:data|tracking|collection|telemetry)",
        "severity": "critical",
        "action": "block_file",
        "description": "No obfuscated data collection",
    },
    {
        "name": "no_secret_logging",
        "pattern": r"(?:console|log)\.[a-z]+\([^)]*secret[^)]*\)",
        "severity": "high",
        "action": "redact_line",
        "description": "No logging of secrets",
    },
    {
        "name": "no_hardcoded_credentials",
        "pattern": r"(?:password|passwd|api_key|apikey|secret_key)\s*=\s*[\"'][A-Za-z0-9+/=_-]{8,}[\"']",
        "severity": "high",
        "action": "redact_line",
        "description": "No hardcoded credentials in source",
    },
    {
        "name": "no_fake_completion",
        "pattern": r"(?:build|test|deploy)[_ ]*success\s*=\s*true\s*(?://.*)?$",
        "severity": "high",
        "action": "warn",
        "description": "No fake completion markers — verify before claiming success",
    },
    {
        "name": "no_silent_destructive_edit",
        "pattern": r"(?:rm\s+-rf\s+/?|DROP\s+TABLE|DELETE\s+FROM\s+\w+\s*;)",
        "severity": "high",
        "action": "block_file",
        "description": "No silent destructive edits without confirmation",
    },
    {
        "name": "no_arabic_in_output",
        "pattern": r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]",
        "severity": "medium",
        "action": "warn",
        "description": "Output must be English only (Rule 1, Section 1)",
    },
]


class StrictProhibitions:
    def __init__(self, ctx):
        self.ctx = ctx

    def run(self) -> None:
        violations: List[Dict[str, Any]] = []

        for path, content in self.ctx.vfs.items():
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                for rule in PROHIBITIONS:
                    if re.search(rule["pattern"], line, re.IGNORECASE):
                        violations.append({
                            "rule": rule["name"],
                            "severity": rule["severity"],
                            "action": rule["action"],
                            "path": path,
                            "line": line_no,
                            "snippet": line[:120],
                            "description": rule["description"],
                        })

        # Record violations
        for v in violations:
            self.ctx.audit_log.append({
                "section": 15,
                "rule": v["rule"],
                "severity": v["severity"],
                "path": v["path"],
                "line": v["line"],
                "detail": v["description"],
                "snippet": v["snippet"],
            })

        # Register prohibition rules in module registry
        for rule in PROHIBITIONS:
            key = f"prohibition.{rule['name']}"
            self.ctx.module_registry[key] = {
                "key": key,
                "title": rule["name"].replace("_", " ").title(),
                "description": rule["description"],
                "severity": rule["severity"],
                "action": rule["action"],
                "pattern": rule["pattern"],
                "section": 15,
            }

        self.ctx.audit_log.append({
            "section": 15,
            "status": "ok" if not violations else "violations_found",
            "prohibitions_enforced": len(PROHIBITIONS),
            "violations_count": len(violations),
            "message": f"Strict prohibitions: {len(PROHIBITIONS)} rules enforced, "
                       f"{len(violations)} violations found",
        })
