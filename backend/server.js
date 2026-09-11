const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;
const SECRET = process.env.BACKEND_SECRET || 'dev-secret';

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Health check (Render uses this)
app.get('/health', (req, res) => res.json({ status: 'ok', service: 'app-engine-studio', version: '7.2.0' }));

// Root
app.get('/', (req, res) => res.json({
  name: 'App Engine Studio Backend',
  version: '7.2.0',
  endpoints: ['/health', '/api/config', '/api/build-apk', '/api/ads', '/api/identity', '/api/stats', '/api/admin/commands']
}));

// Get app config (sent to the APK)
app.get('/api/config', (req, res) => {
  const auth = req.headers.authorization;
  if (auth !== `Bearer ${SECRET}` && process.env.NODE_ENV === 'production') {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  res.json({
    backendUrl: process.env.BACKEND_URL || 'https://all-arab-services.onrender.com',
    firebase: {
      apiKey: process.env.FIREBASE_API_KEY,
      projectId: process.env.FIREBASE_PROJECT_ID,
      databaseUrl: process.env.FIREBASE_DATABASE_URL,
      appId: process.env.FIREBASE_APP_ID,
    },
    features: {
      enableStudio: true,
      enableAds: true,
      enableIdentity: true,
      enableTemplates: true,
      enableJsonTools: true,
      enableHtmlIo: true,
    },
    updatedAt: new Date().toISOString()
  });
});

// Build APK request (queues a build job)
app.post('/api/build-apk', (req, res) => {
  const { config, template, packageName } = req.body;
  if (!config) return res.status(400).json({ error: 'Missing config' });
  const jobId = `job_${Date.now()}`;
  console.log(`[Build] Queued ${jobId} for package ${packageName || 'default'}`);
  res.json({ jobId, status: 'queued', message: 'APK build queued. Check status with GET /api/build-status/:jobId' });
});

// Get build status
app.get('/api/build-status/:jobId', (req, res) => {
  res.json({ jobId: req.params.jobId, status: 'completed', downloadUrl: '/download/app-debug.apk' });
});

// Download APK
app.get('/download/app-debug.apk', (req, res) => {
  const apkPath = path.join(__dirname, '..', 'apk', 'app-debug.apk');
  if (fs.existsSync(apkPath)) {
    res.sendFile(apkPath);
  } else {
    res.status(404).json({ error: 'APK not built yet' });
  }
});

// Ads config
app.get('/api/ads', (req, res) => {
  res.json({
    enabled: true,
    defaultPlatform: 'custom_json',
    types: {
      banner: { enabled: true, platform: 'custom_json' },
      interstitial: { enabled: true, platform: 'custom_json', frequency: 'every_5' },
      rewarded: { enabled: true, platform: 'custom_json', reward: { type: 'points', amount: 10 } }
    }
  });
});

// Identity config
app.get('/api/identity', (req, res) => {
  res.json({
    appName: 'App Engine Studio',
    appLink: 'https://github.com/abuhoney/app-engine-studio',
    firebaseProjectId: process.env.FIREBASE_PROJECT_ID,
    firebaseApiKey: process.env.FIREBASE_API_KEY,
    firebaseDatabaseUrl: process.env.FIREBASE_DATABASE_URL,
  });
});

// Stats
app.post('/api/stats', (req, res) => {
  console.log('[Stats]', req.body);
  res.json({ status: 'ok' });
});

app.get('/api/stats', (req, res) => {
  res.json({ installs: 0, activeUsers: 0, appsGenerated: 0 });
});

// Admin commands
app.post('/api/admin/commands', (req, res) => {
  const { deviceId, command } = req.body;
  console.log(`[Admin] Command for ${deviceId}:`, command);
  res.json({ status: 'queued' });
});

app.get('/api/admin/commands/:deviceId', (req, res) => {
  res.json({ commands: [] });
});

// Serve the HTML generator
app.get('/studio.html', (req, res) => {
  const htmlPath = path.join(__dirname, 'public', 'studio.html');
  if (fs.existsSync(htmlPath)) {
    res.sendFile(htmlPath);
  } else {
    res.status(404).send('Studio HTML not found');
  }
});

app.listen(PORT, () => {
  console.log(`App Engine Studio backend running on port ${PORT}`);
  console.log(`Health: http://localhost:${PORT}/health`);
});
