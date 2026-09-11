(function() {
  'use strict';
  const MODULES = ['js/core.js', 'js/engine-studio.js', 'data/templates-data.js'];
  let loaded = 0;
  function load(src) {
    return new Promise(resolve => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = () => { loaded++; console.log('[index.js] Loaded ' + loaded + '/' + MODULES.length + ': ' + src); resolve(); };
      s.onerror = () => { console.error('[index.js] FAILED: ' + src); resolve(); };
      document.head.appendChild(s);
    });
  }
  async function init() {
    for (const src of MODULES) await load(src);
    console.log('[index.js] All modules loaded!');
    try {
      if (typeof seedDefaults === 'function') seedDefaults();
      if (typeof renderAll === 'function') renderAll();
      if (typeof tsLoadDefault === 'function') tsLoadDefault();
      if (typeof adsLoadDefault === 'function') adsLoadDefault();
      if (typeof idLoadDefault === 'function') idLoadDefault();
      if (typeof tgInit === 'function') tgInit();
    } catch(e) { console.error('[index.js] Init:', e); }
    if (typeof AndroidBridge !== 'undefined') console.log('[index.js] Running in APK');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();