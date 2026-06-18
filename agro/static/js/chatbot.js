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
      .replace(/>/g, '&gt;');
  }

  /** Basic markdown: bold, bullets, line breaks */
  function formatMarkdown(text) {
    let s = escapeHtml(text || '');
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    if (s.includes('<li>')) {
      s = s.replace(/(<li>[\s\S]*?)+/g, (m) => `<ul class="mb-0 ps-3">${m}</ul>`);
    }
    return s.replace(/\n/g, '<br>');
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
    bubble.innerHTML = role === 'bot' ? formatMarkdown(text) : escapeHtml(text).replace(/\n/g, '<br>');
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

  let lastBotAudio = null;
  let currentAudio = null;
  let isMuted = false;
  let isVoiceActive = true;

  function playAudioBase64(base64Data) {
    stopSpeaking();
    if (!isVoiceActive || isMuted) return;

    try {
      const audioUrl = 'data:audio/mp3;base64,' + base64Data;
      currentAudio = new Audio(audioUrl);
      currentAudio.muted = isMuted;
      currentAudio.play().catch((err) => {
        console.warn('Audio play failed:', err);
      });
    } catch (e) {
      console.error('Audio playback error:', e);
    }
  }

  function speakTextFallback(text) {
    stopSpeaking();
    if (!isVoiceActive || isMuted) return;

    if (window.AgroI18n && text) {
      const cleaned = text.replace(/\*\*/g, '').replace(/\*/g, '').split('—')[0].trim();
      AgroI18n.speak(cleaned, AgroI18n.getLang());
    }
  }

  function stopSpeaking() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }

  function toggleMute() {
    isMuted = !isMuted;
    const btn = document.getElementById('muteBtn');
    if (btn) {
      btn.setAttribute('data-muted', isMuted ? 'true' : 'false');
      if (isMuted) {
        btn.classList.add('btn-danger');
        btn.classList.remove('btn-outline-secondary');
        btn.innerHTML = '<i class="fas fa-volume-mute"></i>';
      } else {
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-outline-secondary');
        btn.innerHTML = '<i class="fas fa-volume-mute"></i>'; // keep fontawesome icon class name but style indicates mute/unmute
      }
    }
    if (currentAudio) {
      currentAudio.muted = isMuted;
    }
    if (isMuted && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }

  function toggleVoice() {
    isVoiceActive = !isVoiceActive;
    const btn = document.getElementById('voiceToggleBtn');
    if (btn) {
      btn.setAttribute('data-active', isVoiceActive ? 'true' : 'false');
      if (isVoiceActive) {
        btn.classList.add('btn-success');
        btn.classList.remove('btn-outline-secondary');
      } else {
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-secondary');
        stopSpeaking();
      }
    }
  }

  async function replayLastResponse() {
    if (!lastBotText) return;
    if (lastBotAudio) {
      playAudioBase64(lastBotAudio);
      return;
    }

    try {
      const activeLang = document.documentElement.lang || 'en';
      const resp = await fetch('/api/tts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
        },
        body: JSON.stringify({ text: lastBotText, language: activeLang })
      });
      const data = await resp.json();
      if (data.audio) {
        lastBotAudio = data.audio;
        playAudioBase64(lastBotAudio);
      } else {
        speakTextFallback(lastBotText);
      }
    } catch (e) {
      speakTextFallback(lastBotText);
    }
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
    stopSpeaking();

    try {
      const formData = new FormData();
      formData.append('message', msg);
      if (imageFile) formData.append('image', imageFile);

      let resp, data;
      const chatUrl = '/api/chatbot/';
      if (window.AgroApi) {
        ({ resp, data } = await window.AgroApi.postForm(chatUrl, formData));
      } else {
        resp = await fetch(chatUrl, { method: 'POST', body: formData, credentials: 'same-origin' });
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
      const providerLabel =
        data.provider === 'gemini'
          ? 'Gemini AI'
          : data.provider === 'openai'
            ? 'OpenAI'
            : data.provider === 'fallback'
              ? 'Assistant (offline)'
              : data.provider || '';
      if (providerLabel) {
        reply += `\n\n— *${providerLabel}*`;
      }
      if (data.provider === 'fallback') {
        reply =
          '**AI is not configured yet.**\n\n' +
          '1. Get a free key: https://aistudio.google.com/apikey\n' +
          '2. Add `GEMINI_API_KEY=your_key` to `.env` in the project folder\n' +
          '3. Restart the server (`start_agrosathi.bat`)\n\n' +
          'Until then, here is a quick tip:\n' + reply;
      }
      appendBubble(reply, 'bot');

      // Auto-play generated audio response
      lastBotAudio = data.audio || null;
      if (lastBotAudio) {
        playAudioBase64(lastBotAudio);
      } else {
        speakTextFallback(data.reply || '');
      }
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

  // Bind new voice controls
  const voiceToggleBtn = document.getElementById('voiceToggleBtn');
  if (voiceToggleBtn) {
    voiceToggleBtn.addEventListener('click', toggleVoice);
  }

  const muteBtn = document.getElementById('muteBtn');
  if (muteBtn) {
    muteBtn.addEventListener('click', toggleMute);
  }

  const stopSpeakingBtn = document.getElementById('stopSpeakingBtn');
  if (stopSpeakingBtn) {
    stopSpeakingBtn.addEventListener('click', stopSpeaking);
  }

  const replayBtn = document.getElementById('replayBtn');
  if (replayBtn) {
    replayBtn.addEventListener('click', replayLastResponse);
  }

  if (voiceBtn && (window.SpeechRecognition || window.webkitSpeechRecognition)) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    const activeLang = document.documentElement.lang || 'en';
    rec.lang = activeLang === 'kn' ? 'kn-IN'
      : activeLang === 'hi' ? 'hi-IN'
      : activeLang === 'mr' ? 'mr-IN'
      : activeLang === 'te' ? 'te-IN' : 'en-IN';
    rec.interimResults = false;
    
    voiceBtn.addEventListener('click', () => {
      voiceBtn.classList.add('btn-danger');
      voiceBtn.classList.remove('btn-outline-secondary');
      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        if (messageInput) messageInput.value = transcript;
      };
      rec.onend = () => {
        voiceBtn.classList.remove('btn-danger');
        voiceBtn.classList.add('btn-outline-secondary');
      };
      rec.start();
    });
  } else if (voiceBtn) {
    voiceBtn.disabled = true;
    voiceBtn.title = 'Voice not supported in this browser';
  }

  if (speakLastBtn) {
    speakLastBtn.addEventListener('click', () => {
      replayLastResponse();
    });
  }

  if (clearChatBtn && chatWindow) {
    clearChatBtn.addEventListener('click', () => {
      const welcome = chatWindow.querySelector('.welcome-msg');
      chatWindow.innerHTML = '';
      if (welcome) chatWindow.appendChild(welcome);
      lastBotText = '';
      lastBotAudio = null;
      stopSpeaking();
    });
  }

  scrollToBottom();
})();
