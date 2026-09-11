/**
 * Bardom AI - المحرك الأساسي (Core Engine)
 * الملف الرئيسي الذي يُدير الوحدات والإعدادات والأحداث
 * لا يُستدعى أي مكتبات خارجية - كل شيء ذاتي
 * 
 * مهم: يستخدم XHR بدلاً من fetch لأن WebView مع file:// لا يدعم fetch
 */

// ============================================================
// دالة تحمل ملفات تعمل مع file:// (XMLHttpRequest)
// ============================================================
function _loadJSON(path) {
    return new Promise(function(resolve, reject) {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', path, true);
            xhr.onload = function() {
                if (xhr.status === 200 || xhr.status === 0) {
                    try { resolve(JSON.parse(xhr.responseText)); }
                    catch(e) { reject(e); }
                } else { reject(new Error('HTTP ' + xhr.status)); }
            };
            xhr.onerror = function() { reject(new Error('XHR error')); };
            xhr.send();
        } catch(e) { reject(e); }
    });
}

function _loadText(path) {
    return new Promise(function(resolve, reject) {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', path, true);
            xhr.onload = function() {
                if (xhr.status === 200 || xhr.status === 0) { resolve(xhr.responseText); }
                else { reject(new Error('HTTP ' + xhr.status)); }
            };
            xhr.onerror = function() { reject(new Error('XHR error')); };
            xhr.send();
        } catch(e) { reject(e); }
    });
}

// ============================================================
// نظام إدارة الأحداث (Event Bus)
// ============================================================
class EventBus {
    constructor() {
        this._listeners = {};
    }

    on(event, callback, context) {
        if (!this._listeners[event]) this._listeners[event] = [];
        this._listeners[event].push({ fn: callback, ctx: context || null });
        return () => this.off(event, callback);
    }

    off(event, callback) {
        if (!this._listeners[event]) return;
        this._listeners[event] = this._listeners[event].filter(
            l => l.fn !== callback
        );
    }

    emit(event, data) {
        const list = this._listeners[event];
        if (!list) return;
        list.forEach(l => {
            try { l.fn.call(l.ctx, data); } catch (e) { console.error('Event error [' + event + ']:', e); }
        });
    }

    once(event, callback) {
        const wrap = (d) => { callback(d); this.off(event, wrap); };
        this.on(event, wrap);
    }
}

// ============================================================
// مدير الإعدادات (Config Manager)
// ============================================================
class ConfigManager {
    constructor() {
        this._config = null;
        this._permissions = null;
        this._userSettings = {};
        this._loadUserSettings();
    }

    async load() {
        // الأولوية: بيانات مضمنة في index.html (تعمل مع file://)
        if (typeof __EMBEDDED_APP_CONFIG !== 'undefined') {
            this._config = __EMBEDDED_APP_CONFIG;
            this._permissions = (typeof __EMBEDDED_PERMISSIONS !== 'undefined')
                ? __EMBEDDED_PERMISSIONS : null;
            this._applyUserSettings();
            console.log('[BardomAI] تم تحميل الإعدادات من البيانات المضمنة');
            return this._config;
        }
        // البديل: XHR (يعمل مع file:// في WebView)
        try {
            var results = await Promise.all([
                _loadJSON('config/app.json'),
                _loadJSON('config/permissions.json').catch(function() { return null; })
            ]);
            this._config = results[0];
            this._permissions = results[1];
            this._applyUserSettings();
            return this._config;
        } catch (e) {
            console.error('فشل تحميل الإعدادات:', e);
            return this._getDefaultConfig();
        }
    }

    _getDefaultConfig() {
        return {
            app_name: 'Bardom AI', version: '1.0.0', modules: [],
            categories: [], api: {}, build: {}
        };
    }

    _loadUserSettings() {
        try {
            const saved = localStorage.getItem('bardom_settings');
            if (saved) this._userSettings = JSON.parse(saved);
        } catch (e) { /* تجاهل */ }
    }

    _saveUserSettings() {
        try { localStorage.setItem('bardom_settings', JSON.stringify(this._userSettings)); } catch (e) { /* تجاهل */ }
    }

    _applyUserSettings() {
        if (this._userSettings.api) {
            Object.assign(this._config.api, this._userSettings.api);
        }
    }

    get config() { return this._config; }
    get permissions() { return this._permissions; }

    get(key, defaultValue) {
        if (!this._config) return defaultValue;
        return key.split('.').reduce((o, k) => (o && o[k] !== undefined) ? o[k] : defaultValue, this._config);
    }

