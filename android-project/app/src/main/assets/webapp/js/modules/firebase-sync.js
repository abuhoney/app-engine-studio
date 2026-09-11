/**
 * الوحدة: Firebase
 */
(function() {
  BardomApp.registerModule('firebase-sync', 'Firebase', '🔥', function render() {
    const url = BardomApp.config.get('api.firebase_url', '');
    return `<div style="max-width:600px">
      <div class="section-title">🔥 Firebase</div>
      <div class="card">
        <div class="form-group"><label class="form-label">Firebase RTDB URL</label><input class="form-input" id="fbUrl" value="${url}" placeholder="https://your-app.firebaseio.com" dir="ltr"></div>
        <button class="btn btn-primary" onclick="_saveFbConfig()">💾 حفظ</button>
        <button class="btn btn-ghost" onclick="_testFb()">📡 اختبار</button>
      </div>
      <div class="card mt-16">
        <div class="card-title">📊 سجل البنيات</div>
        <div id="fbBuildLog" class="text-sm text-muted">جاري التحميل...</div>
      </div>
    </div>`;
  });

  window._saveFbConfig = function() {
    BardomApp.config.set('api.firebase_url', document.getElementById('fbUrl')?.value?.trim());
    BardomApp.showToast('✅ تم حفظ إعدادات Firebase', 'success');
  };

  window._testFb = async function() {
    const url = document.getElementById('fbUrl')?.value?.trim();
    if (!url) { BardomApp.showToast('أدخل URL أولاً', 'warning'); return; }
    try {
      const resp = await fetch(url + '/.json');
      BardomApp.showToast(resp.ok ? '✅ متصل بـ Firebase' : '❌ فشل الاتصال', resp.ok ? 'success' : 'error');
    } catch(e) { BardomApp.showToast('❌ فشل الاتصال: ' + e.message, 'error'); }
  };
})();
