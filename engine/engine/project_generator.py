"""
project_generator.py — Turn a FeatureManifest into a complete Android project tree.

Output structure:
    out_dir/
        AndroidManifest.xml
        res/
            values/strings.xml
            values/colors.xml
            values/themes.xml
            layout/activity_main.xml
            mipmap-*/ic_launcher.png (optional)
        src/<package_path>/MainActivity.java
        src/<package_path>/...Feature.java (per feature)
        assets/   (any extra assets)
        build/    (created by apk_builder)

The generator is template-driven: for each feature it picks the matching
template under templates/ and renders it with the feature's variables.
"""
from __future__ import annotations

import shutil
import json
import re
from pathlib import Path
from typing import Optional

from .prompt_parser import FeatureManifest, Feature


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _package_to_path(package: str) -> Path:
    """app.bardom.generated -> app/bardom/generated"""
    return Path(*package.split("."))


def _safe_java_class(name: str) -> str:
    """Sanitize a string into a valid Java class identifier (CamelCase)."""
    parts = re.split(r"[^A-Za-z0-9]+", name)
    cls = "".join(p.capitalize() for p in parts if p)
    if not cls:
        cls = "Feature"
    if cls[0].isdigit():
        cls = "F" + cls
    return cls


# --------------------------------------------------------------------------- #
# Manifest writer
# --------------------------------------------------------------------------- #
MANIFEST_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package}"
    android:versionCode="1"
    android:versionName="{version}">

    <uses-sdk android:minSdkVersion="{min_sdk}" android:targetSdkVersion="{target_sdk}" />
    {permissions}

    <application
        android:label="@string/app_name"
        android:icon="@android:drawable/ic_menu_info_details"
        android:theme="@style/AppTheme"
        android:allowBackup="true">

        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        {extra_activities}
    </application>
</manifest>
"""


def _required_permissions(features: list[Feature]) -> list[str]:
    perms: list[str] = []
    seen = set()
    for f in features:
        cat = f.category
        hint = f.template_hint or ""
        text = (f.description + " " + f.name).lower()
        candidates: list[str] = []
        if "internet" in text or cat == "network" or cat == "ai" or hint == "webview":
            candidates.append("android.permission.INTERNET")
        if "camera" in text or hint in ("camera_app", "qr_scanner"):
            candidates.append("android.permission.CAMERA")
        if "location" in text or "gps" in text or hint == "location":
            candidates += [
                "android.permission.ACCESS_FINE_LOCATION",
                "android.permission.ACCESS_COARSE_LOCATION",
            ]
        if "bluetooth" in text:
            candidates += [
                "android.permission.BLUETOOTH",
                "android.permission.BLUETOOTH_ADMIN",
            ]
        if "notification" in text or cat == "system":
            candidates.append("android.permission.POST_NOTIFICATIONS")
        if "storage" in text or "file" in text:
            candidates += [
                "android.permission.READ_EXTERNAL_STORAGE",
                "android.permission.WRITE_EXTERNAL_STORAGE",
            ]
        if "microphone" in text or "speech" in text or "audio" in text:
            candidates.append("android.permission.RECORD_AUDIO")
        if "contacts" in text:
            candidates.append("android.permission.READ_CONTACTS")
        if "sms" in text:
            candidates.append("android.permission.SEND_SMS")
        for c in candidates:
            if c not in seen:
                seen.add(c)
                perms.append(c)
    return perms


def _perm_xml(perm: str) -> str:
    return f'<uses-permission android:name="{perm}" />'


# --------------------------------------------------------------------------- #
# Strings / colors / themes
# --------------------------------------------------------------------------- #
STRINGS_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{app_name}</string>
{feature_strings}
</resources>
"""

COLORS_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="colorPrimary">#0F62FE</color>
    <color name="colorPrimaryDark">#0043CE</color>
    <color name="colorAccent">#FF832B</color>
    <color name="white">#FFFFFFFF</color>
    <color name="black">#FF000000</color>
    <color name="background">#FFF5F5F5</color>
</resources>
"""

THEMES_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="@android:style/Theme.Material.Light.DarkActionBar">
        <item name="android:colorPrimary">@color/colorPrimary</item>
        <item name="android:colorPrimaryDark">@color/colorPrimaryDark</item>
        <item name="android:colorAccent">@color/colorAccent</item>
        <item name="android:windowBackground">@color/background</item>
    </style>
</resources>
"""


# --------------------------------------------------------------------------- #
# Main layout
# --------------------------------------------------------------------------- #
MAIN_LAYOUT_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<ScrollView xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:padding="16dp">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="vertical">

        <TextView
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="@string/app_name"
            android:textSize="24sp"
            android:textStyle="bold"
            android:paddingBottom="16dp" />
{feature_views}
    </LinearLayout>
</ScrollView>
"""

FEATURE_BUTTON_TEMPLATE = """        <Button
            android:id="@+id/{id}"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="{name}"
            android:layout_marginBottom="8dp" />
"""


# --------------------------------------------------------------------------- #
# Java source templates
# --------------------------------------------------------------------------- #
MAIN_ACTIVITY_TEMPLATE = """package {package};

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.Toast;
import android.content.Intent;

public class MainActivity extends Activity {{
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

{button_listeners}
    }}
}}
"""

FEATURE_ACTIVITY_TEMPLATE = """package {package};

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
        tv.setText("{description}");
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


