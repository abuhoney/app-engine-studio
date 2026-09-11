#!/usr/bin/env python3
"""
cli.py — Command-line interface for the BardomPro Universal App Generator.

Examples:
    # Show config summary
    python cli.py config

    # Build one APK from a prompt file
    python cli.py build --prompt my_prompt.txt --out MyApp.apk

    # Build from a template
    python cli.py build-template --template templates/template_001_calculator.json

    # Run the 100-template self-test
    python cli.py self-test

    # Start the Telegram bot
    python cli.py telegram

    # Push an APK to GitHub
    python cli.py push --apk MyApp.apk --name MyApp

    # Generate AI code for a feature
    python cli.py ai-code --feature "Login screen with email and password"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.config import get_config
from engine.prompt_parser import parse_prompt_file, parse_prompt_text
from engine.project_generator import generate_project
from engine.apk_builder import build_apk
from engine.code_generator import generate_feature_code, CodeGenerator
from engine.self_test import load_template, run_all


def cmd_config(args: argparse.Namespace) -> int:
    print(get_config().summary())
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    prompt_path = Path(args.prompt)
    if not prompt_path.exists():
        print(f"ERROR: prompt file not found: {prompt_path}")
        return 1
    manifest = parse_prompt_file(prompt_path)
    if args.name:
        manifest.app_name = args.name
    if args.package:
        manifest.package_name = args.package
    print(f"Parsed {len(manifest.features)} features from {prompt_path}")
    proj_dir = Path(args.project_dir or f"/tmp/{manifest.app_name}_project")
    generate_project(manifest, proj_dir)
    print(f"Generated project at {proj_dir}")
    out_apk = Path(args.out) if args.out else None
    result = build_apk(proj_dir, out_apk)
    if result.success:
        print(f"\n✅ APK built in {result.elapsed_seconds:.1f}s")
        print(f"   Signed APK: {result.signed_apk}")
        # Optional post-build hooks
        if args.firebase:
            try:
                from integrations.firebase_client import FirebaseClient
                FirebaseClient().record_build(manifest, result)
                print("   Recorded in Firebase.")
            except Exception as e:
                print(f"   Firebase skip: {e}")
        if args.push_github:
            try:
                from integrations.github_client import GitHubClient
                GitHubClient().push_apk(result.signed_apk, manifest.app_name)
                print("   Pushed to GitHub.")
            except Exception as e:
                print(f"   GitHub push skip: {e}")
        return 0
    else:
        print(f"\n❌ Build FAILED: {result.error}")
        print(result.log)
        return 1


def cmd_build_template(args: argparse.Namespace) -> int:
    tmpl_path = Path(args.template)
    if not tmpl_path.exists():
        print(f"ERROR: template not found: {tmpl_path}")
        return 1
    manifest = load_template(tmpl_path)
    print(f"Loaded template: {manifest.app_name} ({len(manifest.features)} features)")
    proj_dir = Path(args.project_dir or f"/tmp/{manifest.app_name}_project")
    generate_project(manifest, proj_dir)
    out_apk = Path(args.out) if args.out else None
    result = build_apk(proj_dir, out_apk)
    if result.success:
        print(f"✅ {manifest.app_name}.apk built in {result.elapsed_seconds:.1f}s")
        print(f"   {result.signed_apk}")
        return 0
    else:
        print(f"❌ FAILED: {result.error}")
        return 1


def cmd_self_test(args: argparse.Namespace) -> int:
    limit = int(args.limit) if args.limit else None
    report = run_all(limit=limit)
    return 0 if report.all_passed else 1


def cmd_telegram(args: argparse.Namespace) -> int:
    from integrations.telegram_bot import TelegramBot
    TelegramBot().run()
    return 0


def cmd_push(args: argparse.Namespace) -> int:
    from integrations.github_client import GitHubClient
    apk = Path(args.apk)
    if not apk.exists():
        print(f"ERROR: APK not found: {apk}")
        return 1
    GitHubClient().push_apk(apk, args.name)
    print(f"Pushed {apk} to GitHub.")
    return 0


def cmd_ai_code(args: argparse.Namespace) -> int:
    from engine.prompt_parser import Feature
    f = Feature(id="F-001", name=args.feature, description=args.feature)
    r = generate_feature_code(f, args.package)
    print(f"// source: {r.source}")
    if r.error:
        print(f"// error: {r.error}")
    print(r.code)
    return 0 if r.success else 0  # always 0 — fallback is acceptable


def cmd_render_deploy(args: argparse.Namespace) -> int:
    from integrations.render_client import RenderClient
    rc = RenderClient()
    if args.suspend:
        print(rc.suspend())
    elif args.resume:
        print(rc.resume())
    else:
        print(rc.trigger_deploy(clear_cache=args.clear_cache))
    return 0


def cmd_firebase_get(args: argparse.Namespace) -> int:
    from integrations.firebase_client import FirebaseClient
    fb = FirebaseClient()
    print(json.dumps(fb.get(args.path), indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="universal-app-generator",
        description="BardomPro Universal App Generator — build real Android APKs from prompts.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("config", help="Show resolved configuration").set_defaults(func=cmd_config)

    b = sub.add_parser("build", help="Build an APK from a prompt file")
    b.add_argument("--prompt", "-p", required=True, help="Path to prompt file (.txt/.md)")
    b.add_argument("--out", "-o", help="Output APK path")
    b.add_argument("--name", help="Override app name")
    b.add_argument("--package", help="Override package name")
    b.add_argument("--project-dir", help="Override generated project dir")
    b.add_argument("--firebase", action="store_true", help="Record build in Firebase")
    b.add_argument("--push-github", action="store_true",
                   help="Push APK to GitHub (ignored if AUTO_PUSH_GITHUB=false)")
    b.set_defaults(func=cmd_build)

    bt = sub.add_parser("build-template", help="Build an APK from a template JSON")
    bt.add_argument("--template", "-t", required=True)
    bt.add_argument("--out", "-o")
    bt.add_argument("--project-dir")
    bt.set_defaults(func=cmd_build_template)

    st = sub.add_parser("self-test", help="Run the 100-template self-test")
    st.add_argument("--limit", help="Only run first N templates")
    st.set_defaults(func=cmd_self_test)

    sub.add_parser("telegram", help="Start the Telegram bot (long-polling)").set_defaults(
        func=cmd_telegram)

    pu = sub.add_parser("push", help="Push an APK to GitHub")
    pu.add_argument("--apk", required=True)
    pu.add_argument("--name", default="GeneratedApp")
    pu.set_defaults(func=cmd_push)

    ac = sub.add_parser("ai-code", help="Generate Android Java code for a feature via Kimi K2")
    ac.add_argument("--feature", required=True, help="Feature description")
    ac.add_argument("--package", default="app.bardom.generated")
    ac.set_defaults(func=cmd_ai_code)

    rd = sub.add_parser("render", help="Trigger Render deploy / suspend / resume")
    rd.add_argument("--clear-cache", action="store_true")
    rd.add_argument("--suspend", action="store_true")
    rd.add_argument("--resume", action="store_true")
    rd.set_defaults(func=cmd_render_deploy)

    fg = sub.add_parser("firebase-get", help="Read a path from Firebase RTDB")
    fg.add_argument("path", default="", nargs="?")
    fg.set_defaults(func=cmd_firebase_get)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
