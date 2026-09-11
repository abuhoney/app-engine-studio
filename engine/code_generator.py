"""
code_generator.py — AI-assisted code generation via OpenRouter Kimi K2.

Given a feature description, ask the AI to produce ready-to-paste Android
Java source code that implements it. Falls back to a deterministic template
if the AI call fails or AI_TOKEN is not configured.
"""
from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from .config import get_config
from .prompt_parser import Feature


SYSTEM_PROMPT = (
    "You are a senior Android engineer. Given a feature description, output "
    "production-ready Java source code for a single Activity class. "
    "Constraints:\n"
    "1. Use only the Android framework APIs (no third-party libraries).\n"
    "2. Target API 21+ (minSdk 21, targetSdk 34).\n"
    "3. The class must extend android.app.Activity and override onCreate.\n"
    "4. Output ONLY the Java source code in a single ```java fenced block.\n"
    "5. Use the package name provided.\n"
    "6. Keep it self-contained: no extra files, no resources beyond what "
    "can be created programmatically.\n"
)


@dataclass
class CodeGenResult:
    success: bool
    code: str
    source: str   # "ai" or "fallback"
    error: Optional[str] = None


class CodeGenerator:
    """Calls OpenRouter Kimi K2 to generate Android Java code."""

    def __init__(self, config=None):
        self.cfg = config or get_config()
        self.ai = self.cfg.ai

    # ----------------------------------------------------------------- #
    def generate_feature_activity(self, feature: Feature,
                                  package: str = "app.bardom.generated") -> CodeGenResult:
        """Ask the AI to write an Activity for one feature."""
        class_name = self._safe_class(feature.name)
        prompt = (
            f"Feature: {feature.name}\n"
            f"Description: {feature.description}\n"
            f"Category: {feature.category}\n"
            f"Priority: {feature.priority}\n"
            f"Package: {package}\n"
            f"Class name: {class_name}\n"
            f"Write the Activity Java source now."
        )
        return self._call_ai(prompt, package, class_name, feature.description)

    # ----------------------------------------------------------------- #
    def _call_ai(self, prompt: str, package: str,
                 class_name: str, fallback_desc: str) -> CodeGenResult:
        if not self.ai:
            return CodeGenResult(False, self._fallback(package, class_name, fallback_desc),
                                 "fallback", "AI not configured")
        body = {
            "model": self.ai.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.ai.temperature,
            "max_tokens": self.ai.max_tokens,
        }
        req = urllib.request.Request(
            self.ai.base_url,
            data=json.dumps(body).encode("utf-8"),
            headers=self.ai.auth_header,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = json.loads(r.read().decode("utf-8"))
            text = payload["choices"][0]["message"]["content"]
            code = self._extract_java_block(text)
            if not code:
                code = self._fallback(package, class_name, fallback_desc)
                return CodeGenResult(False, code, "fallback", "AI returned no code block")
            return CodeGenResult(True, code, "ai")
        except urllib.error.URLError as e:
            return CodeGenResult(False, self._fallback(package, class_name, fallback_desc),
                                 "fallback", f"AI request failed: {e}")
        except Exception as e:
            return CodeGenResult(False, self._fallback(package, class_name, fallback_desc),
                                 "fallback", f"AI error: {e}")

    # ----------------------------------------------------------------- #
    @staticmethod
    def _extract_java_block(text: str) -> str:
        m = re.search(r"```(?:java)?\s*\n(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _safe_class(name: str) -> str:
        parts = re.split(r"[^A-Za-z0-9]+", name)
        cls = "".join(p.capitalize() for p in parts if p) or "Feature"
        if cls[0].isdigit():
            cls = "F" + cls
        return cls

    @staticmethod
    def _fallback(package: str, class_name: str, description: str) -> str:
        desc = description.replace('"', "'").replace("\\", "\\\\")
        return f"""package {package};

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;
import android.widget.LinearLayout;
import android.view.ViewGroup.LayoutParams;

public class {class_name} extends Activity {{
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        TextView tv = new TextView(this);
        tv.setText("{desc}");
        tv.setTextSize(18);
        tv.setPadding(32, 32, 32, 32);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setLayoutParams(new LayoutParams(LayoutParams.MATCH_PARENT,
                                                 LayoutParams.MATCH_PARENT));
        layout.addView(tv);
        setContentView(layout);
    }}
}}
"""


def generate_feature_code(feature: Feature,
                          package: str = "app.bardom.generated") -> CodeGenResult:
    """Convenience wrapper."""
    return CodeGenerator().generate_feature_activity(feature, package)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m engine.code_generator <feature-description>")
        sys.exit(1)
    f = Feature(id="F-001", name=sys.argv[1], description=sys.argv[1])
    r = generate_feature_code(f)
    print(f"Source: {r.source}")
    print(r.code)
