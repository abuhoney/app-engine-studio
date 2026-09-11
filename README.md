# App Engine Studio v10.0 — Unified

Real APK builder + studio.html dashboard in one system.

## Architecture

```
studio.html (dashboard) → POST /api/build → builder.py → REAL signed APK
```

## Backend

```
https://all-arab-services.onrender.com
```

### Endpoints

- `GET /health` — Health check
- `GET /index.html` — studio.html dashboard (1.5 MB)
- `POST /api/build` — Build REAL APK from HTML
  - Body: `{ appName, packageName, htmlContent, versionName, versionCode }`
  - Returns: `{ jobId, status: 'building' }`
- `GET /api/status/:jobId` — Check build status
- `GET /download/:filename` — Download built APK

## Builder

Uses `builder/` directory containing:
- `builder.py` — Main orchestrator
- `compiler.py` — Java → DEX compiler (aapt2/javac/d8)
- `packager.py` — APK packager (zipalign/apksigner)
- `config.json` — Tool paths + SDK config
- `templates/` — Android project template
- `scripts/` — Tool fetchers (SDK/JDK/Gradle)
- `keystore/debug.keystore` — Debug signing key

## Build Pipeline (REAL, not simulated)

1. User fills form in studio.html dashboard
2. Dashboard POSTs to `/api/build`
3. Server runs `builder.py` which:
   a. Creates workspace
   b. Copies Android project template
   c. Injects user's HTML as `webapp.html`
   d. Runs `aapt2 compile` + `aapt2 link`
   e. Runs `javac` (JDK 17)
   f. Runs `d8` (class → DEX)
   g. Merges DEX into APK
   h. Runs `zipalign`
   i. Runs `apksigner sign` (v1+v2)
4. Server responds with download URL
5. User downloads REAL signed APK

## APK

Dashboard APK: `apk/app-engine-studio.apk` (loads dashboard from backend)

## GitHub

https://github.com/abuhoney/app-engine-studio
