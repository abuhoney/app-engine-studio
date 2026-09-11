/**
 * الوحدة: مولد المشاريع (يعرض تفاصيل المشروع المُولَّد)
 */
(function() {
  BardomApp.registerModule('project-generator', 'مولد المشاريع', '⚙️', function render() {
    return `<div style="max-width:700px">
      <div class="section-title">⚙️ مولد المشاريع</div>
      <div class="card">
        <div class="card-title">📁 المشاريع المُولَّدة</div>
        <div id="projectsList" class="text-sm text-muted">جاري التحميل...</div>
      </div>
      <div class="card mt-16">
        <div class="card-title">📝 إنشاء مشروع مخصص</div>
        <div class="form-group"><label class="form-label">نوع المشروع</label>
          <select class="form-select" id="projType"><option value="android">Android APK</option><option value="html">تطبيق WebView</option><option value="pwa">تطبيق ويب (PWA)</option></select>
        </div>
        <div class="form-group"><label class="form-label">وصف مختصر</label><textarea class="form-textarea" id="projDesc" rows="3" placeholder="صف مشروعك..."></textarea></div>
        <button class="btn btn-primary" onclick="_genProject()">⚙️ إنشاء</button>
      </div>
    </div>`;
  });

  window._genProject = function() {
    BardomApp.showToast('✅ سيتم إنشاء المشروع في المجلد المحدد', 'success');
  };
})();