    set(key, value) {
        if (!this._config) return;
        const keys = key.split('.');
        let obj = this._config;
        for (let i = 0; i < keys.length - 1; i++) {
            if (!obj[keys[i]]) obj[keys[i]] = {};
            obj = obj[keys[i]];
        }
        obj[keys[keys.length - 1]] = value;
        this._saveUserSettings();
    }

    getApiKey(service) {
        return this.get('api.' + service + '_api_key', '');
    }

    setApiKey(service, key) {
        this.set('api.' + service + '_api_key', key);
    }
}

// ============================================================
// سجل الوحدات (Module Registry)
// ============================================================
class ModuleRegistry {
    constructor(eventBus) {
        this._modules = new Map();
        this._events = eventBus;
        this._activeId = null;
    }

    register(id, name, icon, renderFn, initFn) {
        this._modules.set(id, { id, name, icon, renderFn, initFn, initialized: false });
        this._events.emit('module:registered', { id, name });
    }

    get(id) { return this._modules.get(id); }

    getAll() { return Array.from(this._modules.values()); }

    get count() { return this._modules.size; }

    get active() { return this._activeId; }

    async activate(id) {
        const mod = this._modules.get(id);
        if (!mod) return;
        this._activeId = id;

        if (!mod.initialized && mod.initFn) {
            try {
                await mod.initFn();
                mod.initialized = true;
            } catch (e) {
                console.error('فشل تهيئة الوحدة:', id, e);
            }
        }

        this._events.emit('module:activated', mod);
        return mod;
    }
}

// ============================================================
// محرك القوالب (Template Engine)
// ============================================================
class TemplateEngine {
    render(htmlString, container) {
        if (typeof container === 'string') container = document.querySelector(container);
        if (!container) return null;
        container.innerHTML = htmlString;
        return container;
    }

