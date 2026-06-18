/**
 * Plant disease detection — image upload and /api/detect-disease/
 */
(function () {
  const dropZone = document.getElementById('dropZone');
  const selectPhotoBtn = document.getElementById('selectPhotoBtn');
  const fileInput = document.getElementById('fileInput');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const resetBtn = document.getElementById('resetBtn');
  const thumb = document.getElementById('thumb');
  const previewWrap = document.getElementById('previewWrap');
  const status = document.getElementById('status');
  const results = document.getElementById('results');

  if (!fileInput || !analyzeBtn) return;

  let currentFile = null;
  let previewUrl = null;

  function openFilePicker() {
    fileInput.click();
  }

  if (selectPhotoBtn) {
    selectPhotoBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      openFilePicker();
    });
  }

  if (dropZone) {
    dropZone.addEventListener('click', (e) => {
      if (e.target === selectPhotoBtn || e.target.closest('#selectPhotoBtn')) return;
      openFilePicker();
    });
    dropZone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openFilePicker();
      }
    });
    ['dragenter', 'dragover'].forEach((ev) => {
      dropZone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach((ev) => {
      dropZone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
      });
    });
    dropZone.addEventListener('drop', (e) => handleFile(e.dataTransfer.files[0]));
  }

  fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

  function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) {
      if (status) status.textContent = 'Please select an image file (PNG or JPG).';
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      if (status) status.textContent = 'Max size 8MB.';
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    currentFile = file;
    previewUrl = URL.createObjectURL(file);
    if (thumb) thumb.src = previewUrl;
    if (previewWrap) previewWrap.classList.remove('d-none');
    analyzeBtn.disabled = false;
    if (results) results.classList.add('d-none');
    if (status) status.textContent = '';
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      currentFile = null;
      fileInput.value = '';
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
      if (previewWrap) previewWrap.classList.add('d-none');
      analyzeBtn.disabled = true;
      if (results) results.classList.add('d-none');
      if (status) status.textContent = '';
    });
  }

  analyzeBtn.addEventListener('click', async () => {
    if (!currentFile) return;
    if (status) {
      status.innerHTML = '<span class="spinner-border spinner-border-sm text-success"></span> Analyzing…';
    }
    analyzeBtn.disabled = true;

    try {
      const form = new FormData();
      form.append('image', currentFile, currentFile.name || 'leaf.jpg');

      const api = window.AgroApi;
      const { resp, data } = api
        ? await api.postForm('/api/detect-disease/', form)
        : await (async () => {
            const r = await fetch('/api/detect-disease/', {
              method: 'POST',
              body: form,
              credentials: 'same-origin',
            });
            return { resp: r, data: await r.json().catch(() => ({})) };
          })();

      if (!resp.ok) {
        if (resp.status === 401 || resp.status === 403) {
          window.location.href = '/login/?next=/disease/';
          return;
        }
        throw new Error(data.error || `Request failed (${resp.status})`);
      }

      renderResults(data);
      if (status) {
        status.textContent = data.source ? `Analysis: ${data.source}` : '';
      }
    } catch (err) {
      if (results) {
        results.classList.remove('d-none');
        results.innerHTML = `<div class="alert alert-danger mb-0">${err.message}</div>`;
      }
      if (status) status.textContent = '';
    } finally {
      analyzeBtn.disabled = !currentFile;
    }
  });

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function renderResults(data) {
    if (!results) return;
    results.classList.remove('d-none');

    const top = data.predictions?.[0]?.disease || 'Unknown';
    const conf = ((data.confidence || 0) * 100).toFixed(0);

    let html = `<div class="card disease-card shadow-sm mb-3"><div class="card-body">
      <h4 class="text-success mb-2"><i class="fas fa-diagnoses me-2"></i>Detected: ${escapeHtml(top)}</h4>
      <p class="mb-2">Confidence: <strong>${conf}%</strong></p>`;

    if (data.image_url) {
      html += `<img src="${escapeHtml(data.image_url)}" class="preview-img mb-3" alt="uploaded">`;
    }
    if (data.note) {
      html += `<p class="small text-warning"><i class="fas fa-info-circle me-1"></i>${escapeHtml(data.note)}</p>`;
    }

    html += '<h6 class="fw-semibold">All predictions</h6><div class="list-group mb-3">';
    (data.predictions || []).forEach((p) => {
      const pct = ((p.probability || 0) * 100).toFixed(1);
      html += `<div class="list-group-item">
        <div class="d-flex justify-content-between"><span>${escapeHtml(p.disease)}</span><span>${pct}%</span></div>
        <div class="confidence-bar mt-1"><span style="width:${Math.min(100, pct)}%"></span></div>
      </div>`;
    });
    html += '</div>';

    if (data.top_solution?.length) {
      html += '<h6 class="fw-semibold text-warning"><i class="fas fa-pills me-1"></i>Treatment plan</h6><ul class="mb-0">';
      data.top_solution.forEach((s) => {
        html += `<li>${escapeHtml(s)}</li>`;
      });
      html += '</ul>';
    }

    html += '</div></div>';
    results.innerHTML = html;
  }
})();
