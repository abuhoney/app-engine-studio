const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { execSync, exec } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '100mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Health
app.get('/health', (req, res) => res.json({ status: 'ok', version: '10.0.0', unified: true }));

// Root
app.get('/', (req, res) => res.json({
  name: 'App Engine Studio — Unified',
  version: '10.0.0',
  features: ['studio-html', 'real-apk-builder', 'firebase', 'github-push'],
  endpoints: ['/health', '/api/build', '/api/status/:jobId', '/download/:file', '/index.html']
}));

// Build APK — REAL compilation using builder.py
app.post('/api/build', (req, res) => {
  const { appName, packageName, htmlContent, versionName, versionCode } = req.body;

  if (!appName || !packageName) {
    return res.status(400).json({ error: 'Missing appName or packageName' });
  }

  const jobId = `job_${Date.now()}`;
  const workDir = `/tmp/${jobId}`;
  const htmlPath = path.join(workDir, 'webapp.html');

  try {
    // Create work directory
    fs.mkdirSync(workDir, { recursive: true });

    // Write HTML content (or use studio.html if no custom HTML)
    const html = htmlContent || '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>' + appName + '</title></head><body><h1>' + appName + '</h1></body></html>';
    fs.writeFileSync(htmlPath, html);

    // Build the APK using builder.py
    const builderPath = path.join(__dirname, '..', 'builder');
    const cmd = `cd ${builderPath} && python3 builder.py --project-name "${appName}" --html "${htmlPath}" --package "${packageName}" --version-name "${versionName || '1.0.0'}" --version-code "${versionCode || '1'}" --target debug 2>&1`;

    console.log(`[Build] Starting ${jobId} for ${appName} (${packageName})`);

    // Run build asynchronously
    exec(cmd, { timeout: 300000, maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
      const logFile = path.join(workDir, 'build.log');
      fs.writeFileSync(logFile, stdout + '\n' + (stderr || ''));

      if (err) {
        console.error(`[Build] ${jobId} failed:`, err.message);
        // Try to find the APK anyway
      }

      // Find the generated APK
      const apkPattern = /\.apk$/;
      let apkPath = null;

      // Check builder workspace
      const workspaceDir = path.join(builderPath, 'workspace');
      if (fs.existsSync(workspaceDir)) {
        const findCmd = `find ${workspaceDir} -name "*.apk" -type f 2>/dev/null | head -1`;
        try {
          apkPath = execSync(findCmd).toString().trim();
        } catch(e) {}
      }

      // Check /tmp
      if (!apkPath || !fs.existsSync(apkPath)) {
        try {
          apkPath = execSync(`find /tmp -name "${appName.replace(/[^a-zA-Z0-9]/g, '_')}*.apk" -type f 2>/dev/null | head -1`).toString().trim();
        } catch(e) {}
      }

      if (apkPath && fs.existsSync(apkPath)) {
        // Copy APK to a downloadable location
        const downloadName = `${appName.replace(/[^a-zA-Z0-9]/g, '_')}.apk`;
        const downloadPath = path.join('/tmp', downloadName);
        fs.copyFileSync(apkPath, downloadPath);

        const size = fs.statSync(downloadPath).size;
        console.log(`[Build] ${jobId} succeeded: ${downloadPath} (${size} bytes)`);
      } else {
        console.error(`[Build] ${jobId} completed but no APK found`);
      }
    });

    res.json({
      jobId,
      status: 'building',
      message: 'APK build started. Check status with GET /api/status/' + jobId,
      checkStatus: '/api/status/' + jobId
    });

  } catch (e) {
    console.error('[Build] Error:', e);
    res.status(500).json({ error: e.message, jobId });
  }
});

// Check build status
app.get('/api/status/:jobId', (req, res) => {
  const jobId = req.params.jobId;
  const logPath = path.join('/tmp', jobId, 'build.log');

  if (fs.existsSync(logPath)) {
    const log = fs.readFileSync(logPath, 'utf-8');
    const success = log.includes('APK ready') || log.includes('BUILD SUCCESSFUL');
    const failed = log.includes('failed') || log.includes('FAILURE');
    const apkMatch = log.match(/([\w\/\.-]+\.apk)/);

    res.json({
      jobId,
      status: success ? 'completed' : (failed ? 'failed' : 'building'),
      log: log.substring(0, 2000),
      apkUrl: success && apkMatch ? `/download/${path.basename(apkMatch[1])}` : null
    });
  } else {
    res.json({ jobId, status: 'pending' });
  }
});

// Download APK
app.get('/download/:filename', (req, res) => {
  const filePath = path.join('/tmp', req.params.filename);
  if (fs.existsSync(filePath)) {
    res.setHeader('Content-Type', 'application/vnd.android.package-archive');
    res.setHeader('Content-Disposition', `attachment; filename="${req.params.filename}"`);
    res.sendFile(filePath);
  } else {
    res.status(404).json({ error: 'File not found' });
  }
});

app.listen(PORT, () => {
  console.log(`App Engine Studio v10.0.0 (Unified) on port ${PORT}`);
  console.log(`Builder: ${path.join(__dirname, '..', 'builder')}`);
});
