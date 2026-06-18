/**
 * Soil analysis page — /api/soil-analysis/
 */
(function () {
  const t = (k) => (window.AgroI18n && window.AgroI18n.t(k)) || k;
  const btn = document.getElementById('analyzeBtn');
  const results = document.getElementById('results');
  const status = document.getElementById('soilStatus');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    if (status) {
      status.innerHTML = `<span class="spinner-border spinner-border-sm text-success"></span> ${t('analyzing_soil')}`;
    }
    btn.disabled = true;
    const payload = {
      N: parseFloat(document.getElementById('n').value),
      P: parseFloat(document.getElementById('p').value),
      K: parseFloat(document.getElementById('k').value),
      ph: parseFloat(document.getElementById('ph').value),
      moisture: parseFloat(document.getElementById('moisture')?.value || 0),
      area_ha: parseFloat(document.getElementById('area')?.value || 1),
      units: document.getElementById('units')?.value || 'ppm',
      soil_type: document.getElementById('soilType')?.value || 'loamy',
      crop_type: document.getElementById('cropType')?.value || 'wheat',
    };
    try {
      let resp, data;
      if (window.AgroApi) {
        ({ resp, data } = await window.AgroApi.postJson('/api/soil-analysis/', payload));
      } else {
        const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        resp = await fetch('/api/soil-analysis/', {
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
      if (!resp.ok) throw new Error(data.error || resp.status);
      document.getElementById('resClass').textContent = data.predicted_class || '—';

      const health = document.getElementById('healthCard');
      if (health && data.soil_health) {
        const score = data.soil_health.score ?? 0;
        const label = data.soil_health.label || '';
        const alertClass =
          score >= 75 ? 'alert-success' : score >= 50 ? 'alert-warning' : 'alert-danger';
        health.className = `alert ${alertClass} border mb-3`;
        health.innerHTML = `<strong>Soil health: ${label} (${score}%)</strong><br>${data.soil_health.summary || ''}`;
      }

      const opt = document.getElementById('resOptimal');
      if (opt && data.optimal_npk) {
        const o = data.optimal_npk;
        opt.textContent = `Target NPK for ${data.crop_type || 'crop'} (${data.soil_type || 'soil'}): N ${o.N}, P ${o.P}, K ${o.K}`;
      }

      const probs = document.getElementById('resProbs');
      probs.innerHTML = '';
      for (const [k, v] of Object.entries(data.probabilities || {})) {
        const li = document.createElement('li');
        const pct = Number(v) <= 1 ? (v * 100).toFixed(1) : v;
        li.textContent = `${k}: ${pct}%`;
        probs.appendChild(li);
      }
      const sug = document.getElementById('resSuggestions');
      sug.innerHTML = '';
      (data.suggestions || []).forEach((s) => {
        const li = document.createElement('li');
        const dose = s.suggest_apply_kg_per_ha != null ? ` @ ${s.suggest_apply_kg_per_ha} kg/ha` : '';
        li.textContent = `${s.nutrient}${dose}: ${s.note || ''}`;
        sug.appendChild(li);
      });
      document.getElementById('resPhAdvice').textContent =
        `${data.ph_advice?.status || ''} ${data.ph_advice?.advice || ''}`;
      if (results) results.style.display = 'block';
      if (status) status.textContent = '';
    } catch (e) {
      if (status) status.textContent = t('analysis_failed') + ': ' + e.message;
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById('resetBtn')?.addEventListener('click', () => {
    if (results) results.style.display = 'none';
    if (status) status.textContent = '';
  });
})();
