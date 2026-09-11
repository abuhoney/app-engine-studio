"""
BardomPro Universal App Generator — Engine Package

v3.0.0 — implements every section of the master prompt (Sections 0..17 + 16A).

Public API:
    from engine import build_app, ExecutionCommand, ExecutionContext
    ctx = build_app(prompt="...", project_name="My App")
"""
__version__ = "3.0.0"
__engine_dir__ = "Bardom engine v3"

# Re-export the top-level orchestrator
from .section_00_execution_command import ExecutionCommand, ExecutionContext  # noqa: F401


def build_app(prompt: str, project_name: str = "Generated App",
              package_name: str = "", platform_profile: str = "android_studio_native_java",
              **kwargs):
    """Single-call entrypoint — runs Sections 0..17 + 16A and returns the ExecutionContext."""
    if package_name:
        kwargs["package_name"] = package_name
    cmd = ExecutionCommand(
        prompt=prompt,
        project_name=project_name,
        platform_profile=platform_profile,
        **kwargs,
    )
    return cmd.run()