# --------------------------------------------------------------------------- #
# Generator
# --------------------------------------------------------------------------- #
class ProjectGenerator:
    """Generate a complete Android project tree from a FeatureManifest."""

    def __init__(self, manifest: FeatureManifest, out_dir: Path):
        self.manifest = manifest
        self.out_dir = Path(out_dir)
        self.src_dir = self.out_dir / "src" / _package_to_path(manifest.package_name)
        self.res_dir = self.out_dir / "res"
        self.assets_dir = self.out_dir / "assets"

    def generate(self) -> Path:
        """Create the project tree. Returns the project root."""
        # 1. Recreate project dir
        if self.out_dir.exists():
            shutil.rmtree(self.out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.src_dir.mkdir(parents=True, exist_ok=True)
        (self.res_dir / "values").mkdir(parents=True, exist_ok=True)
        (self.res_dir / "layout").mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # 2. Write AndroidManifest.xml
        self._write_manifest()

        # 3. Write resource files
        self._write_strings()
        (self.res_dir / "values" / "colors.xml").write_text(COLORS_TEMPLATE,
                                                            encoding="utf-8")
        (self.res_dir / "values" / "themes.xml").write_text(THEMES_TEMPLATE,
                                                             encoding="utf-8")

        # 4. Write layout
        self._write_main_layout()

        # 5. Write MainActivity.java
        self._write_main_activity()

        # 6. Write one Activity per feature
        for f in self.manifest.features:
            self._write_feature_activity(f)

        # 7. Write a manifest.json for downstream tools
        meta = {
            "app_name": self.manifest.app_name,
            "package": self.manifest.package_name,
            "version": self.manifest.version,
            "min_sdk": self.manifest.min_sdk,
            "target_sdk": self.manifest.target_sdk,
            "features": [f.to_dict() for f in self.manifest.features],
            "generated_by": "BardomPro Universal App Generator v1.0.0",
        }
        (self.out_dir / "manifest.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.out_dir

    # ----------------------------------------------------------------- #
    def _write_manifest(self) -> None:
        perms = "\n    ".join(_perm_xml(p) for p in _required_permissions(self.manifest.features))
        extra_acts = ""
        for f in self.manifest.features:
            cls = _safe_java_class(f.name)
            extra_acts += f"""
        <activity android:name=".{cls}" android:exported="false" />"""
        text = MANIFEST_TEMPLATE.format(
            package=self.manifest.package_name,
            version=self.manifest.version,
            min_sdk=self.manifest.min_sdk,
            target_sdk=self.manifest.target_sdk,
            permissions=perms,
            extra_activities=extra_acts,
        )
        (self.out_dir / "AndroidManifest.xml").write_text(text, encoding="utf-8")

    def _write_strings(self) -> None:
        feat_strings = ""
        for f in self.manifest.features:
            sid = f"feat_{f.id.lower().replace('-', '_')}"
            desc = (f.description.replace('"', "'").replace("&", "&amp;"))
            feat_strings += f'    <string name="{sid}">{desc}</string>\n'
        text = STRINGS_TEMPLATE.format(
            app_name=self.manifest.app_name.replace('"', "'").replace("&", "&amp;"),
            feature_strings=feat_strings,
        )
        (self.res_dir / "values" / "strings.xml").write_text(text, encoding="utf-8")

    def _write_main_layout(self) -> None:
        views = ""
        for f in self.manifest.features:
            btn_id = f"btn_{f.id.lower().replace('-', '_')}"
            btn_text = (f.name.replace('"', "'").replace("&", "&amp;"))
            views += FEATURE_BUTTON_TEMPLATE.format(id=btn_id, name=btn_text)
        if not views:
            views = '        <TextView android:layout_width="match_parent"\n' \
                    '            android:layout_height="wrap_content"\n' \
                    '            android:text="No features defined" />\n'
        text = MAIN_LAYOUT_TEMPLATE.format(feature_views=views)
        (self.res_dir / "layout" / "activity_main.xml").write_text(text, encoding="utf-8")

    def _write_main_activity(self) -> None:
        listeners = ""
        for f in self.manifest.features:
            btn_id = f"btn_{f.id.lower().replace('-', '_')}"
            cls = _safe_java_class(f.name)
            listeners += (
                f'        Button btn_{f.id.lower().replace("-", "_")} = '
                f'findViewById(R.id.{btn_id});\n'
                f'        btn_{f.id.lower().replace("-", "_")}'
                f'.setOnClickListener(new View.OnClickListener() {{\n'
                f'            @Override public void onClick(View v) {{\n'
                f'                startActivity(new Intent(MainActivity.this, {cls}.class));\n'
                f'            }}\n'
                f'        }});\n\n'
            )
        if not listeners:
            listeners = "        // No features wired up.\n"
        text = MAIN_ACTIVITY_TEMPLATE.format(
            package=self.manifest.package_name,
            button_listeners=listeners.rstrip(),
        )
        (self.src_dir / "MainActivity.java").write_text(text, encoding="utf-8")

    def _write_feature_activity(self, f: Feature) -> None:
        cls = _safe_java_class(f.name)
        desc = f.description.replace('"', "'").replace("\\", "\\\\")
        text = FEATURE_ACTIVITY_TEMPLATE.format(
            package=self.manifest.package_name,
            class_name=cls,
            description=desc,
        )
        (self.src_dir / f"{cls}.java").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
def generate_project(manifest: FeatureManifest, out_dir: Path) -> Path:
    """Convenience wrapper."""
    return ProjectGenerator(manifest, out_dir).generate()


if __name__ == "__main__":
    from .prompt_parser import parse_prompt_text
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m engine.project_generator <prompt-file> <out-dir>")
        sys.exit(1)
    from .prompt_parser import parse_prompt_file
    m = parse_prompt_file(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/gen_app")
    proj = generate_project(m, out)
    print(f"Project generated at: {proj}")
