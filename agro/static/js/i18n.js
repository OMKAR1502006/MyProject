/**
 * Client-side translations for dynamic UI (weather, market, alerts).
 * Loaded from window.AGRO_I18N / window.AGRO_LANG (set in base.html).
 */
(function (global) {
  function getLang() {
    return (global.AGRO_LANG || document.documentElement.lang || 'en').split('-')[0];
  }

  function t(key) {
    const lang = getLang();
    const dict = global.AGRO_I18N || {};
    if (dict[lang] && dict[lang][key]) return dict[lang][key];
    if (dict.en && dict.en[key]) return dict.en[key];
    return key;
  }

  /** Browser speech synthesis for accessibility (optional). */
  function speak(text, lang) {
    if (!global.speechSynthesis || !text) return;
    const utter = new SpeechSynthesisUtterance(text);
    const map = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN', te: 'te-IN', kn: 'kn-IN' };
    utter.lang = map[lang || getLang()] || 'en-IN';
    utter.rate = 0.9;
    global.speechSynthesis.cancel();
    global.speechSynthesis.speak(utter);
  }

  /** Auto-detect browser language on first visit (optional, respects session). */
  function detectBrowserLanguage() {
    const nav = (navigator.language || 'en').split('-')[0];
    const supported = ['en', 'hi', 'mr', 'te', 'kn'];
    return supported.includes(nav) ? nav : 'en';
  }

  global.AgroI18n = { t, speak, detectBrowserLanguage, getLang };
})(window);
