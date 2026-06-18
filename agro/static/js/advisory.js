/**
 * Smart crop advisory — /api/crop-advisory/
 */
(function () {
  const t = (k) => (window.AgroI18n && window.AgroI18n.t(k)) || k;
  const form = document.getElementById('crop-form');
  const resultDiv = document.getElementById('result');
  const status = document.getElementById('status');
  const submitBtn = document.getElementById('submit-btn');
  if (!form) return;

  document.getElementById('reset-btn')?.addEventListener('click', () => {
    form.reset();
    resultDiv?.classList.add('d-none');
    if (status) status.textContent = '';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (status) status.innerHTML = `<span class="spinner-border spinner-border-sm text-success"></span> ${t('loading_advisory')}`;
    if (submitBtn) submitBtn.disabled = true;
    const payload = {
      soil: document.getElementById('soil').value,
      season: document.getElementById('season').value,
      temp: parseFloat(document.getElementById('temp').value),
      ph: parseFloat(document.getElementById('ph').value),
      rainfall: parseFloat(document.getElementById('rainfall').value),
    };
    try {
      let resp, data;
      if (window.AgroApi) {
        ({ resp, data } = await window.AgroApi.postJson('/api/crop-advisory/', payload));
      } else {
        const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        resp = await fetch('/api/crop-advisory/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(csrf ? { 'X-CSRFToken': csrf } : {}),
          },
          body: JSON.stringify(payload),
          credentials: 'same-origin',
        });
        data = await resp.json();
      }
      if (!resp.ok) throw new Error(data.error || 'Error');
      if (status) status.textContent = '';
      const list = (data.predictions || [])
        .map(
          (p) =>
            `<li><strong>${p.crop}</strong> — ${(p.probability * 100).toFixed(1)}%</li>`
        )
        .join('');
      resultDiv.classList.remove('d-none');
      resultDiv.innerHTML = `<div class="result-panel"><h5 class="text-success">${t('recommended_crops')}</h5><ul>${list}</ul><p class="small text-muted">${data.note || ''}</p></div>`;
    } catch (err) {
      if (status) status.innerHTML = `<span class="text-danger">${err.message}</span>`;
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
})();
