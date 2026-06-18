/**
 * Farmer dashboard — weather widget, market preview, Chart.js activity chart.
 */
(function () {
  const root = document.querySelector('[data-default-city]');
  if (!root) return;

  const city = root.dataset.defaultCity || 'Pune';
  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1];

  function postJson(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrf ? { 'X-CSRFToken': csrf } : {}),
      },
      body: JSON.stringify(body),
      credentials: 'same-origin',
    }).then((r) => r.json().then((d) => ({ ok: r.ok, data: d })));
  }

  // Weather widget
  postJson('/api/weather/', { city, language_code: window.AGRO_LANG || 'en' })
    .then(({ ok, data }) => {
      const el = document.getElementById('weatherSummary');
      const card = document.getElementById('weatherWidget');
      if (card) card.classList.remove('widget-loading');
      if (!ok || data.error) {
        el.textContent = data.error || data.message || 'Weather unavailable (add OPENWEATHER_API_KEY).';
        return;
      }
      const cur = data.current || data;
      const temp = cur.temp ?? cur.temperature;
      const desc = cur.description || cur.weather?.[0]?.description || '';
      el.innerHTML = `<strong>${data.city || city}</strong>: ${temp}°C — ${desc}`;
    })
    .catch(() => {
      document.getElementById('weatherSummary').textContent = 'Could not load weather.';
    });

  // Market preview (GET also supported)
  const marketQs = new URLSearchParams({ crop: 'Wheat', state: 'Maharashtra', limit: '5' });
  fetch('/api/market-prices/?' + marketQs, { credentials: 'same-origin' })
    .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
    .then(({ ok, data }) => {
      const el = document.getElementById('marketPreview');
      const card = document.getElementById('marketWidget');
      if (card) card.classList.remove('widget-loading');
      if (!ok || !data.records?.length) {
        el.textContent = data.note || data.error || 'Market data unavailable.';
        return;
      }
      const srcNote = data.source && !String(data.source).includes('reference')
        ? '' : ' <span class="text-warning">(reference data — add AGMARKNET_API_KEY)</span>';
      el.innerHTML = srcNote + '<ul class="list-unstyled mb-0">' + data.records.slice(0, 5).map((r) =>
        `<li class="mb-1"><strong>${r.commodity || r.crop}</strong> @ ${r.market} — ₹${r.modal_price}/q</li>`
      ).join('') + '</ul>';
    })
    .catch(() => {
      document.getElementById('marketPreview').textContent = 'Could not load prices.';
    });

  // API integration status
  fetch('/api/status/', { credentials: 'same-origin' })
    .then((r) => r.json())
    .then((st) => {
      const el = document.getElementById('apiStatusList');
      if (!el) return;
      const badge = (ok, label) =>
        `<span class="badge ${ok ? 'bg-success' : 'bg-secondary'}">${label}: ${ok ? 'OK' : 'Not configured'}</span>`;
      el.innerHTML = [
        badge(st.openweather, 'Weather'),
        badge(st.agmarknet, 'Mandi'),
        badge(st.gemini || st.openai, 'AI Chat'),
        badge(st.gemini, 'Disease AI'),
      ].join('');
    })
    .catch(() => {
      const el = document.getElementById('apiStatusList');
      if (el) el.textContent = 'Could not load API status.';
    });

  // Activity chart
  const cfg = window.AGRO_DASHBOARD || { cropCount: 0, diseaseCount: 0 };
  const canvas = document.getElementById('activityChart');
  if (canvas && window.Chart) {
    new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Crop advisories', 'Disease reports'],
        datasets: [{
          data: [cfg.cropCount || 0, cfg.diseaseCount || 0],
          backgroundColor: ['#16a34a', '#dc2626'],
        }],
      },
      options: { responsive: true, plugins: { legend: { position: 'bottom' } } },
    });
  }
})();
