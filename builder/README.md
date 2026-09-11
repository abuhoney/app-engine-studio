# Bardom-builder

> Offline-capable APK builder — the brain of the Bardom Platform v20 self-learning conversion engine.

## What it does

`Bardom-builder/` is a self-contained APK build toolkit that lives inside the `abuhoney/bardom` repo. It can build Android APKs from any HTML payload — even when GitHub Actions runners cannot reach the internet for SDK downloads — by caching the SDK, JDK, Gradle wrapper, build-tools, and a debug keystore directly in the repo (or fetching them on first run and then caching).

## Structure

```
Bardom-builder/
├── sdk/                              # Android SDK
│   ├── platform-tools/               # adb, aapt
│   ├── build-tools/34.0.0/           # aapt2, d8, zipalign, apksigner
│   ├── platforms/android-34/         # android.jar
│   └── cmdline-tools/                # sdkmanager
├── jdk/                              # JDK 17 (Temurin)
│   └── bin/javac                     # javac, java, jar, keytool
├── gradle/                           # Gradle 8.4
│   ├── wrapper/                      # gradle-wrapper.jar
│   ├── plugins/                      # AGP 8.1.4
│   └── gradle.properties             # offline-first settings
├── templates/                        # Project templates
│   ├── app/                          # Android app template
│   │   ├── AndroidManifest.xml
│   │   ├── src/main/java/.../MainActivity.java
│   │   ├── src/main/res/             # styles, colors, network security config
│   │   ├── src/main/assets/webapp.html
│   │   └── build.gradle
│   └── libs/                         # .aar / .jar libraries
├── keystore/
│   └── debug.keystore                # APK signing key
├── workspace/                        # Per-project build dirs
│   └── project_123/
├── scripts/                          # Tool fetch + maintenance scripts
│   ├── fetch_jdk.py
│   ├── fetch_gradle_wrapper.py
│   ├── fetch_build_tools.py
│   ├── fetch_platform_34.py
│   ├── generate_keystore.py
│   └── generate_template_icons.py
├── builder.py                        # Brain — orchestrates the whole pipeline
├── compiler.py                       # Calls aapt2 + javac + d8 (or gradle)
├── packager.py                       # zipalign + apksigner
├── config.json                       # Central path registry
├── build-apk-offline.yml             # GitHub Actions workflow
└── README.md                         # This file
```

## Build pipeline

Every build flows through these steps (recorded in `workspace/<project_id>/build_log.json`):

1. **validate_input** — confirm spec has `app_name`, `package_name`, `html_content`
2. **prepare_workspace** — create `workspace/<project_id>/`
3. **ensure_tools** — verify SDK/JDK/Gradle exist locally; fetch & cache if missing
4. **copy_template** — copy `templates/app/` into the project workspace
5. **inject_user_code** — write `AndroidManifest.xml`, `MainActivity.java`, `webapp.html`, `build.gradle`, `settings.gradle`, `gradle.properties`, `gradle-wrapper.{jar,properties}`, `gradlew`
6. **compile** — `compiler.py` runs `./gradlew assembleDebug` (or falls back to raw `aapt2 compile` → `aapt2 link` → `javac` → `d8`)
7. **package** — `packager.py` runs `zipalign` + `apksigner` (or `jarsigner` fallback)
8. **verify_apk** — `apksigner verify --print-certs`
9. **deliver** — return the final APK path (the bot backend sends it via Telegram)

## Offline capability

Two build paths are supported:

### Path A: Gradle (default, online-capable)
Used when the runner can reach `dl.google.com` and `services.gradle.org` (e.g., standard GitHub Actions). Runs `./gradlew assembleDebug` which handles the entire compile+package flow internally.

### Path B: Raw tools (offline)
Used when the runner is offline OR when the Android Gradle Plugin cannot be downloaded. Runs the tool chain directly:

```
aapt2 compile → aapt2 link → javac → d8 → (zip merge) → zipalign → apksigner
```

This requires `Bardom-builder/sdk/build-tools/34.0.0/` and `Bardom-builder/jdk/bin/` to be populated (cached). The fetch scripts handle that:

```bash
python3 Bardom-builder/scripts/fetch_jdk.py
python3 Bardom-builder/scripts/fetch_gradle_wrapper.py
python3 Bardom-builder/scripts/fetch_build_tools.py
python3 Bardom-builder/scripts/fetch_platform_34.py
python3 Bardom-builder/scripts/generate_keystore.py
```

After the first successful run, all tools are cached and subsequent builds work offline.

## Continuous learning

Each successful conversion records a JSON entry under `patterns/<command>/<timestamp>_<run_id>.json` on the repo. The pattern includes:
- `source_format`, `target_format`, `source_name`, `target_name`
- `package_name`, `target_size`
- `steps[]` — the exact pipeline steps used
- `commit_sha`, `run_id`, `run_number`, `timestamp`

After enough patterns accumulate (~10+), the bot backend can short-circuit identical future conversions by reusing the cached recipe.

## Bot integration

The Telegram bot (`server/index.js`) calls `builder.py` indirectly via the GitHub Actions workflow:

```
admin → /html_to_apk → bot → upload HTML to GitHub → trigger workflow →
workflow runs Bardom-builder → produces APK → upload artifact →
bot downloads artifact → sends APK to admin → logs pattern
```

The bot monitors build status every 20s (`monitoring_interval_seconds` in `config.json`) and reports progress back. If a build fails, `auto_correction: true` triggers an automatic retry with a different strategy (online→offline fallback, etc.).

## Adding a new conversion command

To add e.g. `/md_to_apk` (Markdown → APK):

1. In `server/index.js`, add to `CONVERSION_COMMANDS`:
   ```js
   { cmd: '/md_to_apk', source: 'md', target: 'apk', label: 'MD → APK' }
   ```

2. Add a handler:
   ```js
   async function handleMdToApkConversion(chatId, doc, fileName, baseName) {
     // 1. Convert MD → HTML (use marked or similar)
     // 2. Reuse handleHtmlToApkConversion() with the HTML payload
   }
   ```

3. The pattern logger will automatically record the conversion under `patterns/md_to_apk/`.

## License

Part of the Bardom Platform — proprietary to the abuhoney/bardom repo.
