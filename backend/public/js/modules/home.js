/**
 * الوحدة: الصفحة الرئيسية
 */
BardomApp.registerModule('home', 'الرئيسية', '\u{1f3e0}', function render() {
  const mc = BardomApp.modules.count;
  const buildCount = localStorage.getItem('bardom_build_count') || '0';
  return `<div style="max-width:800px">
    <div style="margin-bottom:32px">
      <h1 style="font-size:28px;font-weight:800;margin-bottom:8px">
        <span style="background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">Bardom AI</span>
      </h1>
      <p class="text-muted" style="font-size:15px">مولد التطبيقات الشامل - أنشئ تطبيقات Android حقيقية من وصف نصي</p>
    </div>
    <div class="grid-2">
      <div class="card" onclick="BardomApp.navigateTo('templates-browser')" style="cursor:pointer">
        <div style="font-size:32px;margin-bottom:8px">\u{1f4cb}</div>
        <div class="card-title">100 قالب جاهز</div>
        <div class="card-desc">آلة حاسبة، ألعاب، أدوات إنتاجية، وسائط، صحة، سفر، مالية وأكثر</div>
      </div>
      <div class="card" onclick="BardomApp.navigateTo('apk-builder')" style="cursor:pointer">
        <div style="font-size:32px;margin-bottom:8px">\u{1f528}</div>
        <div class="card-title">بناء APK فوري</div>
        <div class="card-desc">اكتب وصف التطبيق واحصل على APK جاهز للتثبيت</div>
      </div>
      <div class="card" onclick="BardomApp.navigateTo('ai-assistant')" style="cursor:pointer">
        <div style="font-size:32px;margin-bottom:8px">\u{1f916}</div>
        <div class="card-title">مساعد الذكاء الاصطناعي</div>
        <div class="card-desc">Kimi K2 يساعدك في كتابة كود وتصميم واجهات</div>
      </div>
      <div class="card" onclick="BardomApp.navigateTo('settings')" style="cursor:pointer">
        <div style="font-size:32px;margin-bottom:8px">\u2699\ufe0f</div>
        <div class="card-title">الإعدادات والتكاملات</div>
        <div class="card-desc">ربط Telegram, GitHub, Firebase وتخصيص البناء</div>
      </div>
    </div>
    <div class="card mt-24">
      <div class="section-title">\u{1f4ca} الإحصائيات</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:center">
        <div><div style="font-size:28px;font-weight:700;color:var(--accent)">${mc}</div><div class="text-xs text-muted">وحدة نشطة</div></div>
        <div><div style="font-size:28px;font-weight:700;color:var(--green)">${buildCount}</div><div class="text-xs text-muted">APK مبني</div></div>
        <div><div style="font-size:28px;font-weight:700;color:var(--accent2)">100</div><div class="text-xs text-muted">قالب متاح</div></div>
      </div>
    </div>
    <div class="card">
      <div class="section-title">\u{1f4a1} كيف يعمل؟</div>
      <div style="display:flex;gap:16px;flex-wrap:wrap">
        <div style="flex:1;min-width:120px;padding:12px;background:var(--surface2);border-radius:8px;text-align:center">
          <div style="font-size:24px">1\ufe0f\u20e3</div>
          <div style="font-size:13px;font-weight:600;margin:4px 0">اختر قالباً</div>
          <div class="text-xs text-muted">أو اكتب وصفك</div>
        </div>
        <div style="flex:1;min-width:120px;padding:12px;background:var(--surface2);border-radius:8px;text-align:center">
          <div style="font-size:24px">2\ufe0f\u20e3</div>
          <div style="font-size:13px;font-weight:600;margin:4px 0">خصّص التطبيق</div>
          <div class="text-xs text-muted">اسم، لون، مميزات</div>
        </div>
        <div style="flex:1;min-width:120px;padding:12px;background:var(--surface2);border-radius:8px;text-align:center">
          <div style="font-size:24px">3\ufe0f\u20e3</div>
          <div style="font-size:13px;font-weight:600;margin:4px 0">ابنِ APK</div>
          <div class="text-xs text-muted">ضغط زر واحد</div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="section-title">\u{1f513} مفتوح للتكامل</div>
      <p class="text-sm text-muted" style="margin-bottom:12px">كل الوظائف محددة بملفات JS في <code>js/modules/</code>. لإضافة وظيفة جديدة أنشئ ملف JS وأضفه في <code>config/app.json</code>:</p>
      <pre style="background:var(--bg);border-radius:8px;padding:14px;font-size:12px;direction:ltr;text-align:left;overflow-x:auto;color:var(--text2)"><span style="color:var(--text3)">// js/modules/my-feature.js</span>
BardomApp.registerModule('my-id', 'الاسم', '\u{1f3af}', function() {
  return '&lt;h2&gt;محتوى جديد&lt;/h2&gt;';
});
<span style="color:var(--text3)">← لا حاجة لإعادة بناء APK!</span></pre>
    </div>
  </div>`;
});
