/**
 * الوحدة: روبوت تيليجرام
 */
(function() {
  BardomApp.registerModule('telegram-bot', 'تيليجرام', '✈️', function render() {
    const token = BardomApp.config.getApiKey('telegram');
    const hasToken = !!token;
    return `<div style="max-width:600px">
      <div class="section-title">✈️ روبوت تيليجرام</div>
      <div class="card">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
          <div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#0088cc,#229ED9);display:flex;align-items:center;justify-content:center;font-size:24px">✈️</div>
          <div><div style="font-weight:600">@allArabservicesbot</div><div class="text-xs text-muted">ارسل وصف التطبيق وسيتم بناء APK والرد به</div></div>
        </div>
        <div class="form-group"><label class="form-label">Bot Token</label><input class="form-input" id="tgToken" value="${token || ''}" placeholder="123456:ABC-DEF..." dir="ltr"></div>
        <div class="form-group"><label class="form-label">Admin Chat ID</label><input class="form-input" id="tgAdmin" value="${BardomApp.config.get('api.telegram_admin_id', '')}" placeholder="123456789" dir="ltr"></div>
        <button class="btn btn-primary" onclick="_saveTgConfig()">💾 حفظ الإعدادات</button>
        <span style="margin-right:12px" class="badge ${hasToken ? 'badge-green' : ''}">${hasToken ? '✅ متصل' : '⏳ غير متصل'}</span>
      </div>
      <div class="card">
        <div class="card-title">🎮 كيفية الاستخدام</div>
        <ol style="padding-right:20px;color:var(--text2);font-size:13px">
          <li style="margin-bottom:6px">أدخل Bot Token و Admin ID</li>
          <li style="margin-bottom:6px">أرسل وصف التطبيق للبوت في تيليجرام</li>
          <li style="margin-bottom:6px">سيتم بناء APK والرد بالملف</li>
          <li>يمكنك أيضاً إرسال ملف .txt بالمميزات</li>
        </ol>
      </div>
    </div>`;
  });

  window._saveTgConfig = function() {
    const token = document.getElementById('tgToken')?.value?.trim();
    const admin = document.getElementById('tgAdmin')?.value?.trim();
    BardomApp.config.setApiKey('telegram', token);
    BardomApp.config.set('api.telegram_admin_id', admin);
    BardomApp.showToast('✅ تم حفظ إعدادات تيليجرام', 'success');
  };
})();
