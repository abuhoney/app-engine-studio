/**
 * الوحدة: الإعدادات
 */
BardomApp.registerModule('settings', 'الإعدادات', '\u2699\ufe0f', function render() {
  const cfg = BardomApp.config.config || {};
  return `<div style="max-width:600px">
    <div class="section-title">\u2699\ufe0f الإعدادات</div>
    <div class="card">
      <div class="card-title">\u{1f310} مفاتيح API</div>
      <div class="form-group"><label class="form-label">OpenRouter API Key</label><input class="form-input" id="setOpenrouter" value="${BardomApp.config.getApiKey('openrouter') || ''}" placeholder="sk-or-..." dir="ltr"></div>
      <div class="form-group"><label class="form-label">Telegram Bot Token</label><input class="form-input" id="setTelegram" value="${BardomApp.config.getApiKey('telegram') || ''}" dir="ltr"></div>
      <div class="form-group"><label class="form-label">GitHub Token</label><input class="form-input" id="setGithub" value="${BardomApp.config.getApiKey('github') || ''}" type="password" dir="ltr"></div>
      <div class="form-group"><label class="form-label">Firebase URL</label><input class="form-input" id="setFirebase" value="${BardomApp.config.get('api.firebase_url', '') || ''}" dir="ltr"></div>
      <button class="btn btn-primary" onclick="_saveAllSettings()">\u{1f4be} حفظ الكل</button>
    </div>
    <div class="card mt-16">
      <div class="card-title">\u{1f528} إعدادات البناء الافتراضية</div>
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <div class="form-group" style="flex:1;min-width:120px"><label class="form-label">بادئة الحزمة</label><input class="form-input" id="setPkgPrefix" value="${BardomApp.config.get('build.default_package_prefix', 'app.bardom.')}" dir="ltr"></div>
        <div class="form-group" style="flex:1;min-width:80px"><label class="form-label">Min SDK</label><input class="form-input" id="setMinSdk" type="number" value="${BardomApp.config.get('build.default_min_sdk', 21)}" dir="ltr"></div>
        <div class="form-group" style="flex:1;min-width:80px"><label class="form-label">Target SDK</label><input class="form-input" id="setTargetSdk" type="number" value="${BardomApp.config.get('build.default_target_sdk', 34)}" dir="ltr"></div>
      </div>
      <button class="btn btn-primary" onclick="_saveBuildSettings()">\u{1f4be} حفظ</button>
    </div>
    <div class="card mt-16">
      <div class="card-title">\u{1f504} إدارة الوحدات</div>
      <div id="moduleList">${BardomApp.modules.getAll().map(m => '<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--border)"><span>' + m.icon + '</span><span class="text-sm">' + m.name + '</span><span class="text-xs text-muted">' + m.id + '</span></div>').join('')}</div>
      <p class="text-xs text-muted mt-8">\u{1f4dd} لإضافة وحدة جديدة: أنشئ ملف JS في js/modules/ وأضفه في config/app.json</p>
    </div>
    <div class="card mt-16">
      <div class="card-title">\u{1f5d1}\ufe0f مسح البيانات</div>
      <button class="btn btn-danger" onclick="if(confirm('هل أنت متأكد؟')){localStorage.clear();location.reload()}">\u{1f5d1}\ufe0f مسح جميع البيانات المحفوظة</button>
    </div>
    <div class="card mt-16">
      <div class="card-title">\u2139\ufe0f حول التطبيق</div>
      <div class="text-sm text-muted">
        <p><strong>Bardom AI</strong> v${cfg.version || '1.0.0'}</p>
        <p>المحرك: v${cfg.engine_version || '3.0.0'}</p>
        <p>الحزمة: ${cfg.package || 'com.bardom.ai'}</p>
        <p style="margin-top:8px">\u{1f4f1} يعمل بالكامل من الملفات - بدون إعادة بناء APK</p>
      </div>
    </div>
  </div>`;
});

window._saveAllSettings = function() {
  BardomApp.config.setApiKey('openrouter', document.getElementById('setOpenrouter')?.value?.trim());
  BardomApp.config.setApiKey('telegram', document.getElementById('setTelegram')?.value?.trim());
  BardomApp.config.setApiKey('github', document.getElementById('setGithub')?.value?.trim());
  BardomApp.config.set('api.firebase_url', document.getElementById('setFirebase')?.value?.trim());
  BardomApp.showToast('\u2705 تم حفظ جميع الإعدادات', 'success');
};

window._saveBuildSettings = function() {
  BardomApp.config.set('build.default_package_prefix', document.getElementById('setPkgPrefix')?.value?.trim());
  BardomApp.config.set('build.default_min_sdk', parseInt(document.getElementById('setMinSdk')?.value || '21'));
  BardomApp.config.set('build.default_target_sdk', parseInt(document.getElementById('setTargetSdk')?.value || '34'));
  BardomApp.showToast('\u2705 تم حفظ إعدادات البناء', 'success');
};
