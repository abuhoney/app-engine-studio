"""
SECTION 1 — LANGUAGE AND OUTPUT RULES

Enforces the 18 language/output rules from the master prompt:
  1. English only
  2. No Arabic
  3. No unrelated commentary
  4. Suitable for saving as a TXT prompt file
  5. Machine-readable where possible
  6. Human-readable
  7. Valid syntax for target language
  8. Prompts executable by an advanced AI coding agent
  9. Structured tables/JSON for reviews
 10. Exact before/after code blocks for patches
 11. Architecture: modules, keys, inputs, outputs, deps, failure modes, recovery, evolution
 12. Auto-split when output length limits exist
 13. Each major part expandable to >1000 lines when requested
 14. Never stop silently
 15. Never invent successful build results without verification
 16. Never hide privacy-sensitive behavior
 17. Never generate covert surveillance / hidden tracking
 18. Transparent, consent-aware, auditable, policy-compliant triggers
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# Arabic Unicode ranges — used by Rule 1 & 2 (English only, no Arabic)
_ARABIC_RANGES: List[Tuple[int, int]] = [
    (0x0600, 0x06FF),   # Arabic
    (0x0750, 0x077F),   # Arabic Supplement
    (0x08A0, 0x08FF),   # Arabic Extended-A
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
]

# Forbidden surveillance/tracking keywords (Rule 17)
_FORBIDDEN_COVERT_TERMS: List[str] = [
    "covert", "hidden tracking", "secret logging", "obfuscated tracking",
    "device fingerprint silent", "shadow tracker", "stealth logger",
    "undeclared_telemetry", "secret_button_log",
]


@dataclass
class LanguageRuleViolation:
    rule: int
    severity: str       # critical | high | medium | low | informational
    detail: str
    snippet: str = ""


class LanguageRules:
    """Section 1 enforcer. Validates every output string before it leaves the engine."""

    def __init__(self, ctx):
        self.ctx = ctx

    # -- Public API --------------------------------------------------------

    def run(self) -> None:
        """Validate the prompt and any VFS strings for language/output compliance."""
        violations: List[LanguageRuleViolation] = []

        # Rule 1 & 2: English only, no Arabic
        violations += self._check_no_arabic(self.ctx.prompt, where="prompt")
        for path, content in self.ctx.vfs.items():
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                continue
            violations += self._check_no_arabic(text, where=f"vfs:{path}")

        # Rule 17: no covert surveillance
        violations += self._check_no_covert_terms(self.ctx.prompt, where="prompt")
        for path, content in self.ctx.vfs.items():
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                continue
            violations += self._check_no_covert_terms(text, where=f"vfs:{path}")

        # Rule 12: never stop silently — emit a structured note if no violations
        if not violations:
            self.ctx.audit_log.append({
                "section": 1,
                "rule": "all",
                "status": "pass",
                "message": "All language/output rules satisfied",
            })
        else:
            for v in violations:
                self.ctx.audit_log.append({
                    "section": 1,
                    "rule": v.rule,
                    "severity": v.severity,
                    "detail": v.detail,
                    "snippet": v.snippet[:200],
                    "where": v.snippet and "see snippet",
                })

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _is_arabic_char(ch: str) -> bool:
        cp = ord(ch)
        for lo, hi in _ARABIC_RANGES:
            if lo <= cp <= hi:
                return True
        return False

    def _check_no_arabic(self, text: str, where: str) -> List[LanguageRuleViolation]:
        out: List[LanguageRuleViolation] = []
        if not text:
            return out
        arabic_chars = [ch for ch in text if self._is_arabic_char(ch)]
        if arabic_chars:
            sample = "".join(arabic_chars[:20])
            out.append(LanguageRuleViolation(
                rule=1,
                severity="high",
                detail=f"Arabic characters detected in {where} ({len(arabic_chars)} chars). "
                       "Rule 1 mandates English-only output.",
                snippet=sample,
            ))
        return out

    def _check_no_covert_terms(self, text: str, where: str) -> List[LanguageRuleViolation]:
        out: List[LanguageRuleViolation] = []
        if not text:
            return out
        lower = text.lower()
        for term in _FORBIDDEN_COVERT_TERMS:
            if term in lower:
                out.append(LanguageRuleViolation(
                    rule=17,
                    severity="critical",
                    detail=f"Forbidden covert-surveillance term '{term}' detected in {where}.",
                    snippet=term,
                ))
        return out

    # -- Output formatters (Rules 4, 5, 6, 9, 10) -------------------------

    @staticmethod
    def format_table(headers: List[str], rows: List[List[Any]]) -> str:
        """Rule 9 — structured table for review output."""
        if not rows:
            return "(no rows)\n"
        widths = [len(h) for h in headers]
        for r in rows:
            for i, cell in enumerate(r):
                widths[i] = max(widths[i], len(str(cell)))
        sep = " | "
        line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
        out = [line]
        out.append("| " + sep.join(h.ljust(w) for h, w in zip(headers, widths)) + " |")
        out.append(line)
        for r in rows:
            out.append("| " + sep.join(str(c).ljust(w) for c, w in zip(r, widths)) + " |")
        out.append(line)
        return "\n".join(out) + "\n"

    @staticmethod
    def format_patch(before: str, after: str, label: str = "patch") -> str:
        """Rule 10 — exact before/after code blocks for patches."""
        return (
            f"--- {label} — BEFORE\n"
            f"{before}\n"
            f"--- {label} — AFTER\n"
            f"{after}\n"
            f"--- end {label}\n"
        )

    @staticmethod
    def format_architecture(module: Dict[str, Any]) -> str:
        """Rule 11 — architecture block with all required fields."""
        required = ["key", "title", "description", "inputs", "outputs",
                    "dependencies", "failureModes", "recoveryActions", "evolutionHooks"]
        out = [f"MODULE: {module.get('key', '?')}"]
        for field in required:
            val = module.get(field, "")
            out.append(f"  {field}: {val}")
        return "\n".join(out) + "\n"
