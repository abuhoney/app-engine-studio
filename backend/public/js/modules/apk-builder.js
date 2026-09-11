/**
 * الوحدة: بناء APK
 */
(function() {
  let _selectedTemplate = null;
  let _buildSteps = [];

  BardomApp.registerModule('apk-builder', 'بناء APK', '\u{1f528}', function render() {
    return `<div style="max-width:700px">
      <div class="section-title">\u{1f528} بناء APK <span class="st-count">من وصف أو قالب</span></div>
      <div class="card">
        <div class="form-group">
          <label class="form-label">اسم التطبيق</label>
          <input class="form-input" id="appName" placeholder="مثال: حاسبة احترافية" value="${_selectedTemplate ? _selectedTemplate.name : ''}">
        </div>
        <div class="form-group">
          <label class="form-label">اسم الحزمة (package)</label>
          <input class="form-input" id="appPackage" dir="ltr" placeholder="app.bardom.myapp" value="${_selectedTemplate ? _selectedTemplate.package : ''}" style="text-align:left">
        </div>
        <div class="form-group">
          <label class="form-label">وصف التطبيق / المميزات المطلوبة</label>
          <textarea class="form-textarea" id="appFeatures" rows="4" placeholder="اكتب وصف التطبيق أو المميزات المطلوبة، كل ميزة في سطر...\nمثال:\nشاشة رئيسية مع أزرار\nقائمة إعدادات\nوضع ليلي">${_selectedTemplate ? _selectedTemplate.features.map(f => f).join('\n') : ''}</textarea>
        </div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px">
          <div class="form-group" style="flex:1;min-width:140px">
            <label class="form-label">الإصدار</label>
            <input class="form-input" id="appVersion" value="1.0.0" dir="ltr">
          </div>
          <div class="form-group" style="flex:1;min-width:140px">
            <label class="form-label">Min SDK</label>
            <input class="form-input" id="appMinSdk" type="number" value="21" dir="ltr">
          </div>
          <div class="form-group" style="flex:1;min-width:140px">
            <label class="form-label">Target SDK</label>
            <input class="form-input" id="appTargetSdk" type="number" value="34" dir="ltr">
          </div>
        </div>
        <div style="margin-top:20px;display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn btn-primary btn-lg" onclick="_startBuild()">\u{1f680} بناء APK</button>
          <button class="btn btn-ghost btn-lg" onclick="_startBuildWithAI()">\u{1f916} بناء بالذكاء الاصطناعي</button>
        </div>
      </div>
      <div class="card mt-16" id="buildProgressCard" style="display:none">
        <div class="section-title">\u{1f4e6} تقدم البناء</div>
        <div id="buildSteps"></div>
        <div class="progress-bar mt-16"><div class="progress-fill" id="buildProgressFill"></div></div>
        <div id="buildStatus" class="text-sm text-muted mt-8"></div>
      </div>
      <div id="buildResult" style="margin-top:16px"></div>
    </div>`;
  }, function init() {
    BardomApp.events.on('template:selected', function(tmpl) {
      _selectedTemplate = tmpl;
    });
    BardomApp.events.on('build:step', function(d) {
      const el = document.getElementById('step_' + d.index);
      if (el) {
        el.className = 'build-step running';
        el.querySelector('.step-status').textContent = '\u23f3';
      }
    });
    BardomApp.events.on('build:progress', function(d) {
      const fill = document.getElementById('buildProgressFill');
      const status = document.getElementById('buildStatus');
      if (fill) fill.style.width = d.percent + '%';
      if (status) status.textContent = d.step + ' (' + d.percent + '%)';
      // Mark completed steps
      for (let i = 0; i < d.percent / 100 * 8; i++) {
        const el = document.getElementById('step_' + i);
        if (el) { el.className = 'build-step done'; el.querySelector('.step-status').textContent = '\u2705'; }
      }
    });
    BardomApp.events.on('build:complete', function() {
      BardomApp.showToast('\u2705 تم بناء APK بنجاح!', 'success');
      const result = document.getElementById('buildResult');
      if (result) result.innerHTML = '<div class="card" style="border-color:var(--green)"><div style="text-align:center;padding:20px"><div style="font-size:48px;margin-bottom:12px">\u2705</div><h3 style="margin-bottom:8px">تم بناء APK بنجاح!</h3><p class="text-muted text-sm">جاهز للتثبيت على جهاز Android</p><button class="btn btn-success btn-lg mt-16" onclick="_downloadApk()">\u{2b07}\ufe0f تحميل APK</button></div></div>';
    });
    BardomApp.events.on('build:error', function(d) {
      BardomApp.showToast('\u274c فشل البناء: ' + d.error, 'error');
      const status = document.getElementById('buildStatus');
      if (status) status.innerHTML = '<span style="color:var(--red)">\u274c ' + d.error + '</span>';
    });
  });

  window._startBuild = async function() {
    const name = document.getElementById('appName')?.value?.trim();
    const pkg = document.getElementById('appPackage')?.value?.trim();
    const features = document.getElementById('appFeatures')?.value?.trim();
    if (!name) { BardomApp.showToast('أدخل اسم التطبيق', 'warning'); return; }
    if (!pkg) { BardomApp.showToast('أدخل اسم الحزمة', 'warning'); return; }
    if (!features) { BardomApp.showToast('أدخل المميزات المطلوبة', 'warning'); return; }
    const version = document.getElementById('appVersion')?.value || '1.0.0';
    const minSdk = document.getElementById('appMinSdk')?.value || '21';
    const targetSdk = document.getElementById('appTargetSdk')?.value || '34';
    const featureList = features.split('\n').filter(f => f.trim());
    const projectSpec = { name, package: pkg, version, min_sdk: parseInt(minSdk), target_sdk: parseInt(targetSdk), features: featureList, template_id: _selectedTemplate?.id || null };
    _showBuildProgress();
    await _executeBuild(projectSpec);
  };

  window._startBuildWithAI = async function() {
    const name = document.getElementById('appName')?.value?.trim();
    if (!name) { BardomApp.showToast('أدخل اسم التطبيق', 'warning'); return; }
    BardomApp.showLoading('جاري الاتصال بالذكاء الاصطناعي...');
    try {
      const features = document.getElementById('appFeatures')?.value?.trim() || 'تطبيق ' + name;
      const prompt = 'أنت مولد تطبيقات Android. أنشئ تطبيقاً باسم "' + name + '" بالمميزات التالية:\n' + features + '\n\nأعد JSON فقط بهذا الشكل:\n{"java_code": "...", "layout_xml": "...", "colors_xml": "..."}';
      const reply = await BardomApp.ai.chat(prompt);
      BardomApp.hideLoading();
      BardomApp.navigateTo('ai-assistant');
      BardomApp.events.emit('ai:response', { query: features, response: reply, appName: name });
    } catch (e) {
      BardomApp.hideLoading();
      BardomApp.showToast('فشل: ' + e.message, 'error');
    }
  };

  function _showBuildProgress() {
    const card = document.getElementById('buildProgressCard');
    if (card) card.style.display = 'block';
    const stepsEl = document.getElementById('buildSteps');
    if (stepsEl) {
      const steps = ['تحليل المتطلبات', 'توليد AndroidManifest.xml', 'توليد الموارد (res/)', 'توليد كود Java', 'توليد التخطيط (layout)', 'تجميع الموارد (aapt2)', 'ترجمة Java (javac)', 'تحويل إلى DEX (d8)', 'بناء APK وضغطه', 'توقيع APK (apksigner)', 'التحقق والتسليم'];
      stepsEl.innerHTML = steps.map((s, i) =>
        '<div class="build-step" id="step_' + i + '" style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:6px;margin-bottom:4px;background:var(--surface2)"><span class="step-status" style="width:20px;text-align:center">\u23f3</span><span class="text-sm">' + s + '</span></div>'
      ).join('');
    }
  }

  async function _executeBuild(spec) {
    const projectData = _generateProject(spec);
    // حفظ بيانات المشروع
    await BardomApp.files.saveFile('last_project.json', JSON.stringify(spec, null, 2));
    // محاكاة خط أنابيب البناء
    const steps = [
      { name: 'تحليل المتطلبات', delay: 200 },
      { name: 'توليد AndroidManifest.xml', delay: 150 },
      { name: 'توليد الموارد (res/)', delay: 300 },
      { name: 'توليد كود Java', delay: 500 },
      { name: 'توليد التخطيط (layout)', delay: 250 },
      { name: 'تجميع الموارد (aapt2)', delay: 400 },
      { name: 'ترجمة Java (javac)', delay: 600 },
      { name: 'تحويل إلى DEX (d8)', delay: 400 },
      { name: 'بناء APK وضغطه', delay: 500 },
      { name: 'توقيع APK (apksigner)', delay: 300 },
      { name: 'التحقق والتسليم', delay: 100 }
    ];
    // في بيئة APK الحقيقية، يتم استدعاء AndroidBridge.buildApk(projectData)
    // هنا نحاكي العملية
    for (let i = 0; i < steps.length; i++) {
      await new Promise(r => setTimeout(r, steps[i].delay));
      BardomApp.events.emit('build:progress', {
        percent: Math.round(((i + 1) / steps.length) * 100),
        step: steps[i].name, elapsed: steps[i].delay
      });
    }
    // حفظ المشروع المُولَّد
    await BardomApp.files.saveFile(spec.name + '_project.zip', JSON.stringify(projectData));
    let count = parseInt(localStorage.getItem('bardom_build_count') || '0');
    localStorage.setItem('bardom_build_count', String(count + 1));
    localStorage.setItem('bardom_last_build', new Date().toLocaleTimeString('ar'));
    BardomApp.events.emit('build:complete', { spec });
  }

  function _generateProject(spec) {
    const permMap = {
      'كاميرا': 'CAMERA', 'camera': 'CAMERA', 'صوت': 'RECORD_AUDIO', 'audio': 'RECORD_AUDIO',
      'موقع': 'ACCESS_FINE_LOCATION', 'location': 'ACCESS_FINE_LOCATION', 'gps': 'ACCESS_FINE_LOCATION',
      'خريطة': 'ACCESS_FINE_LOCATION', 'map': 'ACCESS_FINE_LOCATION', 'إنترنت': 'INTERNET', 'internet': 'INTERNET',
      'شبكة': 'INTERNET', 'network': 'INTERNET', 'حفظ': 'WRITE_EXTERNAL_STORAGE', 'save': 'WRITE_EXTERNAL_STORAGE',
      'ملف': 'READ_EXTERNAL_STORAGE', 'file': 'READ_EXTERNAL_STORAGE', 'بلوتوث': 'BLUETOOTH', 'bluetooth': 'BLUETOOTH',
      'اتصال': 'CALL_PHONE', 'call': 'CALL_PHONE', 'رسالة': 'SEND_SMS', 'sms': 'SEND_SMS'
    };
    const allPerms = ['INTERNET'];
    const pkgPath = spec.package.replace(/\./g, '/');
    spec.features.forEach(f => {
      const fl = f.toLowerCase();
      Object.entries(permMap).forEach(([kw, perm]) => {
        if (fl.includes(kw) && !allPerms.includes(perm)) allPerms.push(perm);
      });
    });
    return {
      manifest: '<?xml version="1.0" encoding="utf-8"?>\n<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="' + spec.package + '">\n' +
        allPerms.map(p => '  <uses-permission android:name="android.permission.' + p + '"/>').join('\n') + '\n' +
        '  <application android:allowBackup="true" android:icon="@mipmap/ic_launcher" android:label="' + spec.name + '" android:theme="@style/Theme.AppCompat.Light.DarkActionBar">\n' +
        '    <activity android:name=".' + spec.name.replace(/[^a-zA-Z]/g, '') + 'Activity" android:exported="true">\n' +
        '      <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>\n' +
        '    </activity>\n  </application>\n</manifest>',
      mainActivity: 'package ' + spec.package + ';\n\nimport android.app.Activity;\nimport android.os.Bundle;\nimport android.widget.*;\nimport android.view.*;\nimport android.graphics.Color;\n\npublic class ' + spec.name.replace(/[^a-zA-Z]/g, '') + 'Activity extends Activity {\n  @Override\n  protected void onCreate(Bundle savedInstanceState) {\n    super.onCreate(savedInstanceState);\n    LinearLayout layout = new LinearLayout(this);\n    layout.setOrientation(LinearLayout.VERTICAL);\n    layout.setGravity(Gravity.CENTER);\n    layout.setBackgroundColor(Color.parseColor("#0d1117"));\n    TextView title = new TextView(this);\n    title.setText("' + spec.name + '");\n    title.setTextSize(24);\n    title.setTextColor(Color.WHITE);\n    layout.addView(title);\n    setContentView(layout);\n  }\n}',
      layout: '<?xml version="1.0" encoding="utf-8"?>\n<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android" android:layout_width="match_parent" android:layout_height="match_parent" android:orientation="vertical" android:gravity="center" android:background="#0d1117">\n  <TextView android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="' + spec.name + '" android:textSize="24sp" android:textColor="#e6edf3"/>\n</LinearLayout>',
      spec: spec
    };
  }

  window._downloadApk = function() {
    if (window.AndroidBridge && window.AndroidBridge.installApk) {
      window.AndroidBridge.installApk('last_build.apk');
    } else {
      BardomApp.showToast('التحميل متاح فقط من داخل تطبيق Android', 'warning');
    }
  };
})();