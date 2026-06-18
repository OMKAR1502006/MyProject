/**
 * Landing page — live previews, counters, scroll animations
 */
(function () {
  const counters = document.querySelectorAll('[data-counter]');
  const fadeEls = document.querySelectorAll('.fade-in');

  function animateCounter(el) {
    const target = parseInt(el.dataset.counter, 10) || 0;
    const suffix = el.dataset.suffix || '';
    const duration = 1500;
    const start = performance.now();
    function step(now) {
      const p = Math.min(1, (now - start) / duration);
      const val = Math.floor(target * (1 - Math.pow(1 - p, 3)));
      el.textContent = val.toLocaleString('en-IN') + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('visible');
        if (entry.target.dataset.counter) animateCounter(entry.target);
        obs.unobserve(entry.target);
      });
    },
    { threshold: 0.15 }
  );

  fadeEls.forEach((el) => obs.observe(el));
  counters.forEach((el) => {
    if (!el.closest('.fade-in')) obs.observe(el);
  });

  async function loadPreviews() {
    try {
      const resp = await fetch('/api/public/preview/', { credentials: 'same-origin' });
      const data = await resp.json();
      if (!resp.ok) return;

      const weatherEl = document.getElementById('homeWeatherPreview');
      if (weatherEl && data.weather) {
        const w = data.weather;
        const cur = w.current || w;
        const temp = cur.temp ?? cur.temperature ?? '—';
        const desc = cur.description || '';
        weatherEl.innerHTML = `
          <div class="d-flex align-items-center gap-3">
            <i class="fas fa-cloud-sun fa-3x text-primary"></i>
            <div>
              <div class="fw-bold fs-4">${w.city || 'Pune'}, ${temp}°C</div>
              <div class="text-muted">${desc}</div>
              <small class="text-muted">${w.source || 'Open-Meteo'} · Live</small>
            </div>
          </div>`;
      }

      const marketEl = document.getElementById('homeMarketPreview');
      if (marketEl && data.market?.error) {
        marketEl.innerHTML = `<p class="small text-warning mb-0">${data.market.error}</p>
          <a href="https://data.gov.in/" target="_blank" rel="noopener" class="small">Get free API key</a>`;
      } else if (marketEl && data.market?.records?.length) {
        const src = data.market.source || '';
        const live = src.includes('data.gov') || src.includes('cache');
        marketEl.innerHTML = `
          <p class="small text-muted mb-2">${live ? 'Live mandi data' : 'Sample rates'} · ${src}</p>
          <ul class="list-unstyled mb-0">
            ${data.market.records.slice(0, 4).map((r) =>
              `<li class="mb-2"><strong>${r.crop}</strong> @ ${r.market} — <span class="text-success">₹${r.modal_price}/q</span></li>`
            ).join('')}
          </ul>`;
      }

      const diseaseEl = document.getElementById('homeDiseasePreview');
      if (diseaseEl) {
        diseaseEl.innerHTML = `
          <ul class="list-unstyled mb-0">
            <li class="mb-2"><i class="fas fa-check text-success me-2"></i>Upload leaf photo</li>
            <li class="mb-2"><i class="fas fa-check text-success me-2"></i>Gemini Vision + TensorFlow</li>
            <li><i class="fas fa-check text-success me-2"></i>Treatment recommendations</li>
          </ul>`;
      }
    } catch {
      document.querySelectorAll('.loading-pulse').forEach((el) => {
        el.textContent = 'Sign in to see live data';
      });
    }
  }

  document.addEventListener('DOMContentLoaded', loadPreviews);
})();
