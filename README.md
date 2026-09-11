# App Engine Studio

Full Android app generator with v6.2 HTML, Ads Studio, Identity Shimming, Templates Gallery, JSON Tools, and HTML I/O.

## Backend

The backend runs on Render at: https://all-arab-services.onrender.com

### Endpoints

- `GET /health` — Health check
- `GET /api/config` — App config (Firebase, features)
- `POST /api/build-apk` — Queue APK build
- `GET /api/build-status/:jobId` — Check build status
- `GET /download/app-debug.apk` — Download built APK
- `GET /api/ads` — Ad config
- `GET /api/identity` — Identity config
- `POST /api/stats` — Record stats
- `GET /api/stats` — Get stats
- `POST /api/admin/commands` — Send admin command
- `GET /api/admin/commands/:deviceId` — Get pending commands
- `GET /studio.html` — The v6.2 HTML generator

## Frontend (HTML Generator)

The v6.2 HTML generator is at `backend/public/studio.html` (1.5 MB).

## APK

- `app-engine-studio.apk` — Android app with embedded v6.2 generator
- `demo-app-debug.apk` — Demo app (الدليل الشامل للخدمات)

## Architecture

```
GitHub Repo (abuhoney/app-engine-studio)
├── backend/
│   ├── server.js          (Express.js backend)
│   ├── package.json
│   └── public/
│       └── studio.html    (v6.2 HTML generator)
├── apk/
│   ├── app-engine-studio.apk
│   └── demo-app-debug.apk
├── .env.example
└── README.md
```

Render auto-deploys from `main` branch → `backend/` directory.

## License

MIT
