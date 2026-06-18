/**
 * Yield & Profit Prediction Frontend Module
 */
(function () {
  const form = document.getElementById('predictionForm');
  const welcomePanel = document.getElementById('welcomeResultPanel');
  const resultPanel = document.getElementById('actualResultPanel');
  
  const resYield = document.getElementById('resYield');
  const resRevenue = document.getElementById('resRevenue');
  const resExpenses = document.getElementById('resExpenses');
  const resProfit = document.getElementById('resProfit');
  const resMargin = document.getElementById('resMargin');
  const recommendationsList = document.getElementById('recommendationsList');
  
  const fetchWeatherBtn = document.getElementById('fetchWeatherBtn');
  const resetBtn = document.getElementById('resetPredictionBtn');

  // Chart instances
  let yieldChartInst = null;
  let revenueChartInst = null;
  let expensesChartInst = null;
  let profitChartInst = null;

  function destroyCharts() {
    if (yieldChartInst) yieldChartInst.destroy();
    if (revenueChartInst) revenueChartInst.destroy();
    if (expensesChartInst) expensesChartInst.destroy();
    if (profitChartInst) profitChartInst.destroy();
  }

  function renderCharts(data, inputs) {
    destroyCharts();

    const expectedYield = parseFloat(data.expected_yield);
    const revenue = parseFloat(data.estimated_revenue);
    const expenses = parseFloat(data.estimated_expenses);
    const profit = parseFloat(data.estimated_profit);
    const seed = parseFloat(inputs.seed_cost);
    const fertilizer = parseFloat(inputs.fertilizer_cost);
    const labor = parseFloat(inputs.labor_cost);

    // 1. Yield Comparison (Baseline Average Yield vs Forecasted Yield)
    const baseAverageYield = parseFloat(inputs.farm_size) * 1.5; // simple average baseline
    const ctxYield = document.getElementById('yieldChart').getContext('2d');
    yieldChartInst = new Chart(ctxYield, {
      type: 'bar',
      data: {
        labels: ['Regional Average', 'Your Forecast'],
        datasets: [{
          label: 'Yield (Tonnes)',
          data: [baseAverageYield.toFixed(2), expectedYield.toFixed(2)],
          backgroundColor: ['#cbd5e1', '#22c55e'],
          borderWidth: 0,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });

    // 2. Revenue Projection
    const ctxRevenue = document.getElementById('revenueChart').getContext('2d');
    revenueChartInst = new Chart(ctxRevenue, {
      type: 'bar',
      data: {
        labels: ['Total Revenue'],
        datasets: [{
          label: 'Revenue (₹)',
          data: [revenue],
          backgroundColor: ['#3b82f6'],
          borderWidth: 0,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });

    // 3. Expenses Breakdown
    const ctxExpenses = document.getElementById('expensesChart').getContext('2d');
    expensesChartInst = new Chart(ctxExpenses, {
      type: 'doughnut',
      data: {
        labels: ['Seed Cost', 'Fertilizer Cost', 'Labor Cost'],
        datasets: [{
          data: [seed, fertilizer, labor],
          backgroundColor: ['#f59e0b', '#ec4899', '#ef4444'],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }
      }
    });

    // 4. Profit Analysis (Expenses vs Profit)
    const ctxProfit = document.getElementById('profitChart').getContext('2d');
    profitChartInst = new Chart(ctxProfit, {
      type: 'pie',
      data: {
        labels: ['Total Expenses', 'Net Profit'],
        datasets: [{
          data: [expenses, Math.max(0, profit)],
          backgroundColor: ['#ef4444', '#10b981'],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }
      }
    });
  }

  // Bind Submit event
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const crop_type = document.getElementById('crop_type').value;
      const farm_size = document.getElementById('farm_size').value;
      const soil_type = document.getElementById('soil_type').value;
      const season = document.getElementById('season').value;
      const rainfall = document.getElementById('rainfall').value;
      const temperature = document.getElementById('temperature').value;
      const seed_cost = document.getElementById('seed_cost').value;
      const fertilizer_cost = document.getElementById('fertilizer_cost').value;
      const labor_cost = document.getElementById('labor_cost').value;

      const payload = {
        crop_type,
        farm_size,
        soil_type,
        season,
        rainfall,
        temperature,
        seed_cost,
        fertilizer_cost,
        labor_cost
      };

      try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const response = await fetch('/api/yield-prediction/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
          alert(data.error || 'Failed to generate prediction');
          return;
        }

        // Show result panel, hide welcome panel
        if (welcomePanel) welcomePanel.classList.add('d-none');
        if (resultPanel) resultPanel.classList.remove('d-none');

        // Populate metrics
        resYield.textContent = data.expected_yield;
        resRevenue.textContent = parseFloat(data.estimated_revenue).toLocaleString('en-IN');
        resExpenses.textContent = parseFloat(data.estimated_expenses).toLocaleString('en-IN');
        resProfit.textContent = parseFloat(data.estimated_profit).toLocaleString('en-IN');
        resMargin.textContent = data.profit_margin;

        // Recommendations List
        recommendationsList.innerHTML = '';
        if (data.recommendations && data.recommendations.length) {
          data.recommendations.forEach(tip => {
            const item = document.createElement('div');
            item.className = 'recommendation-item';
            item.textContent = tip;
            recommendationsList.appendChild(item);
          });
        }

        // Render Charts
        renderCharts(data, payload);

      } catch (err) {
        console.error(err);
        alert('An error occurred during estimation calculation.');
      }
    });
  }

  // Fetch current weather coordinates for defaults
  if (fetchWeatherBtn) {
    fetchWeatherBtn.addEventListener('click', async () => {
      fetchWeatherBtn.disabled = true;
      try {
        // Try getting weather info from system
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const response = await fetch('/api/weather/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({}) // triggers profile fallback
        });
        
        const data = await response.json();
        if (response.ok && data.current) {
          const temp = data.current.temp || 24;
          const humidity = data.current.humidity || 50;
          // approximate monthly rainfall from humidity/weather
          const calculatedRainfall = data.current.rainfall_mm > 0 ? (data.current.rainfall_mm * 30) : (humidity * 10);
          
          document.getElementById('temperature').value = temp;
          document.getElementById('rainfall').value = Math.round(calculatedRainfall);
        }
      } catch (e) {
        console.warn('Could not fetch weather data defaults.', e);
      } finally {
        fetchWeatherBtn.disabled = false;
      }
    });
  }

  // Reset button
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      form.reset();
      destroyCharts();
      if (welcomePanel) welcomePanel.classList.remove('d-none');
      if (resultPanel) resultPanel.classList.add('d-none');
    });
  }

})();
