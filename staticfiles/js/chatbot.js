/**
 * AgroSathi AI farming chatbot
 */
(function () {
  const t = (k) => (window.AgroI18n && window.AgroI18n.t(k)) || k;

  const chatWindow = document.getElementById('chatWindow');
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('chatMessage');
  const sendBtn = document.getElementById('chatSendBtn');
  const imageInput = document.getElementById('chatImage');
  const imagePreview = document.getElementById('imagePreview');
  const typingEl = document.getElementById('typingIndicator');
  const askAgainBtn = document.getElementById('askAgainBtn');
  const voiceBtn = document.getElementById('voiceBtn');
  const speakLastBtn = document.getElementById('speakLastBtn');
  const clearChatBtn = document.getElementById('clearChatBtn');

  let lastBotText = '';

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>');
  }

  function scrollToBottom() {
    if (chatWindow) {
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }
  }

  function appendBubble(text, role, imageUrl) {
    if (!chatWindow) return;
    const row = document.createElement('div');
    row.className = `chat-row ${role === 'user' ? 'user-row' : 'bot-row'}`;

    const avatar = document.createElement('div');
    avatar.className = 'chat-avatar ' + (role === 'user' ? 'bg-success text-white' : 'bg-light border');
    avatar.innerHTML = role === 'user'
      ? '<i class="fas fa-user"></i>'
      : '<i class="fas fa-robot text-success"></i>';

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    bubble.innerHTML = escapeHtml(text);
    if (imageUrl) {
      bubble.innerHTML += `<br><img src="${imageUrl}" class="chat-image-preview" alt="">`;
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatWindow.appendChild(row);
    scrollToBottom();

    if (role === 'bot') lastBotText = text;
  }

  function showTyping(on) {
    if (!typingEl) return;
    typingEl.style.display = on ? 'block' : 'none';
    if (on) scrollToBottom();
  }

  function setLoading(on) {
    if (sendBtn) sendBtn.disabled = on;
    if (messageInput) messageInput.disabled = on;
    showTyping(on);
  }

  async function sendMessage(text, imageFile) {
    const msg = (text || messageInput?.value || '').trim();
    if (!msg && !imageFile) return;

    appendBubble(msg || t('image_question'), 'user', imageFile ? URL.createObjectURL(imageFile) : null);
    if (messageInput) messageInput.value = '';
    if (imageInput) imageInput.value = '';
    if (imagePreview) imagePreview.innerHTML = '';

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('message', msg);
      if (imageFile) formData.append('image', imageFile);

      let resp, data;
      if (window.AgroApi) {
        ({ resp, data } = await window.AgroApi.postForm('/api/chat/', formData));
      } else {
        resp = await fetch('/api/chat/', { method: 'POST', body: formData, credentials: 'same-origin' });
        data = await resp.json().catch(() => ({}));
      }

      if (!resp.ok) {
        if (resp.status === 401 || resp.status === 403) {
          window.location.href = '/login/?next=/chatbot/';
          return;
        }
        throw new Error(data.error || t('fetch_failed'));
      }

      let reply = data.reply || '';
      if (data.provider === 'fallback') {
        reply += '\n\n— Add GEMINI_API_KEY or OPENAI_API_KEY in .env for live AI responses.';
      }
      appendBubble(reply, 'bot');
    } catch (err) {
      appendBubble(t('fetch_failed') + ': ' + err.message, 'bot');
    } finally {
      setLoading(false);
    }
  }

  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const file = imageInput?.files?.[0] || null;
      sendMessage(null, file);
    });
  }

  if (messageInput) {
    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const file = imageInput?.files?.[0] || null;
        sendMessage(null, file);
      }
    });
  }

  document.querySelectorAll('.quick-chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      const prompt = btn.getAttribute('data-prompt');
      if (messageInput) messageInput.value = prompt;
      sendMessage(prompt, null);
    });
  });

  if (askAgainBtn) {
    askAgainBtn.addEventListener('click', () => {
      if (messageInput) {
        messageInput.focus();
        messageInput.placeholder = t('ask_again_placeholder');
      }
    });
  }

  if (imageInput && imagePreview) {
    imageInput.addEventListener('change', () => {
      const file = imageInput.files[0];
      if (!file) {
        imagePreview.innerHTML = '';
        return;
      }
      imagePreview.innerHTML = `<img src="${URL.createObjectURL(file)}" class="chat-image-preview" alt="">`;
    });
  }

  if (voiceBtn && (window.SpeechRecognition || window.webkitSpeechRecognition)) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.lang = document.documentElement.lang === 'hi' ? 'hi-IN'
      : document.documentElement.lang === 'mr' ? 'mr-IN'
      : document.documentElement.lang === 'te' ? 'te-IN' : 'en-IN';
    rec.interimResults = false;
    voiceBtn.addEventListener('click', () => {
      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (messageInput) messageInput.value = transcript;
      };
      rec.start();
    });
  } else if (voiceBtn) {
    voiceBtn.disabled = true;
    voiceBtn.title = 'Voice not supported in this browser';
  }

  if (speakLastBtn) {
    speakLastBtn.addEventListener('click', () => {
      if (window.AgroI18n && lastBotText) {
        AgroI18n.speak(lastBotText, AgroI18n.getLang());
      }
    });
  }

  if (clearChatBtn && chatWindow) {
    clearChatBtn.addEventListener('click', () => {
      const welcome = chatWindow.querySelector('.welcome-msg');
      chatWindow.innerHTML = '';
      if (welcome) chatWindow.appendChild(welcome);
      lastBotText = '';
    });
  }

  scrollToBottom();
})();
