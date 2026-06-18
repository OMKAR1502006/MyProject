/**
 * Shared API helpers — CSRF token for Django POST requests.
 */
window.AgroApi = {
  getCsrfToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input && input.value) return input.value;
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  },

  async postJson(url, body) {
    const headers = { 'Content-Type': 'application/json' };
    const csrf = this.getCsrfToken();
    if (csrf) headers['X-CSRFToken'] = csrf;
    const resp = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      credentials: 'same-origin',
    });
    const data = await resp.json().catch(() => ({}));
    return { resp, data };
  },

  async postForm(url, formData) {
    const csrf = this.getCsrfToken();
    const headers = {};
    if (csrf) {
      formData.append('csrfmiddlewaretoken', csrf);
      headers['X-CSRFToken'] = csrf;
    }
    const resp = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
      credentials: 'same-origin',
    });
    const data = await resp.json().catch(() => ({}));
    return { resp, data };
  },
};
