/**
 * Mandi market prices — Django proxy at /api/market-prices/
 */
(function () {
  const t = (k) => (window.AgroI18n && window.AgroI18n.t(k)) || k;
  let currentPage = 1;
  let lastFilters = {};
  let chartInstance = null;

  const els = {
    form: document.getElementById('marketSearchForm'),
    crop: document.getElementById('cropSearch'),
    state: document.getElementById('stateFilter'),
    district: document.getElementById('districtFilter'),
    market: document.getElementById('marketFilter'),
    searchBtn: document.getElementById('marketSearchBtn'),
    loading: document.getElementById('marketLoading'),
    error: document.getElementById('marketError'),
    results: document.getElementById('marketResults'),
    tbody: document.getElementById('marketTableBody'),
    source: document.getElementById('dataSource'),
    insights: document.getElementById('marketInsights'),
    pagination: document.getElementById('marketPagination'),
    loadMore: document.getElementById('loadMoreBtn'),
    exportBtn: document.getElementById('exportCsvBtn'),
    watchlistAdd: document.getElementById('addWatchlistBtn'),
    watchlistContainer: document.getElementById('watchlistChips'),
  };

  function labelClass(label) {
    const map = {
      'High Demand': 'label-high-demand',
      'Low Demand': 'label-low-demand',
      Stable: 'label-stable',
      'Good Selling Time': 'label-good-time',
    };
    return map[label] || 'label-stable';
  }

  function formatRs(n) {
    if (n === null || n === undefined) return '—';
    return '₹' + Number(n).toLocaleString('en-IN');
  }

  let statesPopulated = false;

  function populateStates(states) {
    if (!els.state || statesPopulated || !states?.length) return;
    states.forEach((s) => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      els.state.appendChild(opt);
    });
    statesPopulated = true;
  }

  function showLoading(on) {
    if (els.loading) {
      els.loading.style.display = on ? 'block' : 'none';
      els.loading.classList.toggle('active', on);
    }
    if (els.searchBtn) els.searchBtn.disabled = on;
  }

  function showError(msg) {
    if (!els.error) return;
    els.error.classList.remove('d-none');
    els.error.textContent = msg;
  }

  function clearError() {
    if (els.error) {
      els.error.classList.add('d-none');
      els.error.textContent = '';
    }
  }

  function getFilters() {
    return {
      crop: (els.crop?.value || '').trim(),
      state: (els.state?.value || '').trim(),
      district: (els.district?.value || '').trim(),
      market: (els.market?.value || '').trim(),
    };
  }

  function buildQuery(filters, page) {
    const p = new URLSearchParams();
    if (filters.crop) p.set('crop', filters.crop);
    if (filters.state) p.set('state', filters.state);
    if (filters.district) p.set('district', filters.district);
    if (filters.market) p.set('market', filters.market);
    p.set('page', String(page));
    p.set('limit', '20');
    return p.toString();
  }

  async function fetchPrices(page = 1, append = false) {
    clearError();
    showLoading(true);
    currentPage = page;
    lastFilters = getFilters();

    try {
      const qs = buildQuery(lastFilters, page);
      const resp = await fetch('/api/market-prices/?' + qs, {
        credentials: 'same-origin',
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        if (resp.status === 401 || resp.status === 403) {
          window.location.href = '/login/?next=/market/';
          return;
        }
        throw new Error(data.error || 'Request failed');
      }

      populateStates(data.states);
      renderResults(data, append);
      renderInsights(data.insights, data);
      renderWatchlist(data.watchlist || []);
      renderChart(data.records || []);
      updatePagination(data.pagination);
    } catch (err) {
      showError(err.message);
    } finally {
      showLoading(false);
    }
  }

  function demandBadge(label) {
    const cls = labelClass(label);
    return `<span class="badge rounded-pill ${cls}">${label || 'Stable'}</span>`;
  }

  function renderResults(data, append) {
    if (!els.results || !els.tbody) return;
    els.results.style.display = 'block';

    if (els.source) {
      const src = data.source || '—';
      let apiNote = '';
      if (!data.api_configured) {
        apiNote = ' <span class="text-warning">(add AGMARKNET_API_KEY at data.gov.in for live mandi data)</span>';
      } else if (src.includes('sample') || src.includes('reference')) {
        apiNote = ' <span class="text-warning">(add AGMARKNET_API_KEY in .env for live mandi data from data.gov.in)</span>';
      } else {
        apiNote = ' <span class="text-success">(live government data)</span>';
      }
      const updated = data.generated_at ? ` · Updated ${new Date(data.generated_at).toLocaleString()}` : '';
      els.source.innerHTML = `Source: <strong>${src}</strong>${apiNote}${updated}`;
    }

    if (!append) els.tbody.innerHTML = '';

    const records = data.records || [];
    if (!records.length && !append) {
      els.tbody.innerHTML =
        `<tr><td colspan="9" class="text-center text-muted py-4">${t('no_market_results')}</td></tr>`;
      return;
    }

    records.forEach((r) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="fw-semibold">${escapeHtml(r.crop)}</td>
        <td>${escapeHtml(r.market)}</td>
        <td>${escapeHtml(r.district)}</td>
        <td>${escapeHtml(r.state)}</td>
        <td>${formatRs(r.min_price)}</td>
        <td>${formatRs(r.max_price)}</td>
        <td class="fw-bold text-success">${formatRs(r.modal_price)}</td>
        <td>${escapeHtml(r.arrival_date || '—')}</td>
        <td>${demandBadge(r.demand_label)}</td>`;
      els.tbody.appendChild(tr);
    });
  }

  function renderInsights(insights, data) {
    if (!els.insights || !insights) return;

    const selling = insights.selling_label || '—';
    const best = insights.best_market
      ? `${insights.best_market} (${formatRs(insights.best_modal_price)}/qtl)`
      : '—';

    els.insights.innerHTML = `
      <div class="col-md-4">
        <div class="market-insight-card card border-0 shadow-sm p-3 h-100">
          <div class="text-muted small">${t('best_market')}</div>
          <div class="fw-bold fs-5 text-success">${escapeHtml(best)}</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="market-insight-card card border-0 shadow-sm p-3 h-100">
          <div class="text-muted small">${t('price_trend')}</div>
          <p class="mb-0 small">${escapeHtml(insights.price_trend || '')}</p>
        </div>
      </div>
      <div class="col-md-4">
        <div class="market-insight-card card border-0 shadow-sm p-3 h-100">
          <div class="text-muted small">${t('recommendation')}</div>
          <p class="mb-2 small">${escapeHtml(insights.recommendation || '')}</p>
          <span class="badge rounded-pill ${labelClass(selling)}">${escapeHtml(selling)}</span>
        </div>
      </div>`;
    els.insights.style.display = 'flex';
  }

  function renderChart(records) {
    const canvas = document.getElementById('priceChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const top = records
      .filter((r) => r.modal_price)
      .slice(0, 8);

    const labels = top.map((r) => (r.market || r.crop).slice(0, 18));
    const modals = top.map((r) => r.modal_price);

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Modal price (₹/quintal)',
            data: modals,
            backgroundColor: 'rgba(25, 135, 84, 0.65)',
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { callback: (v) => '₹' + v } },
        },
      },
    });
  }

  function updatePagination(pag) {
    if (!els.pagination || !pag) return;
    const { page, total, has_more } = pag;
    els.pagination.textContent = `Page ${page} · ${total} total records`;
    if (els.loadMore) {
      els.loadMore.style.display = has_more ? 'inline-block' : 'none';
    }
  }

  function renderWatchlist(items) {
    if (!els.watchlistContainer) return;
    els.watchlistContainer.innerHTML = '';
    if (!items.length) {
      els.watchlistContainer.innerHTML =
        '<span class="text-muted small">No favorite crops yet.</span>';
      return;
    }
    items.forEach((w) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'btn btn-sm btn-outline-success watchlist-chip me-1 mb-1';
      chip.textContent = w.state ? `${w.crop} (${w.state})` : w.crop;
      chip.title = 'Click to search · right-click to remove';
      chip.addEventListener('click', () => {
        if (els.crop) els.crop.value = w.crop;
        if (els.state && w.state) els.state.value = w.state;
        fetchPrices(1, false);
      });
      chip.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        removeWatchlist(w.crop, w.state || '');
      });
      els.watchlistContainer.appendChild(chip);
    });
  }

  async function addWatchlist() {
    const crop = (els.crop?.value || '').trim();
    if (!crop) {
      showError('Enter a crop name to add to watchlist.');
      return;
    }
    const body = {
      action: 'add',
      crop,
      state: (els.state?.value || '').trim(),
    };
    if (window.AgroApi) {
      await window.AgroApi.postJson('/api/market-watchlist/', body);
    } else {
      await fetch('/api/market-watchlist/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'same-origin',
      });
    }
    fetchPrices(currentPage, false);
  }

  async function removeWatchlist(crop, state) {
    const body = { action: 'remove', crop, state };
    if (window.AgroApi) {
      await window.AgroApi.postJson('/api/market-watchlist/', body);
    } else {
      await fetch('/api/market-watchlist/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'same-origin',
      });
    }
    fetchPrices(currentPage, false);
  }

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  if (els.searchBtn) {
    els.searchBtn.addEventListener('click', () => fetchPrices(1, false));
  }

  if (els.form) {
    els.form.addEventListener('submit', (e) => {
      e.preventDefault();
      fetchPrices(1, false);
    });
  }

  if (els.loadMore) {
    els.loadMore.addEventListener('click', () => fetchPrices(currentPage + 1, true));
  }

  if (els.exportBtn) {
    els.exportBtn.addEventListener('click', () => {
      const qs = buildQuery(lastFilters.crop ? lastFilters : getFilters(), 1);
      window.location.href = '/api/market-prices/export/?' + qs;
    });
  }

  if (els.watchlistAdd) {
    els.watchlistAdd.addEventListener('click', addWatchlist);
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (els.crop && !els.crop.value.trim()) {
      els.crop.value = 'Wheat';
    }
    if (els.state && !els.state.value) {
      const maharashtra = Array.from(els.state.options).find(
        (o) => o.value === 'Maharashtra'
      );
      if (maharashtra) els.state.value = 'Maharashtra';
    }
    fetchPrices(1, false);
  });
})();
