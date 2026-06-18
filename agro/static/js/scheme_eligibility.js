/**
 * Scheme Eligibility Checker Frontend Module
 */
(function () {
  const form = document.getElementById('eligibilityForm');
  const resultsContainer = document.getElementById('eligibilityResultsContainer');
  const searchInput = document.getElementById('schemeSearchInput');
  const sortOrderSelect = document.getElementById('sortOrder');
  const favOnlyBtn = document.getElementById('showFavoritesOnlyBtn');
  const resetBtn = document.getElementById('resetEligibilityBtn');

  let activeSchemes = []; // Stores currently loaded schemes list
  let favoritesOnly = false;

  const t = (k) => (window.AgroI18n && window.AgroI18n.t(k)) || k;

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // Render list of matching schemes based on current search & sort state
  function renderSchemes() {
    let list = [...activeSchemes];

    // 1. Filter by favorites
    if (favoritesOnly) {
      list = list.filter(s => s.is_favorite);
    }

    // 2. Filter by search query
    const q = searchInput.value.trim().toLowerCase();
    if (q) {
      list = list.filter(s => 
        s.title.toLowerCase().includes(q) || 
        (s.description || '').toLowerCase().includes(q) ||
        (s.short_description || '').toLowerCase().includes(q) ||
        (s.benefits || '').toLowerCase().includes(q) ||
        (s.eligibility || '').toLowerCase().includes(q)
      );
    }

    // 3. Sort list
    const sort = sortOrderSelect.value;
    if (sort === 'score_desc') {
      list.sort((a, b) => b.eligibility_score - a.eligibility_score);
    } else if (sort === 'score_asc') {
      list.sort((a, b) => a.eligibility_score - b.eligibility_score);
    } else if (sort === 'title_asc') {
      list.sort((a, b) => a.title.localeCompare(b.title));
    }

    if (!list.length) {
      resultsContainer.innerHTML = `
        <div class="alert alert-info text-center py-4">
          <i class="fas fa-info-circle fa-2x mb-2"></i>
          <div>${t('no_schemes') || 'No matching schemes found.'}</div>
        </div>`;
      return;
    }

    resultsContainer.innerHTML = list.map(s => {
      const scoreColor = s.eligibility_score >= 80 ? 'bg-success' : s.eligibility_score >= 50 ? 'bg-warning text-dark' : 'bg-danger';
      const favClass = s.is_favorite ? 'fav-active' : 'fav-inactive';
      const favIcon = s.is_favorite ? 'fas fa-star' : 'far fa-star';

      return `
        <div class="card mb-3 border-start border-success border-4 scheme-card-item" data-id="${s.scheme_id}">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
              <div>
                <h5 class="card-title text-success mb-1 d-inline-block me-2">${escapeHtml(s.title)}</h5>
                <span class="badge ${scoreColor} eligibility-score-badge">${s.eligibility_score}% Match</span>
              </div>
              <div class="d-flex align-items-center gap-2">
                <button type="button" class="fav-btn ${favClass}" title="Toggle Favorite" onclick="window.toggleSchemeFavorite('${s.scheme_id}')">
                  <i class="${favIcon}"></i>
                </button>
                ${s.apply_url ? `<a href="${escapeHtml(s.apply_url)}" target="_blank" rel="noopener" class="btn btn-outline-success btn-sm">${t('official_portal') || 'Apply'}</a>` : ''}
              </div>
            </div>
            
            <p class="text-muted small mb-2">${escapeHtml(s.short_description || '')}</p>
            <p class="mb-3">${escapeHtml(s.description || '')}</p>
            
            <div class="border-top pt-2">
              <p class="small mb-1"><strong>${t('eligibility') || 'Eligibility Conditions'}:</strong> ${escapeHtml(s.eligibility || '—')}</p>
              <p class="small mb-1"><strong>${t('benefits') || 'Benefits'}:</strong> ${escapeHtml(s.benefits || '—')}</p>
              
              ${s.application_steps && s.application_steps.length ? `
                <div class="mt-2">
                  <strong class="small d-block mb-1">Application Steps:</strong>
                  <ol class="small mb-0 ps-3">
                    ${s.application_steps.map(step => `<li>${escapeHtml(step)}</li>`).join('')}
                  </ol>
                </div>
              ` : ''}
            </div>

            <div class="mt-3">
              <span class="badge bg-light text-dark border me-1">${escapeHtml(s.category || 'general')}</span>
              <span class="badge bg-secondary">${escapeHtml((s.states || ['All']).join(', '))}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // Favorite toggle API handler
  window.toggleSchemeFavorite = async function (schemeId) {
    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      const response = await fetch('/api/schemes/favorite/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ scheme_id: schemeId })
      });
      const data = await response.json();
      if (response.ok) {
        // Update local schemes favorite flag
        activeSchemes = activeSchemes.map(s => {
          if (s.scheme_id === schemeId) {
            return { ...s, is_favorite: data.is_favorite };
          }
          return s;
        });
        renderSchemes();
      }
    } catch (err) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  // Submit form handler
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const state = document.getElementById('state').value;
      const farmer_category = document.getElementById('farmer_category').value;
      const land_holding_size = document.getElementById('land_holding_size').value;
      const crop_type = document.getElementById('crop_type').value;
      const irrigation_availability = document.getElementById('irrigation_availability').value;

      resultsContainer.innerHTML = `<div class="text-center py-5 text-success"><span class="spinner-border text-success"></span><p class="mt-2">Checking match results...</p></div>`;

      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const response = await fetch('/api/schemes/eligibility/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            state,
            category: farmer_category,
            land_holding_size,
            crop_type,
            irrigation_availability
          })
        });

        const data = await response.json();
        if (response.ok) {
          activeSchemes = data.schemes || [];
          renderSchemes();
        } else {
          resultsContainer.innerHTML = `<div class="alert alert-danger">${data.error || 'Failed to match schemes'}</div>`;
        }
      } catch (err) {
        console.error(err);
        resultsContainer.innerHTML = `<div class="alert alert-danger">An error occurred during evaluation.</div>`;
      }
    });
  }

  // Real-time filters and search event listeners
  if (searchInput) {
    searchInput.addEventListener('input', renderSchemes);
  }
  if (sortOrderSelect) {
    sortOrderSelect.addEventListener('change', renderSchemes);
  }
  if (favOnlyBtn) {
    favOnlyBtn.addEventListener('click', () => {
      favoritesOnly = !favoritesOnly;
      favOnlyBtn.setAttribute('data-favorites', favoritesOnly ? 'true' : 'false');
      if (favoritesOnly) {
        favOnlyBtn.classList.add('btn-warning', 'text-white');
        favOnlyBtn.classList.remove('btn-outline-warning');
      } else {
        favOnlyBtn.classList.remove('btn-warning', 'text-white');
        favOnlyBtn.classList.add('btn-outline-warning');
      }
      renderSchemes();
    });
  }

  // Reset button
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      form.reset();
      activeSchemes = [];
      resultsContainer.innerHTML = `
        <div class="text-center py-5 text-muted">
          <i class="fas fa-landmark fa-3x mb-3 text-success-subtle"></i>
          <h6>${t('find_eligible_schemes') || 'Find Eligible Schemes'}</h6>
          <p class="small">${t('check_instructions') || "Select your profile parameters and click 'Check Eligibility' to view customized schemes matched for your farm."}</p>
        </div>`;
    });
  }
})();
