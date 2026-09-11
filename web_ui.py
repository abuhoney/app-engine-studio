#!/usr/bin/env python3
"""
web_ui.py — Flask web UI for the BardomPro Universal App Generator.

NEW in this version (vs. previous):
  - `select type app` dropdown replaces the free-text prompt area.
    Choices: JSON to Apk | Html To Apk | Zip To Apk | Music to Apk |
             Photos to Apk | Video to Apk | Image to Apk
  - Multi-file upload page for Music / Photos / Video (repeat row N times).
  - Per-type build endpoints under /api/build-<type>
  - Files are converted to base64 -> binary -> real playable assets.
  - Render is fully OPTIONAL — /api/render/health shows live status.
  - /dashboard shows the ControlCenter (ads / stats / monitoring) for
    every generated app.

Endpoints:
    GET  /                       — Home with app-type selector
    POST /api/build-prompt       — legacy free-text prompt
    POST /api/build-template     — by template ID
    POST /api/build-image-apk    — JSON manifest → image gallery APK
    POST /api/build-music-apk    — music files → music player APK
    POST /api/build-photos-apk   — photos → gallery APK
    POST /api/build-video-apk    — videos → video player APK
    POST /api/build-json-apk     — JSON config → APK
    POST /api/build-html-apk     — HTML → APK
    POST /api/build-zip-apk      — ZIP → APK
    GET  /dashboard              — ControlCenter (ads, stats, monitoring)
    GET  /api/control/apps       — list registered apps
    POST /api/control/apps/<id>/ads  — update ad config
    GET  /api/control/stats      — global stats
    GET  /api/render/health      — Render availability probe
    GET  /download/<file>        — Download a built APK
    GET  /templates              — list available templates
    GET  /api/config             — JSON config summary (no secrets)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import shutil
import zipfile
import io
from pathlib import Path
from typing import Optional

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.config import get_config
from engine.prompt_parser import parse_prompt_text
from engine.project_generator import generate_project
from engine.apk_builder import build_apk
from engine.self_test import load_template

# Optional Flask import
try:
    from flask import (Flask, request, jsonify, send_file,
                       render_template_string)
    HAVE_FLASK = True
except ImportError:
    HAVE_FLASK = False
    print("Flask not installed. Install with: pip install flask")
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import urllib.parse

APP_PORT = int(os.environ.get("PORT", "3000"))
cfg = get_config()
BUILD_DIR = cfg.project_root / "web_builds"
BUILD_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------- #
# App types offered in the `select type app` dropdown
# --------------------------------------------------------------------- #
APP_TYPES = [
    {"id": "json",   "label": "JSON to Apk",   "icon": "📋",
     "desc": "Generate an APK from a JSON manifest",
     "accept": ".json",          "multi": False},
    {"id": "html",   "label": "Html To Apk",   "icon": "🌐",
     "desc": "Wrap HTML/CSS/JS inside a WebView APK",
     "accept": ".html,.htm",     "multi": False},
    {"id": "zip",    "label": "Zip To Apk",    "icon": "📦",
     "desc": "Bundle a ZIP of assets into an APK",
     "accept": ".zip",           "multi": False},
    {"id": "music",  "label": "Music to Apk",  "icon": "🎵",
     "desc": "Build a music player APK from audio files",
     "accept": "audio/*",        "multi": True},
    {"id": "photos", "label": "Photos to Apk", "icon": "🖼",
     "desc": "Build an image gallery APK from photos",
     "accept": "image/*",        "multi": True},
    {"id": "video",  "label": "Video to Apk",  "icon": "🎬",
     "desc": "Build a video player APK from video files",
     "accept": "video/*",        "multi": True},
    {"id": "image",  "label": "Image to Apk",  "icon": "🎨",
     "desc": "Advanced image pipeline (base64 → binary → real PNG)",
     "accept": "image/*",        "multi": True},
]

# --------------------------------------------------------------------- #
HTML_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BardomPro Universal App Generator</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         margin: 0; padding: 0; background: #0d1117; color: #c9d1d9; }
  header { background: #161b22; padding: 16px 24px; border-bottom: 1px solid #30363d;
           display: flex; justify-content: space-between; align-items: center; }
  header h1 { margin: 0; font-size: 20px; color: #58a6ff; }
  header .nav a { color: #8b949e; text-decoration: none; margin-left: 16px; font-size: 13px; }
  header .nav a:hover { color: #58a6ff; }
  main { max-width: 1100px; margin: 24px auto; padding: 0 16px; }
  .grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 16px; }
  @media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }
  .card { background: #161b22; padding: 16px; border-radius: 8px;
          border: 1px solid #30363d; margin-bottom: 16px; }
  .card h3 { margin: 0 0 12px; color: #58a6ff; font-size: 14px; }
  label { display: block; margin: 10px 0 4px; font-size: 13px; color: #8b949e; }
  input[type="text"], input[type="file"], textarea, select {
    width: 100%; background: #0d1117; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 6px; padding: 10px;
    font-family: inherit; font-size: 13px; }
  textarea { height: 120px; font-family: ui-monospace, monospace; }
  button { background: #238636; color: white; border: none;
           padding: 10px 20px; border-radius: 6px; font-size: 14px;
           cursor: pointer; margin-top: 12px; }
  button:hover { background: #2ea043; }
  button.secondary { background: #21262d; color: #c9d1d9; }
  button.secondary:hover { background: #30363d; }
  .type-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
  .type-card { background: #0d1117; padding: 14px; border-radius: 8px;
               border: 1px solid #30363d; cursor: pointer; transition: all 0.15s; }
  .type-card:hover { border-color: #58a6ff; background: #161b22; }
  .type-card.selected { border-color: #58a6ff; background: #161b22;
                         box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15); }
  .type-card .icon { font-size: 28px; display: block; margin-bottom: 8px; }
  .type-card .title { font-weight: 600; color: #c9d1d9; font-size: 14px; }
  .type-card .desc { font-size: 11px; color: #8b949e; margin-top: 4px; }
  #files-area { display: none; }
  .file-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
  .file-row input { flex: 1; }
  .file-row button { margin: 0; padding: 6px 10px; background: #da3633; }
  pre { background: #0d1117; padding: 12px; border-radius: 6px;
        overflow-x: auto; color: #8b949e; font-size: 12px; max-height: 240px; overflow-y: auto; }
  #status { margin-top: 16px; padding: 12px; background: #161b22;
            border-radius: 6px; display: none; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
           font-size: 11px; margin-left: 6px; }
  .badge.ok { background: #1f6f3c; color: white; }
  .badge.warn { background: #9e6a03; color: white; }
  .badge.err { background: #da3633; color: white; }
  .tmpl-list { max-height: 320px; overflow-y: auto; }
  .tmpl-list a { color: #58a6ff; text-decoration: none; display: block;
                 padding: 6px 0; font-size: 13px; border-bottom: 1px solid #21262d; }
  .tmpl-list a:hover { color: #79c0ff; }
</style>
</head>
<body>
<header>
  <h1> BardomPro Universal App Generator</h1>
  <div class="nav">
    <a href="/">Home</a>
    <a href="/dashboard">Dashboard</a>
    <a href="/templates">Templates</a>
    <a href="/api/config">Config</a>
  </div>
</header>
<main>
  <div class="card">
    <h3>إعدادات التطبيق الرئيسي</h3>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 12px;">
      <div>
        <label>اسم التطبيق</label>
        <input type="text" id="app_name" placeholder="My Gallery">
      </div>
      <div>
        <label>أيقونة التطبيق (PNG)</label>
        <input type="file" id="app_icon" accept="image/png,image/jpeg">
      </div>
    </div>
    <label>اختر نوع التطبيق (select type app)</label>
    <div class="type-grid" id="type_grid"></div>
  </div>

  <div class="grid">
    <div>
      <div class="card" id="prompt-area">
        <h3>الكود (JSON / HTML / ZIP)</h3>
        <textarea id="prompt" placeholder="الصق الكود هنا أو ارفع ملف..."></textarea>
        <input type="file" id="code_file" style="margin-top:8px;">
      </div>
      <div class="card" id="files-area">
        <h3>رفع الملفات <span id="files_count" class="badge ok">0</span></h3>
        <div id="file_rows"></div>
        <button class="secondary" onclick="addFileRow()">+ إضافة ملف</button>
      </div>
      <button onclick="startBuilding()">Start Building</button>
      <div id="status"></div>
    </div>
    <div>
      <div class="card">
        <h3>Templates (100)</h3>
        <div class="tmpl-list" id="tmpl"></div>
      </div>
      <div class="card">
        <h3>Configuration</h3>
        <pre id="cfg">Loading...</pre>
      </div>
      <div class="card">
        <h3>Render Status</h3>
        <pre id="render">Loading...</pre>
      </div>
    </div>
  </div>
</main>

<script>
const APP_TYPES = """ + json.dumps(APP_TYPES, ensure_ascii=False) + """;
let selectedType = null;

function renderTypes() {
  const grid = document.getElementById('type_grid');
  grid.innerHTML = APP_TYPES.map(t => `
    <div class="type-card" id="type_${t.id}" onclick="selectType('${t.id}')">
      <span class="icon">${t.icon}</span>
      <div class="title">${t.label}</div>
      <div class="desc">${t.desc}</div>
    </div>`).join('');
}

function selectType(id) {
  selectedType = id;
  document.querySelectorAll('.type-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('type_' + id).classList.add('selected');
  const t = APP_TYPES.find(x => x.id === id);
  // Toggle which area is visible
  const promptArea = document.getElementById('prompt-area');
  const filesArea  = document.getElementById('files-area');
  if (t.multi) {
    promptArea.style.display = 'none';
    filesArea.style.display  = 'block';
    document.getElementById('files_count').textContent = '0';
    // Reset rows
    document.getElementById('file_rows').innerHTML = '';
    addFileRow();
  } else {
    promptArea.style.display = 'block';
    filesArea.style.display  = 'none';
    document.querySelector('#prompt-area h3').textContent =
      id === 'json' ? 'الكود JSON' :
      id === 'html' ? 'الكود HTML' :
      id === 'zip'  ? 'ارفع ملف ZIP' : 'الكود';
    const fileInput = document.getElementById('code_file');
    fileInput.accept = t.accept;
  }
}

function addFileRow() {
  const row = document.createElement('div');
  row.className = 'file-row';
  const t = APP_TYPES.find(x => x.id === selectedType) || {accept:'*/*'};
  row.innerHTML = `
    <input type="file" accept="${t.accept}" onchange="updateCount()">
    <input type="text" placeholder="اسم الملف" class="file-name">
    <button onclick="this.parentElement.remove(); updateCount();">✕</button>`;
  document.getElementById('file_rows').appendChild(row);
  updateCount();
}

function updateCount() {
  const rows = document.querySelectorAll('#file_rows .file-row');
  document.getElementById('files_count').textContent = rows.length;
}

async function loadConfig() {
  const r = await fetch('/api/config');
  document.getElementById('cfg').textContent = JSON.stringify(await r.json(), null, 2);
}

async function loadTemplates() {
  const r = await fetch('/templates');
  const t = await r.json();
  document.getElementById('tmpl').innerHTML = t.templates.map(x =>
    `<a href="#" onclick="buildTemplate('${x.id}');return false;">${x.id} ${x.name}</a>`
  ).join('');
}

async function loadRender() {
  const r = await fetch('/api/render/health');
  document.getElementById('render').textContent = JSON.stringify(await r.json(), null, 2);
}

async function startBuilding() {
  if (!selectedType) { alert('اختر نوع التطبيق أولاً'); return; }
  const status = document.getElementById('status');
  status.style.display = 'block';
  status.textContent = 'جاري البناء... قد يستغرق 30 ثانية';
  const appName = document.getElementById('app_name').value || 'WebApp';
  const t = APP_TYPES.find(x => x.id === selectedType);

  let body = { name: appName, app_type: selectedType };
  let endpoint = '/api/build-' + selectedType + '-apk';

  if (t.multi) {
    // collect files
    const rows = document.querySelectorAll('#file_rows .file-row');
    const files = [];
    const names = [];
    rows.forEach(r => {
      const f = r.querySelector('input[type=file]').files[0];
      const n = r.querySelector('.file-name').value || (f ? f.name : '');
      if (f) { files.push(f); names.push(n); }
    });
    if (files.length === 0) { alert('اختر ملفاً واحداً على الأقل'); return; }
    const fd = new FormData();
    fd.append('name', appName);
    files.forEach((f, i) => fd.append('files', f));
    names.forEach(n => fd.append('names', n));
    const r = await fetch(endpoint, { method: 'POST', body: fd });
    const res = await r.json();
    showResult(res, status);
  } else {
    const code = document.getElementById('prompt').value;
    const fileInput = document.getElementById('code_file');
    if (fileInput.files.length) {
      const fd = new FormData();
      fd.append('name', appName);
      fd.append('file', fileInput.files[0]);
      const r = await fetch(endpoint, { method: 'POST', body: fd });
      const res = await r.json();
      showResult(res, status);
    } else if (code.trim()) {
      body.code = code;
      const r = await fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
      });
      const res = await r.json();
      showResult(res, status);
    } else {
      alert('الصق كوداً أو ارفع ملفاً');
    }
  }
}

function showResult(res, status) {
  if (res.success) {
    status.innerHTML = '✅ تم البناء في ' + (res.elapsed_seconds || 0).toFixed(1) +
      's. <a href="' + res.download_url + '" download>تحميل APK</a>';
  } else {
    status.textContent = '❌ خطأ: ' + (res.error || 'unknown');
  }
}

async function buildTemplate(id) {
  const status = document.getElementById('status');
  status.style.display = 'block';
  status.textContent = 'جاري بناء القالب ' + id + '...';
  const r = await fetch('/build-template', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id})
  });
  const res = await r.json();
  showResult(res, status);
}

renderTypes();
loadConfig();
loadTemplates();
loadRender();
</script>
</body>
</html>"""


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BardomPro — Dashboard</title>
<style>
  body { font-family: system-ui, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; }
  header { background: #161b22; padding: 16px 24px; border-bottom: 1px solid #30363d; }
  header h1 { margin: 0; font-size: 20px; color: #58a6ff; }
  main { max-width: 1200px; margin: 24px auto; padding: 0 16px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
          padding: 16px; margin-bottom: 16px; }
  .card h2 { margin: 0 0 12px; color: #58a6ff; font-size: 16px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: right; padding: 8px; border-bottom: 1px solid #21262d; font-size: 13px; }
  th { color: #8b949e; font-weight: 600; }
  .badge { padding: 2px 8px; border-radius: 12px; font-size: 11px; }
  .badge.on  { background: #1f6f3c; color: white; }
  .badge.off { background: #21262d; color: #8b949e; }
  button { background: #238636; color: white; border: none; padding: 6px 12px;
           border-radius: 4px; cursor: pointer; font-size: 12px; }
  button.danger { background: #da3633; }
  pre { background: #0d1117; padding: 8px; border-radius: 4px; font-size: 11px;
        overflow-x: auto; max-height: 200px; }
</style>
</head>
<body>
<header><h1> BardomPro Control Center</h1></header>
<main>
  <div class="card">
    <h2>التطبيقات المُولّدة (<span id="n_apps">0</span>)</h2>
    <table>
      <thead><tr>
        <th>التطبيق</th><th>الحزمة</th><th>الإعلانات</th>
        <th>الإحصاءات (7 أيام)</th><th>إجراءات</th>
      </tr></thead>
      <tbody id="apps_tbody"></tbody>
    </table>
  </div>
  <div class="card">
    <h2>إجراءات سريعة</h2>
    <button class="danger" onclick="killAllAds()">إيقاف كل الإعلانات فوراً</button>
    <button onclick="loadDashboard()">تحديث</button>
  </div>
  <div class="card">
    <h2>آخر الإشعارات</h2>
    <pre id="notifs">Loading...</pre>
  </div>
</main>
<script>
async function loadDashboard() {
  const r = await fetch('/api/control/apps');
  const apps = await r.json();
  document.getElementById('n_apps').textContent = apps.length;
  const tbody = document.getElementById('apps_tbody');
  tbody.innerHTML = apps.map(a => `
    <tr>
      <td>${a.name || a.id}<br><small style="color:#8b949e">${a.id}</small></td>
      <td><code>${a.package || ''}</code></td>
      <td><span class="badge ${a.ads.enabled?'on':'off'}">${a.ads.enabled?'مفعّل':'معطّل'}</span></td>
      <td>${JSON.stringify(a._stats || {})}</td>
      <td>
        <button onclick="toggleAds('${a.id}', ${!a.ads.enabled})">
          ${a.ads.enabled?'إيقاف':'تفعيل'} الإعلانات
        </button>
      </td>
    </tr>`).join('');
  const nr = await fetch('/api/control/notifications?limit=10');
  document.getElementById('notifs').textContent = JSON.stringify(await nr.json(), null, 2);
}
async function toggleAds(appId, enable) {
  await fetch('/api/control/apps/' + appId + '/ads', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ enabled: enable })
  });
  loadDashboard();
}
async function killAllAds() {
  if (!confirm('إيقاف كل الإعلانات في كل التطبيقات؟')) return;
  const r = await fetch('/api/control/ads/disable-all', { method: 'POST' });
  const res = await r.json();
  alert('تم إيقاف الإعلانات في ' + res.affected + ' تطبيق');
  loadDashboard();
}
loadDashboard();
setInterval(loadDashboard, 10000);
</script>
</body>
</html>"""


# --------------------------------------------------------------------- #
# Helpers — write uploaded files to a build dir, return their paths.
# --------------------------------------------------------------------- #
def _save_upload(file_storage, dest_dir: Path, name: Optional[str] = None) -> Path:
    """Save a Flask FileStorage to dest_dir. Returns the saved path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = name or file_storage.filename or "uploaded"
    # Sanitize
    fname = Path(fname).name
    dest = dest_dir / fname
    file_storage.save(dest)
    return dest


def _files_to_base64_payload(paths: list[Path]) -> list[dict]:
    """Read files, return list of {name, mime, bytes, base64}."""
    out = []
    import mimetypes
    for p in paths:
        data = p.read_bytes()
        b64 = base64.b64encode(data).decode()
        out.append({
            "name":   p.name,
            "mime":   mimetypes.guess_type(p.name)[0] or "application/octet-stream",
            "bytes":  len(data),
            "base64": b64,
        })
    return out


def _build_apk_for_manifest(manifest, app_name: str) -> dict:
    """Common build pipeline — returns a JSON-serialisable result dict."""
    proj_dir = BUILD_DIR / f"{app_name}_{int(time.time())}"
    generate_project(manifest, proj_dir)
    result = build_apk(proj_dir)
    if result.success:
        apk_name = f"{app_name}.apk"
        final = BUILD_DIR / apk_name
        shutil.copy2(result.signed_apk, final)
        return {
            "success": True,
            "elapsed_seconds": result.elapsed_seconds,
            "download_url": f"/download/{apk_name}",
        }
    return {"success": False, "error": result.error, "log": getattr(result, "log", "")}


# --------------------------------------------------------------------- #
if HAVE_FLASK:
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template_string(HTML_PAGE)

    @app.route("/dashboard")
    def dashboard():
        return render_template_string(DASHBOARD_HTML)

    # ---- Render health (graceful) ------------------------------------
    @app.route("/api/render/health")
    def render_health():
        try:
            from integrations.render_client import RenderClient
            rc = RenderClient(allow_disabled=True)
            return jsonify(rc.health())
        except Exception as e:
            return jsonify({"ok": False, "enabled": False, "error": str(e)})

    # ---- Legacy prompt build -----------------------------------------
    @app.route("/build", methods=["POST"])
    @app.route("/api/build-prompt", methods=["POST"])
    def build_prompt():
        data = request.get_json(force=True)
        prompt = data.get("prompt", "")
        name = data.get("name", "WebApp")
        try:
            manifest = parse_prompt_text(prompt)
            manifest.app_name = name
            return jsonify(_build_apk_for_manifest(manifest, name))
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # ---- Template build ----------------------------------------------
    @app.route("/build-template", methods=["POST"])
    def build_template():
        data = request.get_json(force=True)
        tid = data.get("id", "")
        tmpl_path = cfg.project_root / "templates" / f"{tid}.json"
        if not tmpl_path.exists():
            matches = list((cfg.project_root / "templates").glob(f"{tid}*.json"))
            if matches: tmpl_path = matches[0]
            else: return jsonify({"success": False, "error": f"Template {tid} not found"})
        try:
            manifest = load_template(tmpl_path)
            return jsonify(_build_apk_for_manifest(manifest, manifest.app_name))
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # ---- Multi-file builders (music / photos / video / image) -------
    def _multi_file_build(app_type: str):
        name = request.form.get("name", "MultiApp")
        files = request.files.getlist("files")
        names = request.form.getlist("names")
        if not files:
            return jsonify({"success": False, "error": "No files uploaded"})
        upload_dir = BUILD_DIR / f"uploads_{name}_{int(time.time())}"
        paths = []
        for i, f in enumerate(files):
            n = names[i] if i < len(names) and names[i] else f.filename
            paths.append(_save_upload(f, upload_dir, n))
        try:
            # Build a manifest via the appropriate type
            from engine.project_generator import Manifest
            manifest = Manifest(
                app_name=name,
                package=f"com.bardom.{app_type}.{int(time.time())}",
                app_type=app_type,
                assets=[{"path": str(p), "name": p.name, "type": app_type}
                        for p in paths],
            )
            return jsonify(_build_apk_for_manifest(manifest, name))
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/api/build-music-apk",  methods=["POST"])
    def build_music_apk():  return _multi_file_build("music")

    @app.route("/api/build-photos-apk", methods=["POST"])
    def build_photos_apk(): return _multi_file_build("photos")

    @app.route("/api/build-video-apk",  methods=["POST"])
    def build_video_apk():  return _multi_file_build("video")

    @app.route("/api/build-image-apk",  methods=["POST"])
    def build_image_apk():  return _multi_file_build("image")

    # ---- Single-file builders (json / html / zip) -------------------
    def _single_file_or_code_build(app_type: str):
        name = request.form.get("name") or request.json.get("name", "CodeApp")
        # File upload via FormData
        if "file" in request.files:
            f = request.files["file"]
            upload_dir = BUILD_DIR / f"uploads_{name}_{int(time.time())}"
            p = _save_upload(f, upload_dir)
            code = p.read_text(encoding="utf-8", errors="replace")
        else:
            code = (request.json or {}).get("code", "")
        if not code.strip():
            return jsonify({"success": False, "error": "Empty code / file"})
        try:
            from engine.project_generator import Manifest
            manifest = Manifest(
                app_name=name,
                package=f"com.bardom.{app_type}.{int(time.time())}",
                app_type=app_type,
                source_code=code,
            )
            return jsonify(_build_apk_for_manifest(manifest, name))
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/api/build-json-apk", methods=["POST"])
    def build_json_apk(): return _single_file_or_code_build("json")

    @app.route("/api/build-html-apk",  methods=["POST"])
    def build_html_apk(): return _single_file_or_code_build("html")

    @app.route("/api/build-zip-apk",   methods=["POST"])
    def build_zip_apk():
        if "file" not in request.files:
            return jsonify({"success": False, "error": "ZIP file required"})
        name = request.form.get("name", "ZipApp")
        f = request.files["file"]
        upload_dir = BUILD_DIR / f"uploads_{name}_{int(time.time())}"
        zip_path = _save_upload(f, upload_dir)
        # Extract
        extract_dir = upload_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            return jsonify({"success": False, "error": f"Bad ZIP: {e}"})
        try:
            from engine.project_generator import Manifest
            manifest = Manifest(
                app_name=name,
                package=f"com.bardom.zip.{int(time.time())}",
                app_type="zip",
                assets_dir=str(extract_dir),
            )
            return jsonify(_build_apk_for_manifest(manifest, name))
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # ---- Control Center (ads / stats / monitoring) ------------------
    @app.route("/api/control/apps")
    def control_apps():
        from dashboard import get_control_center
        cc = get_control_center()
        out = []
        for a in cc.list_apps():
            entry = dict(a)
            entry["_stats"] = cc.get_stats(a["id"], days=7)
            out.append(entry)
        return jsonify(out)

    @app.route("/api/control/apps/<app_id>/ads", methods=["POST"])
    def control_set_ads(app_id):
        from dashboard import get_control_center
        cc = get_control_center()
        data = request.get_json(force=True)
        return jsonify(cc.set_ads(app_id, **data))

    @app.route("/api/control/ads/disable-all", methods=["POST"])
    def control_kill_ads():
        from dashboard import get_control_center
        cc = get_control_center()
        n = cc.disable_all_ads()
        return jsonify({"affected": n})

    @app.route("/api/control/stats")
    def control_stats():
        from dashboard import get_control_center
        cc = get_control_center()
        days = int(request.args.get("days", "7"))
        return jsonify(cc.get_all_stats(days))

    @app.route("/api/control/notifications")
    def control_notifs():
        from dashboard import get_control_center
        cc = get_control_center()
        app_id = request.args.get("app_id")
        limit = int(request.args.get("limit", "50"))
        return jsonify(cc.list_notifications(app_id, limit))

    @app.route("/api/control/broadcast", methods=["POST"])
    def control_broadcast():
        from dashboard import get_control_center
        cc = get_control_center()
        d = request.get_json(force=True)
        return jsonify(cc.broadcast(d.get("title", ""), d.get("body", ""), d.get("data")))

    # ---- Download ----------------------------------------------------
    @app.route("/download/<path:filename>")
    def download(filename):
        return send_file(BUILD_DIR / filename, as_attachment=True)

    # ---- Templates ---------------------------------------------------
    @app.route("/templates")
    def list_templates():
        tdir = cfg.project_root / "templates"
        out = []
        for p in sorted(tdir.glob("template_*.json")):
            try:
                d = json.loads(p.read_text())
                out.append({"id": p.stem, "name": d.get("name", p.stem),
                            "features": len(d.get("features", []))})
            except Exception:
                pass
        return jsonify({"templates": out})

    # ---- Config (no secrets) ----------------------------------------
    @app.route("/api/config")
    def api_config():
        return jsonify({
            "telegram_bot":    f"@{cfg.telegram.bot_username}" if cfg.telegram else None,
            "github_repo":     cfg.github.repo if cfg.github else None,
            "ai_model":        cfg.ai.model if cfg.ai else None,
            "firebase_project": cfg.firebase.project_id if cfg.firebase else None,
            "render_service":  cfg.render.service_id if cfg.render else None,
            "render_enabled":  bool(cfg.render and cfg.render.api_key),
            "auto_push_github": cfg.auto_push_github,
            "require_100_test_pass": cfg.require_100_test_pass,
            "engine_dir":      cfg.engine_dir,
            "build_tools":     str(cfg.build.build_tools) if cfg.build else None,
            "app_types":       APP_TYPES,
        })

    @app.route("/api/builds")
    def api_builds():
        try:
            from integrations.firebase_client import FirebaseClient
            return jsonify(FirebaseClient().get("builds"))
        except Exception as e:
            return jsonify({"error": str(e)})

    def main():
        print(f"Universal App Generator web UI on http://localhost:{APP_PORT}")
        app.run(host="0.0.0.0", port=APP_PORT, debug=False)


else:
    # Fallback: http.server
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self._html(HTML_PAGE)
            elif self.path == "/dashboard":
                self._html(DASHBOARD_HTML)
            elif self.path == "/api/config":
                self._json({
                    "telegram_bot": f"@{cfg.telegram.bot_username}" if cfg.telegram else None,
                    "github_repo": cfg.github.repo if cfg.github else None,
                    "ai_model": cfg.ai.model if cfg.ai else None,
                    "app_types": APP_TYPES,
                })
            elif self.path == "/templates":
                tdir = cfg.project_root / "templates"
                out = []
                for p in sorted(tdir.glob("template_*.json")):
                    try:
                        d = json.loads(p.read_text())
                        out.append({"id": p.stem, "name": d.get("name", p.stem),
                                    "features": len(d.get("features", []))})
                    except Exception:
                        pass
                self._json({"templates": out})
            else:
                self._html("Not found", 404)

        def _html(self, body, code=200):
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def _json(self, obj, code=200):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(obj).encode())

    def main():
        print(f"Universal App Generator web UI (fallback) on http://localhost:{APP_PORT}")
        HTTPServer(("0.0.0.0", APP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