    component(tag, props, children) {
        let attrs = '';
        if (props) {
            Object.entries(props).forEach(([k, v]) => {
                if (k === 'className') k = 'class';
                if (k === 'onclick' || k === 'style') {
                    attrs += ' ' + k + '="' + String(v).replace(/"/g, '&quot;') + '"';
                } else if (k.startsWith('data-') || k === 'id') {
                    attrs += ' ' + k + '="' + v + '"';
                } else {
                    attrs += ' ' + k + '="' + String(v).replace(/"/g, '&quot;') + '"';
                }
            });
        }
        return '<' + tag + attrs + '>' + (children || '') + '</' + tag + '>';
    }
}

// ============================================================
// مدير الملفات (File Manager)
// ============================================================
class FileManager {
    constructor() {
        this._bridge = window.AndroidBridge || null;
    }

    async saveFile(name, content) {
        if (this._bridge && this._bridge.saveFile) {
            return this._bridge.saveFile(name, content);
        }
        // Fallback: IndexedDB
        return this._idbSave(name, content);
    }

    async readFile(name) {
        if (this._bridge && this._bridge.readFile) {
            return this._bridge.readFile(name);
        }
        return this._idbRead(name);
    }

    async listFiles(dir) {
        if (this._bridge && this._bridge.listFiles) {
            return JSON.parse(this._bridge.listFiles(dir));
        }
        return this._idbList(dir);
    }

    async _idbSave(name, content) {
        const db = await this._getDb();
        const tx = db.transaction('files', 'readwrite');
        tx.objectStore('files').put({ name, content, updated: Date.now() });
        return new Promise((res, rej) => {
            tx.oncomplete = () => res(true);
            tx.onerror = () => rej(tx.error);
        });
    }

    async _idbRead(name) {
        const db = await this._getDb();
        const tx = db.transaction('files', 'readonly');
        const req = tx.objectStore('files').get(name);
        return new Promise((res, rej) => {
            req.onsuccess = () => res(req.result ? req.result.content : null);
            req.onerror = () => rej(req.error);
        });
    }

    async _idbList(dir) {
        const db = await this._getDb();
        const tx = db.transaction('files', 'readonly');
        const req = tx.objectStore('files').getAll();
        return new Promise((res, rej) => {
            req.onsuccess = () => {
                const files = req.result || [];
                const prefix = dir ? dir + '/' : '';
                res(files.filter(f => f.name.startsWith(prefix)));
            };
            req.onerror = () => rej(req.error);
        });
    }

    _getDb() {
        if (!this._dbPromise) {
            this._dbPromise = new Promise((resolve, reject) => {
                const req = indexedDB.open('BardomAI', 1);
                req.onupgradeneeded = (e) => {
                    e.target.result.createObjectStore('files', { keyPath: 'name' });
                };
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
        }
        return this._dbPromise;
    }
}

// ============================================================
// خط أنابيب البناء (Build Pipeline)
// ============================================================
class BuildPipeline {
    constructor(eventBus) {
        this._events = eventBus;
        this._steps = [];
        this._currentStep = 0;
        this._running = false;
    }

    setSteps(steps) {
        this._steps = steps;
    }

    async run(context) {
        if (this._running) throw new Error('يوجد بناء آخر قيد التشغيل');
        this._running = true;
        this._currentStep = 0;
        const results = [];
        try {
            for (let i = 0; i < this._steps.length; i++) {
                this._currentStep = i;
                const step = this._steps[i];
                this._events.emit('build:step', {
                    index: i, name: step.name, status: 'running'
                });
                const startTime = Date.now();
                const result = await step.execute(context);
                const elapsed = Date.now() - startTime;
                results.push({ ...step, result, elapsed, status: 'done' });
                this._events.emit('build:progress', {
                    percent: Math.round(((i + 1) / this._steps.length) * 100),
                    step: step.name, elapsed
                });
            }
            this._events.emit('build:complete', { results, context });
            return results;
        } catch (e) {
            this._events.emit('build:error', { error: e.message, step: this._currentStep });
            throw e;
        } finally {
            this._running = false;
        }
    }
}

// ============================================================
// محرك الذكاء الاصطناعي (AI Engine)
// ============================================================
class AIEngine {
    constructor(configManager) {
        this._config = configManager;
        this._conversationHistory = [];
    }

    async chat(userMessage, systemPrompt) {
        const apiKey = this._config.getApiKey('openrouter');
        if (!apiKey) {
            throw new Error('مفتاح OpenRouter API غير معين. اذهب إلى الإعدادات.');
        }

        this._conversationHistory.push({ role: 'user', content: userMessage });
        const messages = [];
        if (systemPrompt) messages.push({ role: 'system', content: systemPrompt });
        messages.push(...this._conversationHistory);

        const url = this._config.get('api.openrouter_url');
        const model = this._config.get('api.openrouter_model');

        const resp = await new Promise(function(resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', url, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Authorization', 'Bearer ' + apiKey);
            xhr.onload = function() {
                if (xhr.status === 200) {
                    try { resolve(JSON.parse(xhr.responseText)); }
                    catch(e) { reject(e); }
                } else {
                    try {
                        var err = JSON.parse(xhr.responseText);
                        reject(new Error(err.error && err.error.message ? err.error.message : 'HTTP ' + xhr.status));
                    } catch(e) { reject(new Error('HTTP ' + xhr.status)); }
                }
            };
            xhr.onerror = function() { reject(new Error('فشل الاتصال بالخادم')); };
            xhr.timeout = 60000;
            xhr.ontimeout = function() { reject(new Error('انتهت مهلة الاتصال')); };
            xhr.send(JSON.stringify({ model: model, messages: messages, temperature: 0.3, max_tokens: 40000 }));
        });
        const reply = (resp.choices && resp.choices[0] && resp.choices[0].message) ? resp.choices[0].message.content : '';
        this._conversationHistory.push({ role: 'assistant', content: reply });
        return reply;
    }

    clearHistory() {
        this._conversationHistory = [];
    }
}

// ============================================================
// التطبيق الرئيسي (Bardom App)
// ============================================================
const BardomApp = {
    _events: null,
    _config: null,
    _modules: null,
    _template: null,
    _files: null,
    _build: null,
    _ai: null,
    _ready: false,

    async init() {
        console.log('[BardomAI] تهيئة النظام...');
        this._events = new EventBus();
        this._config = new ConfigManager();
        this._modules = new ModuleRegistry(this._events);
        this._template = new TemplateEngine();
        this._files = new FileManager();
        this._build = new BuildPipeline(this._events);
        this._ai = new AIEngine(this._config);

        await this._config.load();
        await this._loadModules();
        this._renderShell();
        await this._modules.activate('home');
        this._ready = true;
        this._events.emit('app:ready', {});
        console.log('[BardomAI] جاهز - ' + this._modules.count + ' وحدة محملة');
    },

    async _loadModules() {
        const moduleFiles = this._config.get('modules', []);
        const loadPromises = moduleFiles.map(file => {
            return new Promise((resolve) => {
                const script = document.createElement('script');
                script.src = 'js/' + file;
                script.onload = () => resolve(true);
                script.onerror = () => {
                    console.warn('[BardomAI] فشل تحميل الوحدة:', file);
                    resolve(false);
                };
                document.head.appendChild(script);
            });
        });
        await Promise.all(loadPromises);
    },

    _renderShell() {
        const modules = this._modules.getAll();
        const version = this._config.get('version', '1.0.0');

        // الشريط الجانبي
        const sidebarItems = modules.map(m =>
            '<div class="nav-item" data-module="' + m.id + '" onclick="BardomApp.navigateTo(\'' + m.id + '\')">' +
            '<span class="nav-icon">' + m.icon + '</span>' +
            '<span class="nav-label">' + m.name + '</span></div>'
        ).join('');

        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.innerHTML =
            '<div class="sidebar-header"><h2>Bardom AI</h2><span class="version">v' + version + '</span></div>' +
            '<div class="sidebar-nav">' + sidebarItems + '</div>';

        // شريط التنقل السفلي للموبايل
        const bottomNav = document.getElementById('bottomNav');
        if (bottomNav) {
            const quickModules = modules.slice(0, 4);
            bottomNav.innerHTML = quickModules.map(m =>
                '<div class="bottom-nav-item" data-module="' + m.id + '" onclick="BardomApp.navigateTo(\'' + m.id + '\')">' +
                '<span class="bnav-icon">' + m.icon + '</span>' +
                '<span class="bnav-label">' + m.name + '</span></div>'
            ).join('');
        }

        // شريط الحالة
        this._updateStatusBar();
    },

    _updateStatusBar() {
        const bar = document.getElementById('statusBar');
        if (!bar) return;
        const mc = this._modules.count;
        const lastBuild = localStorage.getItem('bardom_last_build') || 'لم يتم بعد';
        bar.innerHTML =
            '<span>💾 الوحدات: <strong>' + mc + '</strong></span>' +
            '<span>🔄 آخر بناء: ' + lastBuild + '</span>' +
            '<span>✅ يعمل بالملفات - بدون إعادة بناء APK</span>';
    },

    async navigateTo(moduleId) {
        const mod = await this._modules.activate(moduleId);
        if (!mod) return;

        // تحديث التنقل النشط
        document.querySelectorAll('.nav-item, .bottom-nav-item').forEach(el => {
            el.classList.toggle('active', el.dataset.module === moduleId);
        });

        // تقديم المحتوى
        const main = document.getElementById('mainContent');
        if (main && mod.renderFn) {
            main.innerHTML = mod.renderFn();
        }

        // إغلاق الشريط الجانبي على الموبايل
        document.getElementById('sidebar')?.classList.remove('open');
        document.getElementById('overlay')?.classList.remove('active');

        // تحديث العنوان
        const title = document.getElementById('pageTitle');
        if (title) title.textContent = mod.name;
    },

    // ---- واجهات عامة ----
    registerModule(id, name, icon, renderFn, initFn) {
        this._modules.register(id, name, icon, renderFn, initFn);
    },

    showToast(msg, type) {
        type = type || 'info';
        const t = document.getElementById('toast');
        if (!t) { alert(msg); return; }
        const colors = { info: '#58a6ff', success: '#3fb950', error: '#f85149', warning: '#d29922' };
        t.style.borderLeft = '4px solid ' + (colors[type] || colors.info);
        t.textContent = msg;
        t.classList.add('show');
        clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
    },

    showModal(title, contentHtml, actions) {
        const modal = document.getElementById('modal');
        if (!modal) return;
        const mTitle = document.getElementById('modalTitle');
        const mBody = document.getElementById('modalBody');
        const mActions = document.getElementById('modalActions');
        if (mTitle) mTitle.textContent = title;
        if (mBody) mBody.innerHTML = contentHtml;
        if (mActions) {
            mActions.innerHTML = (actions || []).map(a =>
                '<button class="btn btn-' + (a.type || 'primary') + '" onclick="(' + a.action + ')(); BardomApp.closeModal()">' + a.label + '</button>'
            ).join('') + '<button class="btn btn-ghost" onclick="BardomApp.closeModal()">إغلاق</button>';
        }
        modal.classList.add('active');
    },

    closeModal() {
        document.getElementById('modal')?.classList.remove('active');
    },

    showLoading(msg) {
        const overlay = document.getElementById('loadingOverlay');
        const text = document.getElementById('loadingText');
        if (overlay) overlay.classList.add('active');
        if (text) text.textContent = msg || 'جاري التحميل...';
    },

    hideLoading() {
        document.getElementById('loadingOverlay')?.classList.remove('active');
    },

    get events() { return this._events; },
    get config() { return this._config; },
    get modules() { return this._modules; },
    get template() { return this._template; },
    get files() { return this._files; },
    get build() { return this._build; },
    get ai() { return this._ai; },
    get isReady() { return this._ready; }
};

// ---- نقطة البدء ----
document.addEventListener('DOMContentLoaded', () => BardomApp.init());
