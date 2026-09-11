/**
 * الوحدة: GitHub
 */
(function() {
  BardomApp.registerModule('github-push', 'GitHub', '❤️', function render() {
    const token = BardomApp.config.getApiKey('github');
    const repo = BardomApp.config.get('api.github_repo', 'abuhoney/bardom');
    return `<div style="max-width:600px">
      <div class="section-title">❤️ GitHub</div>
      <div class="card">
        <div class="form-group"><label class="form-label">Personal Access Token</label><input class="form-input" id="ghToken" type="password" value="${token || ''}" placeholder="ghp_xxxx..." dir="ltr"></div>
        <div class="form-group"><label class="form-label">المستودع</label><input class="form-input" id="ghRepo" value="${repo}" dir="ltr"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="_saveGhConfig()">f4be حفظ</button>
          <button class="btn btn-ghost" onclick="_testGhConn()">f50c اختبار الاتصال</button>
        </div>
      </div>
      <div class="card mt-16">
        <div class="card-title">f4e6 إدارة الإصدارات</div>
        <p class="text-sm text-muted" style="margin-bottom:12px">رفع APK كمبدأ GitHub Release</p>
        <button class="btn btn-success" onclick="_createRelease()">f680 إنشاء Release</button>
      </div>
    </div>`;
  });

  window._saveGhConfig = function() {
    BardomApp.config.setApiKey('github', document.getElementById('ghToken')?.value?.trim());
    BardomApp.config.set('api.github_repo', document.getElementById('ghRepo')?.value?.trim());
    BardomApp.showToast('✅ تم حفظ إعدادات GitHub', 'success');
  };

  window._testGhConn = async function() {
    const token = document.getElementById('ghToken')?.value?.trim();
    if (!token) { BardomApp.showToast('أدخل Token أولاً', 'warning'); return; }
    BardomApp.showLoading('جاري اختبار الاتصال...');
    try {
      const resp = await fetch('https://api.github.com/user', { headers: { 'Authorization': 'Bearer ' + token } });
      if (resp.ok) { const u = await resp.json(); BardomApp.showToast('✅ متصل: ' + u.login, 'success'); }
      else { BardomApp.showToast('❌ Token غير صالح', 'error'); }
    } catch(e) { BardomApp.showToast('❌ فشل الاتصال', 'error'); }
    BardomApp.hideLoading();
  };

  window._createRelease = function() {
    BardomApp.showToast('f399️ هذه الوظيفة تعمل من خلال APK على الجهاز', 'warning');
  };
})();