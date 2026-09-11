const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Health check
app.get('/health', (req, res) => res.json({ status: 'ok', service: 'app-engine-studio', version: '7.2.0' }));

// Root
app.get('/', (req, res) => res.json({
  name: 'App Engine Studio Backend',
  version: '7.2.0',
  status: 'live',
  endpoints: ['/health', '/api/config', '/api/ads', '/api/identity', '/api/stats', '/api/admin/commands', '/studio.html'],
  firebase: process.env.FIREBASE_PROJECT_ID || 'not-configured',
  github: process.env.GITHUB_REPO || 'not-configured'
}));

// Get app config (no auth required — security is in Firebase rules)
app.get('/api/config', (req, res) => {
  res.json({
    backendUrl: 'https://all-arab-services.onrender.com',
    firebase: {
      apiKey: process.env.FIREBASE_API_KEY || 'AIzaSyBm-ZwOv8oPd_0rms_2oesGz3fDmt5ogvA',
      projectId: process.env.FIREBASE_PROJECT_ID || 'all-arab-services-750ad',
      databaseUrl: process.env.FIREBASE_DATABASE_URL || 'https://all-arab-services-750ad-default-rtdb.europe-west1.firebasedatabase.app',
      appId: process.env.FIREBASE_APP_ID || '1:1002499268790:web:9437bee4f4df9f93adc617',
    },
    features: {
      enableStudio: true,
      enableAds: true,
      enableIdentity: true,
      enableTemplates: true,
      enableJsonTools: true,
      enableHtmlIo: true,
    },
    studioHtmlUrl: 'https://all-arab-services.onrender.com/studio.html',
    apkUrls: {
      studio: 'https://github.com/abuhoney/app-engine-studio/raw/main/apk/app-engine-studio.apk',
      demo: 'https://github.com/abuhoney/app-engine-studio/raw/main/apk/demo-app-debug.apk'
    },
    updatedAt: new Date().toISOString()
  });
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
    firebaseProjectId: process.env.FIREBASE_PROJECT_ID || 'all-arab-services-750ad',
    firebaseApiKey: process.env.FIREBASE_API_KEY || 'AIzaSyBm-ZwOv8oPd_0rms_2oesGz3fDmt5ogvA',
    firebaseDatabaseUrl: process.env.FIREBASE_DATABASE_URL || 'https://all-arab-services-750ad-default-rtdb.europe-west1.firebasedatabase.app',
  });
});

// Stats
app.post('/api/stats', (req, res) => {
  console.log('[Stats]', JSON.stringify(req.body).substring(0, 200));
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

// Build APK
app.post('/api/build-apk', (req, res) => {
  const jobId = `job_${Date.now()}`;
  console.log(`[Build] Queued ${jobId}`);
  res.json({ jobId, status: 'queued', message: 'Build queued' });
});

app.get('/api/build-status/:jobId', (req, res) => {
  res.json({ jobId: req.params.jobId, status: 'completed', downloadUrl: 'https://github.com/abuhoney/app-engine-studio/raw/main/apk/app-engine-studio.apk' });
});

// Serve studio.html
app.get('/studio.html', (req, res) => {
  const htmlPath = path.join(__dirname, 'public', 'studio.html');
  if (fs.existsSync(htmlPath)) res.sendFile(htmlPath);
  else res.status(404).send('Studio HTML not found');
});

app.listen(PORT, () => {
  console.log(`App Engine Studio backend running on port ${PORT}`);
});
