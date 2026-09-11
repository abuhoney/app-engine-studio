/**
 * الوحدة: مساعد الذكاء الاصطناعي
 */
(function() {
  let _messages = [];

  BardomApp.registerModule('ai-assistant', 'المساعد الذكي', '\u{1f916}', function render() {
    return `<div style="max-width:700px;display:flex;flex-direction:column;height:calc(100vh - 200px)">
      <div class="section-title">\u{1f916} مساعد الذكاء الاصطناعي <span class="st-count">${BardomApp.config.get('api.openrouter_model', 'kimi-k2')}</span></div>
      <div id="chatMessages" style="flex:1;overflow-y:auto;padding:8px 0;display:flex;flex-direction:column;gap:12px">
        <div class="chat-msg system">\u{1f4a1} اكتب وصف التطبيق الذي تريده وسأساعدك في بنائه. يمكنك أيضاً طلب شرح كود أو اقتراح تحسينات.</div>
        ${_messages.map(m => '<div class="chat-msg ' + m.role + '">' + _escHtml(m.content) + '</div>').join('')}
      </div>
      <div style="padding-top:12px;border-top:1px solid var(--border);display:flex;gap:8px">
        <textarea class="form-textarea" id="aiInput" rows="2" placeholder="اكتب رسالتك هنا..." style="min-height:60px;flex:1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();_sendAiMsg()}"></textarea>
        <button class="btn btn-primary" onclick="_sendAiMsg()" style="align-self:flex-end">\u{1f680}</button>
      </div>
    </div>`;
  }, function init() {
    BardomApp.events.on('ai:response', function(d) {
      _messages.push({ role: 'user', content: d.query });
      _messages.push({ role: 'assistant', content: d.response });
    });
  });

  window._sendAiMsg = async function() {
    const input = document.getElementById('aiInput');
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    _messages.push({ role: 'user', content: msg });
    const container = document.getElementById('chatMessages');
    if (container) {
      container.innerHTML += '<div class="chat-msg user">' + _escHtml(msg) + '</div>';
      container.innerHTML += '<div class="chat-msg assistant" id="aiTyping">\u23f3 جاري التفكير...</div>';
      container.scrollTop = container.scrollHeight;
    }
    try {
      const systemPrompt = 'أنت مساعد مولد تطبيقات Android لـ Bardom AI. أجب بالعربية. ساعد المستخدم في:
1. تصميم واجهات Android
2. كتابة كود Java/Kotlin
3. اقتراح مميزات للتطبيقات
4. حل مشاكل البرمجة
5. تحسين أداء التطبيقات
كن مختصراً ومفيداً.';
      const reply = await BardomApp.ai.chat(msg, systemPrompt);
      _messages.push({ role: 'assistant', content: reply });
      const typing = document.getElementById('aiTyping');
      if (typing) typing.outerHTML = '<div class="chat-msg assistant">' + _escHtml(reply) + '</div>';
    } catch (e) {
      const typing = document.getElementById('aiTyping');
      if (typing) typing.outerHTML = '<div class="chat-msg system" style="color:var(--red)">\u274c ' + _escHtml(e.message) + '</div>';
    }
    if (container) container.scrollTop = container.scrollHeight;
  };

  function _escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
  }
})();