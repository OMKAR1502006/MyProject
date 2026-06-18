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

  if (selectPhotoBtn && selectPhotoBtn.tagName === 'LABEL') {
    /* label[for=fileInput] opens picker natively */
  } else if (selectPhotoBtn) {
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
      if (err.message && (err.message.includes("Invalid Image") || err.message.includes("No plant material detected"))) {
        renderInvalidImageCard(previewUrl);
      } else {
        if (results) {
          results.classList.remove('d-none');
          results.innerHTML = `<div class="alert alert-danger mb-0">${err.message}</div>`;
        }
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

  function renderInvalidImageCard(imageUrl) {
    if (!results) return;
    results.classList.remove('d-none');

    let html = `
    <div class="card shadow-sm border-0 mb-3" style="background-color: #fff5f5; border-left: 5px solid #ef4444 !important; border-radius: 12px; overflow: hidden;">
      <div class="card-body p-4">
        <div class="row align-items-center">
          <div class="col-md-8">
            <div class="d-flex align-items-center gap-2 mb-3">
              <span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-1.5 rounded-pill fw-bold" style="font-size: 0.85rem;">
                <i class="fas fa-times-circle me-1"></i>Not a Plant Leaf
              </span>
            </div>
            
            <h3 class="text-danger fw-bold mb-2" style="font-size: 1.6rem; letter-spacing: -0.02em;">No plant material detected</h3>
            <p class="text-muted mb-3" style="font-size: 0.95rem;">Confidence: <strong class="text-danger">0%</strong></p>
            <p class="lead text-secondary mb-4 fs-6" style="color: #4b5563;">The uploaded image does not appear to contain a crop or plant leaf.</p>
            
            <hr class="my-4" style="border-top: 1px solid #fee2e2;">

            <div class="mb-4">
              <h6 class="fw-bold text-dark mb-3" style="font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em;">
                <i class="fas fa-question-circle me-2 text-danger"></i>Why this image is not suitable?
              </h6>
              <ul class="list-unstyled ps-0 mb-0" style="font-size: 0.925rem; color: #4b5563;">
                <li class="mb-2 d-flex align-items-center"><i class="fas fa-times text-danger me-2" style="width: 14px;"></i>Contains text or UI elements</li>
                <li class="mb-2 d-flex align-items-center"><i class="fas fa-times text-danger me-2" style="width: 14px;"></i>Looks like a screenshot or document</li>
                <li class="d-flex align-items-center"><i class="fas fa-times text-danger me-2" style="width: 14px;"></i>No visible leaf structure found</li>
              </ul>
            </div>

            <div class="mb-4">
              <h6 class="fw-bold text-dark mb-3" style="font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.05em;">
                <i class="fas fa-check-circle me-2 text-success"></i>Supported Images
              </h6>
              <div class="row g-2">
                <div class="col-6 col-sm-3">
                  <div class="p-2.5 border rounded text-center bg-white shadow-sm d-flex flex-column align-items-center justify-content-center" style="font-size: 0.85rem; border-color: #f3f4f6 !important; border-radius: 8px;">
                    <i class="fas fa-leaf text-success mb-1.5 fs-5"></i>Tomato Leaf
                  </div>
                </div>
                <div class="col-6 col-sm-3">
                  <div class="p-2.5 border rounded text-center bg-white shadow-sm d-flex flex-column align-items-center justify-content-center" style="font-size: 0.85rem; border-color: #f3f4f6 !important; border-radius: 8px;">
                    <i class="fas fa-leaf text-success mb-1.5 fs-5"></i>Potato Leaf
                  </div>
                </div>
                <div class="col-6 col-sm-3">
                  <div class="p-2.5 border rounded text-center bg-white shadow-sm d-flex flex-column align-items-center justify-content-center" style="font-size: 0.85rem; border-color: #f3f4f6 !important; border-radius: 8px;">
                    <i class="fas fa-leaf text-success mb-1.5 fs-5"></i>Rice Leaf
                  </div>
                </div>
                <div class="col-6 col-sm-3">
                  <div class="p-2.5 border rounded text-center bg-white shadow-sm d-flex flex-column align-items-center justify-content-center" style="font-size: 0.85rem; border-color: #f3f4f6 !important; border-radius: 8px;">
                    <i class="fas fa-leaf text-success mb-1.5 fs-5"></i>Corn Leaf
                  </div>
                </div>
              </div>
            </div>

            <div class="alert alert-info border-0 mb-0 d-flex align-items-start gap-2" style="background-color: #eff6ff; color: #1e3a8a; border-radius: 8px;">
              <i class="fas fa-info-circle fs-5 mt-0.5"></i>
              <span style="font-size: 0.9rem; line-height: 1.4;">Upload a clear photo of a crop leaf for disease analysis.</span>
            </div>
          </div>
          <div class="col-md-4 text-center mt-4 mt-md-0 d-flex flex-column align-items-center justify-content-center gap-3">
    `;

    if (imageUrl) {
      html += `<img src="${escapeHtml(imageUrl)}" class="preview-img img-fluid border shadow-sm" style="max-height: 220px; object-fit: contain; border-radius: 12px; background: #fff;" alt="uploaded preview">`;
    } else {
      html += `
        <i class="fas fa-exclamation-triangle fa-4x text-danger mb-1 d-block d-md-none"></i>
        <i class="fas fa-exclamation-triangle fa-5x text-danger mb-1 d-none d-md-block mx-auto"></i>
      `;
    }

    html += `
          </div>
        </div>
      </div>
    </div>
    `;
    results.innerHTML = html;
  }

  function renderResults(data) {
    if (!results) return;
    results.classList.remove('d-none');

    const top = data.predictions?.[0]?.disease || 'Unknown';
    const conf = ((data.confidence || 0) * 100).toFixed(0);

    if (top === "No plant material detected") {
      renderInvalidImageCard(data.image_url || previewUrl);
      return;
    }

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
