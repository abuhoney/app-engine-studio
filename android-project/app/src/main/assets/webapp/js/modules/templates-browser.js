/**
 * الوحدة: مستعرض القوالب
 */
(function() {
  let _templates = [];
  let _filtered = [];
  let _currentCat = 'all';

  BardomApp.registerModule('templates-browser', 'القوالب', '\u{1f4cb}', function render() {
    const cats = BardomApp.config.get('categories', []);
    return `<div>
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:20px">
        <div class="section-title" style="margin:0">\u{1f4cb} 100 قالب جاهز <span class="st-count">(${_filtered.length} قالب)</span></div>
        <div style="display:flex;gap:8px;align-items:center">
          <input class="form-input" id="templateSearch" placeholder="\u{1f50d} بحث..." style="width:200px" oninput="_filterTemplates()">
        </div>
      </div>
      <div id="catTabs" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:20px">
        <button class="btn ${_currentCat==='all'?'btn-primary':'btn-ghost'}" onclick="_setCat('all')" style="font-size:12px;padding:6px 12px">الكل</button>
        ${cats.map(c => `<button class="btn ${_currentCat===c.id?'btn-primary':'btn-ghost'}" onclick="_setCat('${c.id}')" style="font-size:12px;padding:6px 12px">${c.icon} ${c.name}</button>`).join('')}
      </div>
      <div id="templatesGrid" class="grid-4">
        ${_renderCards()}
      </div>
    </div>`;
  }, async function init() {
    await _loadTemplates();
    _filtered = _templates;
  });

  async function _loadTemplates() {
    try {
      _templates = await _loadJSON('data/templates.json');
      return;
    } catch(e) {
      console.warn('[templates] فشل تحميل الملف، استخدام القائمة المُولَّدة');
    }
    // Generate from individual files or fallback
    _templates = _generateFallback();
  }

  function _generateFallback() {
    const cats = BardomApp.config.get('categories', []);
    const names = {
      utility:['Calculator','Notes','Todo','Flashlight','Compass','Stopwatch','Timer','QR Generator','QR Scanner','Unit Converter'],
      social:['Chat','Contacts','Email','Walkie Talkie','Forum','RSS','Social Feed','Messenger','Blog Reader','Podcast'],
      media:['Music Player','Video Player','Camera','Photo Editor','Audio Recorder','Gallery','Radio','Soundboard','Lyrics','Metronome'],
      productivity:['Calendar','File Manager','PDF Reader','Document Scanner','Cloud Drive','Markdown Editor','Password Manager','Habit Tracker','Expense Tracker','Weather'],
      education:['Flashcards','Dictionary','Quiz','Language Learner','Math Trainer','Periodic Table','World Map','Spelling Bee','Geography Quiz','Typing Tutor'],
      games:['Tic-Tac-Toe','Memory Match','Snake','2048','Sudoku','Minesweeper','Pong','Brick Breaker','Word Search','Hangman'],
      health:['Step Counter','Water Reminder','Heart Rate','Meditation','Sleep Tracker','Workout Tracker','Calorie Counter','Yoga Guide','Cycle Tracker','BMI Calculator'],
      travel:['Maps','Compass Plus','Translator','Currency Converter','Travel Planner','Speedometer','Altimeter','Parking Reminder','Hiking Tracker','Geocaching'],
      smart_home:['Smart Home','Plant Monitor','Thermostat','Doorbell','Robot Vacuum','Lighting','Sprinkler','Garage Door','Pet Feeder','Air Quality'],
      finance:['Tip Calculator','Stock Tracker','Budget Planner','Loan Calculator','Invoice Maker','Crypto Tracker','Receipt Scanner','Bill Splitter','Donation Tracker','Tax Estimator']
    };
    const descs = {
      utility:['حاسبة بسيطة','تطبيق ملاحظات','قائمة مهام','كشاف ضوئي','بوصلة','ساعة إيقاف','مؤقت','مولد QR','ماسح QR','محول وحدات'],
      social:['دردشة','جهات اتصال','بريد إلكتروني','اتصال صوتي','منتدى','قارئ RSS','تغذية اجتماعية','مراسل','قارئ مدونات','مشغل بودكاست'],
      media:['مشغل موسيقى','مشغل فيديو','كاميرا','محرر صور','مسجل صوت','معرض صور','راديو','لوحة أصوات','كلمات أغاني','ميترونوم'],
      productivity:['تقويم','مدير ملفات','قارئ PDF','ماسح مستندات','قرص سحابي','محرر Markdown','مدير كلمات مرور','متتبع عادات','متتبع مصاريف','طقس'],
      education:['بطاقات تعليمية','قاموس','اختبار','تعلم لغات','تمرين رياضيات','جدول دوري','خريطة عالم','إملاء','جغرافيا','طباعة'],
      games:['إكس أو','مطابقة ذاكرة','ثعبان','2048','سودوكو','ألغام','بونغ','كسر طوب','بحث كلمات','حبل المشنقة'],
      health:['عداد خطوات','تذكير شرب','معدل نبض','تأمل','متتبع نوم','تمارين','عداد سعرات','يوجا','متتبع دورة','حاسبة BMI'],
      travel:['خرائط','بوصلة متقدمة','مترجم','محول عملات','مخطط سفر','مقياس سرعة','مقياس ارتفاع','تذكير ركن','متتبع مشي','كشف كنوز'],
      smart_home:['منزل ذكي','مراقب نباتات','منظم حرارة','جرس باب','روبوت تنظيف','إضاءة','رشاش','باب جراج','مطعم حيوان','جودة هواء'],
      finance:['حاسبة إكرامية','متتبع أسهم','مخطط ميزانية','حاسبة قرض','فاتورة','عملات رقمية','ماسح إيصالات','تقسيم فاتورة','تبرعات','ضرائب']
    };
    const icons = {
      utility:['\u{1f4ca}','\u{1f4dd}','\u{1f4c4}','\u{1f526}','\u{1f9ed}','\u{23f1}','\u23f0','\u{1f4f2}','\u{1f4f1}','\u{1f4cf}'],
      social:['\u{1f4ac}','\u{1f4d7}','\u{1f4e7}','\u{1f4f1}','\u{1f5bc}','\u{1f4f0}','\u{1f4f1}','\u{1f4e8}','\u{1f4d6}','\u{1f3b5}'],
      media:['\u{1f3b5}','\u{1f3ac}','\u{1f4f7}','\u{1f5bc}','\u{1f3a4}','\u{1f5bc}','\u{1f4fb}','\u{1f3b5}','\u{1f3a4}','\u{1f3b5}'],
      productivity:['\u{1f4c5}','\u{1f4c1}','\u{1f4c4}','\u{1f4f0}','\u2601\ufe0f','\u{1f4dd}','\u{1f512}','\u{1f4cb}','\u{1f4b0}','\u{2600}\ufe0f'],
      education:['\u{1f4da}','\u{1f4d6}','\u2753','\u{1f310}','\u{1f521}','\u2697\ufe0f','\u{1f5fa}','\u{1f4da}','\u{1f5fa}','\u2328\ufe0f'],
      games:['\u{1f3ae}','\u{1f3b3}','\u{1f40d}','\u{1f522}','\u{1f4cf}','\u{1f4a3}','\u{1f3d3}','\u{1f3b1}','\u{1f50d}','\u{1f3ad}'],
      health:['\u{1f6b6}','\u{1f4a7}','\u2764\ufe0f','\u{1f54a}','\u{1f634}','\u{1f3cb}','\u{1f372}','\u{1f9d8}','\u{1f4ca}','\u{1f4ca}'],
      travel:['\u{1f5fa}','\u{1f9ed}','\u{1f310}','\u{1f4b1}','\u{1f3d6}','\u{1f3ce}','\u{1f4cf}','\u{1f17f}','\u{1f6b6}','\u{1f4ff}'],
      smart_home:['\u{1f3e0}','\u{1f331}','\u{1f321}','\u{1f514}','\u{1f916}','\u{1f4a1}','\u{1f4a7}','\u{1f3de}','\u{1f436}','\u{1f32c}'],
      finance:['\u{1f4b0}','\u{1f4c8}','\u{1f4ca}','\u{1f3e6}','\u{1f4e6}','\u{1f4b3}','\u{1f4f0}','\u{1f9fe}','\u{2764}\ufe0f','\u{1f4cb}']
    };
    const result = [];
    cats.forEach(cat => {
      const cn = cat.id;
      for (let i = 0; i < 10; i++) {
        const num = cat.range[0] + i;
        const ni = names[cn] ? names[cn][i] : 'App ' + num;
        const di = descs[cn] ? descs[cn][i] : 'تطبيق ' + ni;
        const ic = icons[cn] ? icons[cn][i] : '\u{1f4f1}';
        result.push({
          id: 'template_' + String(num).padStart(3, '0'),
          name: ni, name_ar: di,
          description: di, icon: ic,
          category: cn, category_name: cat.name, category_icon: cat.icon,
          package: 'app.bardom.' + ni.toLowerCase().replace(/[^a-z0-9]/g, ''),
          version: '1.0.0', min_sdk: 21, target_sdk: 34,
          features: _genFeatures(cn, i)
        });
      }
    });
    return result;
  }

  function _genFeatures(cat, idx) {
    const all = {
      utility:[['Display numeric keypad','عرض لوحة أرقام'],['Add two numbers','جمع رقمين'],['Subtract two numbers','طرح رقمين'],['Multiply two numbers','ضرب رقمين'],['Divide two numbers','قسمة رقمين'],['Clear display','مسح الشاشة'],['Show result','عرض النتيجة'],['Decimal point','نقطة عشرية'],['Percentage calculation','حساب نسبة مئوية'],['Delete last digit','حذف آخر رقم'],
      ['Create new note','إنشاء ملاحظة'],['Edit existing note','تعديل ملاحظة'],['Delete note','حذف ملاحظة'],['Search notes','بحث في الملاحظات'],['Pin important notes','تثبيت ملاحظات مهمة'],['Sort by date','ترتيب بالتاريخ'],['Category tags','تصنيف بالعلامات'],['Dark mode','وضع داكن'],['Export notes','تصدير الملاحظات'],['Word count','عدد الكلمات'],
      ['Add new task','إضافة مهمة'],['Mark task complete','تحديد مهمة مكتملة'],['Delete task','حذف مهمة'],['Filter by status','تصفية بالحالة'],['Set due date','تحديد تاريخ استحقاق'],['Priority levels','مستويات أولوية'],['Categories','تصنيفات'],['Search tasks','بحث في المهام'],['Sort tasks','ترتيب المهام'],['Statistics','إحصائيات'],
      ['Toggle flashlight','تشغيل/إيقاف الكشاف'],['Screen bright white','شاشة بيضاء ساطعة'],['SOS pattern','نمط SOS'],['Adjust brightness','تعديل السطوع'],['Strobe effect','تأثير وميض'],['Battery level','مستوى البطارية'],['Compass mode','وضع بوصلة'],['Color modes','أوضاع لونية']],
      social:[['Send text message','إرسال رسالة نصية'],['Receive messages','استقبال رسائل'],['Online status','حالة الاتصال'],['User profile','ملف المستخدم'],['Search users','بحث عن مستخدمين'],['Block user','حظر مستخدم'],['Media sharing','مشاركة وسائط'],['Group chat','دردشة جماعية'],['Notifications','إشعارات'],['Message history','سجل الرسائل']],
      media:[['Play music','تشغيل موسيقى'],['Pause/Resume','إيقاف/استمرار'],['Next track','المقطع التالي'],['Previous track','المقطع السابق'],['Volume control','التحكم بالصوت'],['Playlist management','إدارة قوائم التشغيل'],['Shuffle mode','وضع عشوائي'],['Repeat mode','وضع التكرار'],['Progress bar','شريط التقدم'],['Album art','غلاف الألبوم'],
      ['Open camera','فتح الكاميرا'],['Capture photo','التقاط صورة'],['Switch camera','تبديل الكاميرا'],['Flash toggle','تفعيل الفلاش'],['Zoom in/out','تكبير/تصغير'],['Timer capture','تصوير مؤقت'],['Filter effects','تأثيرات فلاتر'],['Save photo','حفظ الصورة'],['Gallery view','عرض المعرض'],['Share photo','مشاركة الصورة']],
      productivity:[['Monthly view','عرض شهري'],['Weekly view','عرض أسبوعي'],['Add event','إضافة حدث'],['Edit event','تعديل حدث'],['Delete event','حذف حدث'],['Reminder','تذكير'],['Search events','بحث في الأحداث'],['Day view','عرض يومي'],['Agenda view','عرض جدول'],['Export calendar','تصدير التقويم'],
      ['Browse files','تصفح الملفات'],['Create folder','إنشاء مجلد'],['Copy file','نسخ ملف'],['Move file','نقل ملف'],['Delete file','حذف ملف'],['Rename file','إعادة تسمية'],['Sort files','ترتيب الملفات'],['File info','معلومات الملف'],['Search files','بحث في الملفات'],['Storage info','معلومات التخزين']],
      education:[['Create flashcard','إنشاء بطاقة'],['Flip card','قلب البطاقة'],['Shuffle cards','خلط البطاقات'],['Categories','تصنيفات'],['Progress tracking','تتبع التقدم'],['Spaced repetition','تكرار متباعد'],['Import cards','استيراد بطاقات'],['Export cards','تصدير بطاقات'],['Statistics','إحصائيات'],['Dark mode','وضع داكن'],
      ['Search word','بحث عن كلمة'],['Word definition','تعريف الكلمة'],['Pronunciation','النطق'],['Examples','أمثلة'],['Favorites','المفضلة'],['History','السجل'],['Language selection','اختيار اللغة'],['Daily word','كلمة اليوم'],['Quiz mode','وضع اختبار'],['Offline mode','وضع عدم الاتصال']],
      games:[['3x3 grid','شبكة 3×3'],['Player vs AI','لاعب ضد ذكاء اصطناعي'],['Player vs Player','لاعب ضد لاعب'],['Win detection','كشف الفوز'],['Reset game','إعادة اللعبة'],['Score tracking','تتبع النقاط'],['Sound effects','مؤثرات صوتية'],['Animations','حركات'],['Theme selection','اختيار السمة'],['Difficulty levels','مستويات الصعوبة'],
      ['Move snake','تحريك الثعبان'],['Eat food','أكل الطعام'],['Grow longer','النمو'],['Avoid collision','تجنب التصادم'],['Score tracking','تتبع النقاط'],['Speed increase','زيادة السرعة'],['Pause/Resume','إيقاف/استمرار'],['Game over screen','شاشة نهاية اللعبة'],['High score','أعلى نقاط'],['Restart','إعادة البدء']],
      health:[['Count steps','عد الخطوات'],['Daily goal','هدف يومي'],['Distance tracker','متتبع المسافة'],['Calories burned','سعرات محروقة'],['Weekly chart','رسم أسبوعي'],['History','السجل'],['Achievements','إنجازات'],['Reminder','تذكير'],['Settings','الإعدادات'],['Export data','تصدير البيانات'],
      ['Set interval','تحديد فترة'],['Notifications','إشعارات'],['Track glasses','تتبع الأكواب'],['Daily goal','هدف يومي'],['Statistics','إحصائيات'],['Reminder','تذكير'],['History','السجل'],['Custom amount','كمية مخصصة'],['Progress bar','شريط التقدم'],['Streak tracking','تتبع المتابعة']],
      travel:[['Show map','عرض الخريطة'],['Current location','الموقع الحالي'],['Search place','بحث عن مكان'],['Directions','الاتجاهات'],['Save places','حفظ الأماكن'],['Offline maps','خرائط بدون إنترنت'],['Route planning','تخطيط المسار'],['Distance measure','قياس المسافة'],['Share location','مشاركة الموقع'],['Explore nearby','استكشاف قريب']],
      smart_home:[['Device list','قائمة الأجهزة'],['Toggle device','تشغيل/إيقاف جهاز'],['Schedule','جدولة'],['Automation','أتمتة'],['Rooms','الغرف'],['Scenes','المشاهد'],['Energy monitor','مراقب الطاقة'],['Notifications','إشعارات'],['Voice control','تحكم صوتي'],['Security mode','وضع الأمان']],
      finance:[['Bill amount','قيمة الفاتورة'],['Tip percentage','نسبة الإكرامية'],['Split bill','تقسيم الفاتورة'],['Round up','تقريب للأعلى'],['Currency display','عرض العملة'],['History','السجل'],['Quick percentages','نسب سريعة'],['Tax calculation','حساب الضريبة'],['Share result','مشاركة النتيجة'],['Settings','الإعدادات'],
      ['Add expense','إضافة مصروف'],['Category','تصنيف'],['Amount','المبلغ'],['Date','التاريخ'],['Monthly summary','ملخص شهري'],['Charts','رسوم بيانية'],['Budget limit','حد الميزانية'],['Remaining budget','الميزانية المتبقية'],['Export data','تصدير البيانات'],['Recurring expenses','مصاريف متكررة']]
    };
    const pool = all[cat] || all.utility;
    const start = (idx % Math.floor(pool.length / 10)) * 10;
    return pool.slice(start, start + 10).map(f => f[0]);
  }

  function _renderCards() {
    if (_filtered.length === 0) {
      return '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text3)">لا توجد قوالب مطابقة</div>';
    }
    return _filtered.map(t =>
      `<div class="template-card" onclick="_selectTemplate('${t.id}')">
        <div class="tc-icon">${t.icon || '\u{1f4f1}'}</div>
        <div class="tc-name">${t.name}</div>
        <div class="tc-desc">${t.description}</div>
        <div class="tc-cat">${t.category_icon || ''} ${t.category_name || ''}</div>
      </div>`
    ).join('');
  }

  window._setCat = function(cat) {
    _currentCat = cat;
    if (cat === 'all') {
      _filtered = _templates;
    } else {
      _filtered = _templates.filter(t => t.category === cat);
    }
    const search = document.getElementById('templateSearch');
    if (search && search.value) {
      const q = search.value.toLowerCase();
      _filtered = _filtered.filter(t => t.name.toLowerCase().includes(q) || t.description.includes(q));
    }
    document.getElementById('templatesGrid').innerHTML = _renderCards();
    // Re-render tabs
    const cats = BardomApp.config.get('categories', []);
    const tabsHtml = '<button class="btn ' + (cat==='all'?'btn-primary':'btn-ghost') + '" onclick="_setCat(\'all\')" style="font-size:12px;padding:6px 12px">الكل</button>' +
      cats.map(c => '<button class="btn ' + (cat===c.id?'btn-primary':'btn-ghost') + '" onclick="_setCat(\'' + c.id + '\')" style="font-size:12px;padding:6px 12px">' + c.icon + ' ' + c.name + '</button>').join('');
    document.getElementById('catTabs').innerHTML = tabsHtml;
  };

  window._filterTemplates = function() {
    const q = (document.getElementById('templateSearch')?.value || '').toLowerCase();
    if (!q) { _setCat(_currentCat); return; }
    _filtered = _templates.filter(t =>
      (t.category === _currentCat || _currentCat === 'all') &&
      (t.name.toLowerCase().includes(q) || t.description.includes(q))
    );
    document.getElementById('templatesGrid').innerHTML = _renderCards();
  };

  window._selectTemplate = function(id) {
    const t = _templates.find(x => x.id === id);
    if (!t) return;
    BardomApp.events.emit('template:selected', t);
    BardomApp.navigateTo('apk-builder');
  };

  // Expose for builder module
  window._getTemplateById = function(id) { return _templates.find(x => x.id === id); };
  window._getAllTemplates = function() { return _templates; };
})();