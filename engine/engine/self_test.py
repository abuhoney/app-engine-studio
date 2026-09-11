"""
self_test.py — 100-template self-test runner.

For each template under templates/:
    1. Parse the template JSON
    2. Generate an Android project tree
    3. Build a signed APK
    4. Verify the APK
    5. Record pass/fail in a report

If REQUIRE_100_TEST_PASS=true (default), the runner exits with code 1
unless every template built successfully. This gate protects against
pushing a broken APK-maker to GitHub.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from .config import get_config
from .prompt_parser import FeatureManifest, Feature, parse_prompt_text
from .project_generator import generate_project
from .apk_builder import build_apk


@dataclass
class TestResult:
    template_id: str
    template_name: str
    success: bool
    apk_path: Optional[str]
    elapsed_seconds: float
    feature_count: int
    error: Optional[str] = None


@dataclass
class TestReport:
    total: int
    passed: int
    failed: int
    elapsed_seconds: float
    results: list[TestResult]
    all_passed: bool

    def to_json(self, path: Path) -> None:
        d = asdict(self)
        path.write_text(json.dumps(d, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    def summary(self) -> str:
        lines = [
            "=" * 60,
            f"Self-test Report: {self.passed}/{self.total} passed "
            f"({self.failed} failed) in {self.elapsed_seconds:.1f}s",
            "=" * 60,
        ]
        for r in self.results:
            mark = "✅" if r.success else "❌"
            lines.append(f"{mark} {r.template_id} {r.template_name} "
                         f"({r.feature_count} feats, {r.elapsed_seconds:.1f}s)")
            if not r.success and r.error:
                lines.append(f"     ERROR: {r.error[:200]}")
        lines.append("=" * 60)
        lines.append(f"ALL PASSED: {self.all_passed}")
        return "\n".join(lines)


def load_template(path: Path) -> FeatureManifest:
    """Convert a template JSON file into a FeatureManifest."""
    data = json.loads(path.read_text(encoding="utf-8"))
    manifest = FeatureManifest(
        source_path=path,
        title=data.get("name", "Universal App"),
        package_name=data.get("package", "app.bardom.generated"),
        app_name=data.get("name", "Generated App"),
        version=data.get("version", "1.0.0"),
        min_sdk=data.get("min_sdk", 21),
        target_sdk=data.get("target_sdk", 34),
    )
    for idx, feat_desc in enumerate(data.get("features", []), start=1):
        manifest.features.append(Feature(
            id=f"F-{idx:03d}",
            name=feat_desc[:60],
            description=feat_desc,
            raw_line=feat_desc,
            category="general",
        ))
    return manifest


def run_one(template_path: Path, out_root: Path) -> TestResult:
    """Generate + build a single template."""
    t0 = time.time()
    try:
        manifest = load_template(template_path)
        proj_dir = out_root / template_path.stem
        generate_project(manifest, proj_dir)
        apk_out = proj_dir / "build" / "apk" / f"{manifest.app_name}.apk"
        result = build_apk(proj_dir, out_apk=apk_out)
        return TestResult(
            template_id=template_path.stem,
            template_name=manifest.app_name,
            success=result.success,
            apk_path=str(result.signed_apk) if result.signed_apk else None,
            elapsed_seconds=time.time() - t0,
            feature_count=len(manifest.features),
            error=result.error,
        )
    except Exception as e:
        return TestResult(
            template_id=template_path.stem,
            template_name=template_path.stem,
            success=False,
            apk_path=None,
            elapsed_seconds=time.time() - t0,
            feature_count=0,
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        )


def run_all(templates_dir: Optional[Path] = None,
            out_root: Optional[Path] = None,
            limit: Optional[int] = None) -> TestReport:
    """Run the full 100-template self-test."""
    cfg = get_config()
    templates_dir = templates_dir or (cfg.project_root / "templates")
    out_root = out_root or (cfg.project_root / "self_test_output")
    out_root.mkdir(parents=True, exist_ok=True)

    templates = sorted(templates_dir.glob("template_*.json"))
    if limit:
        templates = templates[:limit]

    t0 = time.time()
    results: list[TestResult] = []
    for i, t in enumerate(templates, start=1):
        print(f"\n[{i}/{len(templates)}] {t.name}", flush=True)
        r = run_one(t, out_root)
        results.append(r)
        if r.success:
            print(f"  ✅ {r.template_name} built in {r.elapsed_seconds:.1f}s")
        else:
            print(f"  ❌ {r.template_name} FAILED: {r.error[:200] if r.error else ''}")

    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    report = TestReport(
        total=len(results),
        passed=passed,
        failed=failed,
        elapsed_seconds=time.time() - t0,
        results=results,
        all_passed=(failed == 0),
    )

    # Save report
    report_path = out_root / "self_test_report.json"
    report.to_json(report_path)
    print(f"\nReport saved to {report_path}")
    print(report.summary())

    # Honor the safety gate
    if cfg.require_100_test_pass and not report.all_passed:
        print("\n⚠️  REQUIRE_100_TEST_PASS=true — self-test FAILED.")
        print("    AUTO_PUSH_GITHUB will be blocked until all templates pass.")
    return report


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    report = run_all(limit=limit)
    sys.exit(0 if report.all_passed or not cfg.require_100_test_pass else 1) \
        if False else sys.exit(0 if report.all_passed else 1)
