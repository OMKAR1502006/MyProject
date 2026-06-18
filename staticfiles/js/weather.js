/**
 * AgroSathi weather page — Django /api/weather/ proxy.
 */
(function () {
  const t = (k) => (window.AgroI18n && window.AgroI18n.t(k)) || k;
  const root = document.querySelector('[data-default-city]');
  const defaultCity = root?.dataset.defaultCity || '';

  const els = {
    cityInput: document.getElementById('cityInput'),
    getWeatherBtn: document.getElementById('getWeatherBtn'),
    geoBtn: document.getElementById('geoBtn'),
    loading: document.getElementById('weatherLoading'),
    results: document.getElementById('weatherResults'),
    alerts: document.getElementById('weatherAlerts'),
    error: document.getElementById('weatherError'),
    apiHint: document.getElementById('weatherApiHint'),
    cityName: document.getElementById('cityName'),
    weatherIcon: document.getElementById('weatherIcon'),
    currentTemp: document.getElementById('currentTemp'),
    currentCond: document.getElementById('currentCond'),
    humidity: document.getElementById('humidity'),
    rainfall: document.getElementById('rainfall'),
    windSpeed: document.getElementById('windSpeed'),
    feelsLike: document.getElementById('feelsLike'),
    forecastGrid: document.getElementById('forecastGrid'),
    suggestionsList: document.getElementById('suggestionsList'),
    alertCount: document.getElementById('alertCount'),
  };

  function showLoading(on) {
    if (els.loading) els.loading.classList.toggle('active', on);
    if (els.getWeatherBtn) els.getWeatherBtn.disabled = on;
    if (els.geoBtn) els.geoBtn.disabled = on;
  }

  function showResults(on) {
    if (!els.results) return;
    els.results.classList.toggle('d-none', !on);
    if (on && els.loading) els.loading.classList.remove('active');
  }

  function showError(msg, isConfig) {
    if (!els.error) return;
    els.error.classList.remove('d-none');
    els.error.innerHTML = msg;
    if (els.apiHint && isConfig) {
      els.apiHint.classList.remove('d-none');
    }
  }

  function clearError() {
    if (els.error) {
      els.error.classList.add('d-none');
      els.error.textContent = '';
    }
    if (els.apiHint) els.apiHint.classList.add('d-none');
  }

  async function fetchWeather(payload) {
    clearError();
    showLoading(true);

    try {
      const api = window.AgroApi;
      const body = {
        ...payload,
        language_code: window.AGRO_LANG || 'en',
      };
      const { resp, data } = api
        ? await api.postJson('/api/weather/', body)
        : await (async () => {
            const r = await fetch('/api/weather/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(body),
              credentials: 'same-origin',
            });
            return { resp: r, data: await r.json().catch(() => ({})) };
          })();

      if (!resp.ok) {
        if (resp.status === 401 || resp.status === 403) {
          window.location.href = '/login/?next=/weather/';
          return;
        }
        const configErr = resp.status === 500 && (data.error || '').includes('API key');
        showResults(false);
        showError(
          data.error || t('fetch_failed') + ` (${resp.status})`,
          configErr
        );
        return;
      }

      clearError();
      renderWeather(data);
      showResults(true);
    } catch (err) {
      showResults(false);
      showError(t('fetch_failed') + ': ' + err.message);
    } finally {
      showLoading(false);
    }
  }

  function renderWeather(data) {
    if (!els.results) return;

    const cur = data.current || {};
    if (els.cityName) els.cityName.textContent = data.city || 'Your location';
    if (els.weatherIcon) {
      els.weatherIcon.src = cur.icon_url || '';
      els.weatherIcon.alt = cur.weather || 'Weather';
      els.weatherIcon.onerror = () => { els.weatherIcon.style.display = 'none'; };
      els.weatherIcon.style.display = cur.icon_url ? 'block' : 'none';
    }
    if (els.currentTemp) {
      els.currentTemp.textContent =
        cur.temp != null ? `${cur.temp}°C` : '—';
    }
    if (els.currentCond) els.currentCond.textContent = cur.weather || cur.condition || '—';
    if (els.humidity) {
      els.humidity.textContent = cur.humidity != null ? `${cur.humidity}%` : '—';
    }
    if (els.rainfall) {
      els.rainfall.textContent =
        cur.rainfall_mm != null ? `${cur.rainfall_mm} mm` : '0 mm';
    }
    if (els.windSpeed) {
      els.windSpeed.textContent =
        cur.wind_speed != null ? `${cur.wind_speed} m/s` : '—';
    }
    if (els.feelsLike) {
      els.feelsLike.textContent =
        cur.feels_like != null ? `${cur.feels_like}°C` : '—';
    }

    const alerts = data.alerts || [];
    if (els.alertCount) els.alertCount.textContent = alerts.length;
    renderAlerts(alerts);
    renderForecast(data.forecast || []);
    renderSuggestions(data.farming_suggestions || []);

    const footer = document.getElementById('weatherSourceNote');
    if (footer) {
      const src = data.source || '';
      footer.textContent = data.api_note || (
        src === 'openweather'
          ? 'Data: OpenWeatherMap'
          : src === 'open-meteo'
            ? 'Live data: Open-Meteo (free). Optional: add OPENWEATHER_API_KEY in .env'
            : ''
      );
    }
  }

  function renderAlerts(alerts) {
    if (!els.alerts) return;
    els.alerts.innerHTML = '';
    if (!alerts.length) {
      els.alerts.innerHTML =
        `<div class="alert alert-success mb-0"><i class="fas fa-check-circle me-2"></i>${t('no_alerts')}</div>`;
      return;
    }
    alerts.forEach((a) => {
      els.alerts.insertAdjacentHTML(
        'beforeend',
        `<div class="alert alert-${a.type || 'info'} mb-2"><strong>${a.title}:</strong> ${a.msg}</div>`
      );
    });
  }

  function renderForecast(days) {
    if (!els.forecastGrid) return;
    els.forecastGrid.innerHTML = '';
    if (!days.length) {
      els.forecastGrid.innerHTML = '<div class="col-12 text-muted text-center">Forecast unavailable</div>';
      return;
    }
    days.forEach((d) => {
      const date = new Date(d.date + 'T12:00:00').toLocaleDateString(undefined, {
        weekday: 'short', month: 'short', day: 'numeric',
      });
      const pop = ((d.rain_probability || 0) * 100).toFixed(0);
      els.forecastGrid.insertAdjacentHTML(
        'beforeend',
        `<div class="col-6 col-md-4 col-lg">
          <div class="forecast-day-card h-100 text-center p-2">
            <div class="fw-semibold small text-muted">${date}</div>
            ${d.icon_url ? `<img src="${d.icon_url}" alt="" width="48" height="48" class="my-2">` : ''}
            <div class="fw-bold">${d.temp_max_c ?? '—'}° / ${d.temp_min_c ?? '—'}°</div>
            <div class="small text-muted">${d.summary || d.weather || '—'}</div>
            <div class="small mt-1 text-primary">Rain ${pop}% · ${d.precip_mm ?? 0} mm</div>
          </div>
        </div>`
      );
    });
  }

  function renderSuggestions(tips) {
    if (!els.suggestionsList) return;
    els.suggestionsList.innerHTML = '';
    if (!tips.length) {
      els.suggestionsList.innerHTML = '<li class="text-muted">No suggestions available.</li>';
      return;
    }
    tips.forEach((tip) => {
      els.suggestionsList.insertAdjacentHTML(
        'beforeend',
        `<li class="suggestion-item"><i class="fas fa-leaf text-success me-2"></i>${tip}</li>`
      );
    });
  }

  function tryDefaultCity() {
    const city = (els.cityInput?.value || defaultCity || 'Pune').trim();
    if (city) {
      if (els.cityInput) els.cityInput.value = city;
      fetchWeather({ city });
    } else {
      showLoading(false);
      showError(t('geo_denied'));
    }
  }

  if (els.getWeatherBtn) {
    els.getWeatherBtn.addEventListener('click', () => {
      const city = (els.cityInput?.value || '').trim();
      if (!city) {
        showError('Please enter a city name.');
        return;
      }
      fetchWeather({ city });
    });
  }

  if (els.geoBtn) {
    els.geoBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        tryDefaultCity();
        return;
      }
      showLoading(true);
      navigator.geolocation.getCurrentPosition(
        (pos) => fetchWeather({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => tryDefaultCity(),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 300000 }
      );
    });
  }

  let initialLoadDone = false;

  function loadInitialWeather() {
    if (initialLoadDone) return;
    initialLoadDone = true;
    if (!navigator.geolocation) {
      tryDefaultCity();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => fetchWeather({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => tryDefaultCity(),
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 600000 }
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadInitialWeather);
  } else {
    loadInitialWeather();
  }
})();
