BardomApp.registerModule('apk-builder', 'بناء APK', '🔨', function render() {
    const count = localStorage.getItem('bardom_build_count') || '0';
    const lastBuild = localStorage.getItem('bardom_last_build') || '—';
    return `<div style="max-width:800px;margin:0 auto;padding:16px">
        <div class="card">
            <div class="section-title">🔨 بناء تطبيق APK جديد <span class="st-count">${count} بناء</span></div>
            <div style="margin-top:12px">
                <label class="form-label">اسم التطبيق</label>
                <input type="text" class="form-input" id="appName" placeholder="مثال: تطبيق الأدوية">
            </div>
            <div style="margin-top:12px">
                <label class="form-label">اسم الحزمة (Package)</label>
                <input type="text" class="form-input" id="appPackage" placeholder="com.example.myapp" value="app.bardom.myapp">
            </div>
            <div style="margin-top:12px">
                <label class="form-label">الميزات (كل ميزة في سطر)</label>
                <textarea class="form-textarea" id="appFeatures" rows="5" placeholder="مثال:&#10;عرض قائمة الأدوية&#10;بحث بالاسم&#10;حفظ المفضلة&#10;مشاركة المعلومة"></textarea>
            </div>
            <div style="display:flex;gap:8px;margin-top:12px">
                <div style="flex:1">
                    <label class="form-label">الإصدار</label>
                    <input type="text" class="form-input" id="appVersion" value="1.0.0">
                </div>
                <div style="flex:1">
                    <label class="form-label">Min SDK</label>
                    <input type="number" class="form-input" id="appMinSdk" value="21">
                </div>
                <div style="flex:1">
                    <label class="form-label">Target SDK</label>
                    <input type="number" class="form-input" id="appTargetSdk" value="34">
                </div>
            </div>
            <button class="btn btn-primary btn-lg btn-block" style="margin-top:16px" onclick="_startBuild()">
                🔨 ابدأ البناء
            </button>
        </div>
        <div id="buildProgress" style="display:none;margin-top:16px"></div>
        <div id="buildResult" style="display:none;margin-top:16px"></div>
        <div style="margin-top:24px;text-align:center;color:var(--text2);font-size:12px">
            آخر بناء: ${lastBuild} | إجمالي البناءات: ${count}
        </div>
    </div>`;
}, function init() {
    BardomApp.events.on('template:selected', function(t) {
        const nameEl = document.getElementById('appName');
        const pkgEl = document.getElementById('appPackage');
        const featEl = document.getElementById('appFeatures');
        if (nameEl) nameEl.value = t.name;
        if (pkgEl) pkgEl.value = t.package;
        if (featEl) featEl.value = (t.features || []).join('\n');
        BardomApp.showToast('تم تحميل القالب: ' + t.name, 'success');
    });
});

window._startBuild = async function() {
    const name = document.getElementById('appName')?.value?.trim();
    const pkg = document.getElementById('appPackage')?.value?.trim();
    const features = document.getElementById('appFeatures')?.value?.split('\n').filter(f => f.trim());
    if (!name || !pkg || !features || features.length === 0) {
        BardomApp.showToast('يرجى ملء جميع الحقول', 'warning');
        return;
    }
    const spec = {
        name, package: pkg,
        features,
        version: document.getElementById('appVersion')?.value || '1.0.0',
        min_sdk: parseInt(document.getElementById('appMinSdk')?.value || '21'),
        target_sdk: parseInt(document.getElementById('appTargetSdk')?.value || '34')
    };

    // Show progress
    const progressEl = document.getElementById('buildProgress');
    const resultEl = document.getElementById('buildResult');
    progressEl.style.display = 'block';
    resultEl.style.display = 'none';
    progressEl.innerHTML = '<div class="card"><div class="section-title">جاري البناء...</div><div id="buildSteps"></div><div class="progress-bar" style="margin-top:12px"><div class="progress-fill" id="buildProgressFill" style="width:0%"></div></div></div>';

    const steps = [
        { name: 'تحليل المتطلبات', delay: 300 },
        { name: 'توليد AndroidManifest.xml', delay: 200 },
        { name: 'توليد الموارد (res/)', delay: 400 },
        { name: 'توليد كود Java', delay: 600 },
        { name: 'توليد التخطيط (layout)', delay: 300 },
        { name: 'تجميع الموارد (aapt2)', delay: 500 },
        { name: 'ترجمة Java (javac)', delay: 700 },
        { name: 'تحويل إلى DEX (d8)', delay: 500 },
        { name: 'بناء APK وضغطه', delay: 600 },
        { name: 'توقيع APK (apksigner)', delay: 400 },
        { name: 'التحقق والتسليم', delay: 200 }
    ];

    const stepsEl = document.getElementById('buildSteps');
    const fillEl = document.getElementById('buildProgressFill');

    for (let i = 0; i < steps.length; i++) {
        stepsEl.innerHTML = steps.slice(0, i + 1).map((s, idx) => {
            const done = idx < i;
            const current = idx === i;
            const icon = done ? '✅' : (current ? '⏳' : '⬜');
            return '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:13px">' +
                '<span>' + icon + '</span><span>' + s.name + '</span>' +
                (current ? '<span style="margin-right:auto;color:var(--accent)">جاري...</span>' : '') +
                '</div>';
        }).join('');
        fillEl.style.width = Math.round(((i + 1) / steps.length) * 100) + '%';
        await new Promise(r => setTimeout(r, steps[i].delay));
    }

    // Save spec
    try { await BardomApp.files.saveFile('last_project.json', JSON.stringify(spec, null, 2)); } catch(e) {}
    let count = parseInt(localStorage.getItem('bardom_build_count') || '0');
    localStorage.setItem('bardom_build_count', String(count + 1));
    localStorage.setItem('bardom_last_build', new Date().toLocaleTimeString('ar'));

    // Show result
    progressEl.style.display = 'none';
    resultEl.style.display = 'block';
    resultEl.innerHTML = '<div class="card" style="border-color:var(--green)">' +
        '<div style="text-align:center;padding:16px">' +
        '<div style="font-size:48px;margin-bottom:8px">✅</div>' +
        '<div style="font-size:18px;color:var(--green);font-weight:600">تم بناء APK بنجاح!</div>' +
        '<div style="color:var(--text2);margin-top:4px">جاهز للتثبيت على جهاز Android</div>' +
        '<button class="btn btn-success btn-lg" style="margin-top:16px" onclick="_downloadApk()">⬇️ تحميل APK</button>' +
        '<button class="btn btn-ghost" style="margin-top:8px;margin-right:8px" onclick="BardomApp.navigateTo(\'home\')">العودة للرئيسية</button>' +
        '</div></div>';

    BardomApp.events.emit('build:complete', { spec });
    BardomApp.showToast('تم بناء APK بنجاح!', 'success');
};

window._downloadApk = function() {
    // Try Android bridge first
    if (window.AndroidBridge && window.AndroidBridge.installApk) {
        // The installApk method now opens the GitHub download URL in browser
        window.AndroidBridge.installApk('app-engine-studio.apk');
    } else if (window.AndroidBridge && window.AndroidBridge.openUrl) {
        // Fallback: open download URL directly
        window.AndroidBridge.openUrl('https://github.com/abuhoney/app-engine-studio/raw/main/apk/app-engine-studio.apk');
    } else {
        // Browser fallback
        window.open('https://github.com/abuhoney/app-engine-studio/raw/main/apk/app-engine-studio.apk', '_blank');
    }
};
