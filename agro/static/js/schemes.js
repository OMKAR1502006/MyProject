/**
 * Government schemes page — /api/schemes/
 */
(function () {
  const t = (k) => (window.AgroI18n && window.AgroI18n.t(k)) || k;
  const root = document.getElementById('schemesList');
  if (!root) return;

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  async function loadSchemes() {
    const params = new URLSearchParams();
    const st = document.getElementById('filterState')?.value.trim();
    const cat = document.getElementById('filterCategory')?.value;
    const q = document.getElementById('filterQ')?.value.trim();
    if (st) params.append('state', st);
    if (cat) params.append('category', cat);
    if (q) params.append('q', q);
    root.innerHTML = `<div class="text-muted py-3"><span class="spinner-border spinner-border-sm text-success"></span> ${t('loading_schemes')}</div>`;
    try {
      const resp = await fetch('/api/schemes/?' + params.toString(), { credentials: 'same-origin' });
      if (resp.status === 401 || resp.status === 403) {
        window.location.href = '/login/?next=/schemes/';
        return;
      }
      const data = await resp.json();
      if (!data.schemes?.length) {
        root.innerHTML = `<div class="alert alert-info">${t('no_schemes')}</div>`;
        return;
      }
      root.innerHTML = data.schemes
        .map(
          (s) => `
        <div class="card mb-3 border-start border-success border-4 scheme-card-item">
          <div class="card-body">
            <div class="d-flex justify-content-between flex-wrap gap-2">
              <div>
                <h5 class="card-title text-success mb-1">${escapeHtml(s.title)}</h5>
                <p class="text-muted small mb-2">${escapeHtml(s.short || '')}</p>
              </div>
              ${s.apply_url ? `<a href="${escapeHtml(s.apply_url)}" target="_blank" rel="noopener" class="btn btn-outline-success btn-sm">${t('official_portal')}</a>` : ''}
            </div>
            <p class="mb-2">${escapeHtml(s.description || '')}</p>
            <p class="small mb-1"><strong>${t('eligibility') || 'Eligibility'}:</strong> ${escapeHtml(s.eligibility || '—')}</p>
            <p class="small mb-1"><strong>${t('benefits') || 'Benefits'}:</strong> ${escapeHtml(s.benefits || '—')}</p>
            <span class="badge bg-light text-dark me-1">${escapeHtml(s.category || 'general')}</span>
            <span class="badge bg-secondary">${escapeHtml((s.states || ['All']).join(', '))}</span>
          </div>
        </div>`
        )
        .join('');
    } catch (e) {
      root.innerHTML = `<div class="alert alert-danger">${t('failed_schemes')}</div>`;
    }
  }

  document.getElementById('btnFilter')?.addEventListener('click', loadSchemes);
  document.getElementById('filterQ')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      loadSchemes();
    }
  });
  document.getElementById('filterCategory')?.addEventListener('change', loadSchemes);
  loadSchemes();
})();
