// LINK Inpaint Studio — Advanced Canvas Application Logic

(async function () {
  // --- URL & Session Params ---
  const urlParams = new URLSearchParams(window.location.search);
  const sessionToken = urlParams.get('token');
  const clientId = urlParams.get('client_id');

  const statusOverlay = document.getElementById('status-overlay');
  const statusText = document.getElementById('status-text');

  function setStatus(msg, showSpinner = true) {
    statusText.textContent = msg;
    const spinner = statusOverlay.querySelector('.spinner');
    if (spinner) spinner.style.display = showSpinner ? 'block' : 'none';
    statusOverlay.classList.remove('hidden');
  }

  function hideStatus() {
    statusOverlay.classList.add('hidden');
  }

  // --- Fetch Session Data ---
  if (!sessionToken) {
    setStatus("Error: Invalid or missing session token. Please run /inpaint in Discord.", false);
    return;
  }

  let sessionData = null;
  try {
    setStatus("Loading inpaint session...");
    const res = await fetch(`/api/inpaint/session/${sessionToken}`);
    if (!res.ok) {
      const errDetail = await res.json().catch(() => ({}));
      throw new Error(errDetail.detail || `Session not found or expired (${res.status})`);
    }
    sessionData = await res.json();
  } catch (err) {
    setStatus(`Error: ${err.message}`, false);
    return;
  }

  // Set prompt input default
  const promptInput = document.getElementById('prompt-input');
  if (sessionData.prompt) {
    promptInput.value = sessionData.prompt;
  }

  // --- Canvas Setup ---
  const viewport = document.getElementById('viewport');
  const stack = document.getElementById('canvas-stack');
  const bgCanvas = document.getElementById('bg-canvas');
  const maskCanvas = document.getElementById('mask-canvas');
  const gridCanvas = document.getElementById('grid-canvas');
  const cursorCanvas = document.getElementById('cursor-canvas');

  const bgCtx = bgCanvas.getContext('2d');
  const maskCtx = maskCanvas.getContext('2d');
  const gridCtx = gridCanvas.getContext('2d');
  const cursorCtx = cursorCanvas.getContext('2d');

  let imgWidth = 512;
  let imgHeight = 512;

  // Load Source Image
  const img = new Image();
  img.crossOrigin = "anonymous";

  await new Promise((resolve, reject) => {
    img.onload = resolve;
    img.onerror = () => reject(new Error("Failed to load source image."));
    img.src = sessionData.source_image_url;
  });

  imgWidth = img.naturalWidth || img.width;
  imgHeight = img.naturalHeight || img.height;

  // Set canvas dimensions
  [bgCanvas, maskCanvas, gridCanvas, cursorCanvas].forEach(c => {
    c.width = imgWidth;
    c.height = imgHeight;
  });

  // Draw background image
  bgCtx.drawImage(img, 0, 0, imgWidth, imgHeight);

  // Setup stack dimensions in container
  const maxW = viewport.clientWidth - 40;
  const maxH = viewport.clientHeight - 40;
  const initialScale = Math.min(maxW / imgWidth, maxH / imgHeight, 1.0);

  const displayW = Math.round(imgWidth * initialScale);
  const displayH = Math.round(imgHeight * initialScale);

  stack.style.width = `${displayW}px`;
  stack.style.height = `${displayH}px`;

  hideStatus();

  // --- State Variables ---
  let mode = 'brush'; // 'brush' | 'eraser' | 'lasso' | 'wand' | 'grid-fill' | 'pan'
  let shape = 'circle'; // 'circle' | 'square' | 'soft'
  let gridPreset = 'off'; // 'off' | '1/2' | '1/3' | '1/4' | '3h' | '3v' | '2h' | '2v'
  let brushSize = 40;
  let wandTolerance = 32;
  let brushOpacity = 1.0;
  let overlayOpacity = 0.65;
  let isMaskVisible = true;

  // Zoom & Pan State
  let zoomLevel = 1.0; // 0.25 to 5.0
  let panX = 0;
  let panY = 0;
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;

  // Drawing & Selection State
  let isDrawing = false;
  let lastX = 0;
  let lastY = 0;
  let lassoPoints = [];
  let hoverGridCell = null;

  // Undo/Redo History
  const undoStack = [];
  const redoStack = [];
  const MAX_HISTORY = 30;

  function saveState() {
    if (undoStack.length >= MAX_HISTORY) undoStack.shift();
    undoStack.push(maskCtx.getImageData(0, 0, imgWidth, imgHeight));
    redoStack.length = 0; // Clear redo
  }

  // Save initial blank state
  saveState();

  // --- Controls Wiring ---
  const btnBrush = document.getElementById('btn-brush');
  const btnEraser = document.getElementById('btn-eraser');
  const btnLasso = document.getElementById('btn-lasso');
  const btnWand = document.getElementById('btn-wand');
  const btnGridFill = document.getElementById('btn-grid-fill');
  const btnPan = document.getElementById('btn-pan');

  const shapeGroup = document.getElementById('shape-group');
  const btnShapeCircle = document.getElementById('btn-shape-circle');
  const btnShapeSquare = document.getElementById('btn-shape-square');
  const btnShapeSoft = document.getElementById('btn-shape-soft');

  const gridSelect = document.getElementById('grid-select');

  const btnZoomOut = document.getElementById('btn-zoom-out');
  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomReset = document.getElementById('btn-zoom-reset');
  const zoomVal = document.getElementById('zoom-val');

  const sizeContainer = document.getElementById('size-container');
  const sizeSlider = document.getElementById('size-slider');
  const sizeVal = document.getElementById('size-val');

  const wandTolContainer = document.getElementById('wand-tol-container');
  const wandTolSlider = document.getElementById('wand-tol-slider');
  const wandTolVal = document.getElementById('wand-tol-val');

  const opacitySlider = document.getElementById('opacity-slider');
  const opacityVal = document.getElementById('opacity-val');
  const overlaySlider = document.getElementById('overlay-slider');
  const overlayVal = document.getElementById('overlay-val');

  const btnUndo = document.getElementById('btn-undo');
  const btnRedo = document.getElementById('btn-redo');
  const btnToggleMask = document.getElementById('btn-toggle-mask');
  const btnClear = document.getElementById('btn-clear');
  const btnSubmit = document.getElementById('btn-submit');

  const toolButtons = [btnBrush, btnEraser, btnLasso, btnWand, btnGridFill, btnPan];

  function setToolMode(m, activeBtn) {
    mode = m;
    toolButtons.forEach(b => b.classList.remove('active'));
    if (activeBtn) activeBtn.classList.add('active');

    viewport.classList.toggle('mode-pan', mode === 'pan');

    // Dynamic UI visibility based on selected tool
    if (mode === 'brush' || mode === 'eraser') {
      shapeGroup.classList.remove('hidden-tool');
      sizeContainer.classList.remove('hidden-tool');
      wandTolContainer.classList.add('hidden-tool');
    } else if (mode === 'wand') {
      shapeGroup.classList.add('hidden-tool');
      sizeContainer.classList.add('hidden-tool');
      wandTolContainer.classList.remove('hidden-tool');
    } else {
      shapeGroup.classList.add('hidden-tool');
      sizeContainer.classList.add('hidden-tool');
      wandTolContainer.classList.add('hidden-tool');
    }

    renderGrid();
    cursorCtx.clearRect(0, 0, imgWidth, imgHeight);
  }

  btnBrush.addEventListener('click', () => setToolMode('brush', btnBrush));
  btnEraser.addEventListener('click', () => setToolMode('eraser', btnEraser));
  btnLasso.addEventListener('click', () => setToolMode('lasso', btnLasso));
  btnWand.addEventListener('click', () => setToolMode('wand', btnWand));
  btnGridFill.addEventListener('click', () => setToolMode('grid-fill', btnGridFill));
  btnPan.addEventListener('click', () => setToolMode('pan', btnPan));

  // Initialize tool view
  setToolMode('brush', btnBrush);

  function setShape(s, btn) {
    shape = s;
    [btnShapeCircle, btnShapeSquare, btnShapeSoft].forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }

  btnShapeCircle.addEventListener('click', () => setShape('circle', btnShapeCircle));
  btnShapeSquare.addEventListener('click', () => setShape('square', btnShapeSquare));
  btnShapeSoft.addEventListener('click', () => setShape('soft', btnShapeSoft));

  // Grid selection
  gridSelect.addEventListener('change', (e) => {
    gridPreset = e.target.value;
    renderGrid();
  });

  // Zoom Engine
  function applyTransform() {
    stack.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
    zoomVal.textContent = `${Math.round(zoomLevel * 100)}%`;
  }

  function setZoom(newZoom) {
    zoomLevel = Math.min(5.0, Math.max(0.25, newZoom));
    applyTransform();
  }

  btnZoomIn.addEventListener('click', () => setZoom(zoomLevel + 0.25));
  btnZoomOut.addEventListener('click', () => setZoom(zoomLevel - 0.25));
  btnZoomReset.addEventListener('click', () => {
    zoomLevel = 1.0;
    panX = 0;
    panY = 0;
    applyTransform();
  });

  // Mouse wheel zoom
  viewport.addEventListener('wheel', (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    setZoom(zoomLevel * zoomFactor);
  }, { passive: false });

  // Sliders
  sizeSlider.addEventListener('input', (e) => {
    brushSize = parseInt(e.target.value, 10);
    sizeVal.textContent = `${brushSize}px`;
  });

  wandTolSlider.addEventListener('input', (e) => {
    wandTolerance = parseInt(e.target.value, 10);
    wandTolVal.textContent = wandTolerance.toString();
  });

  if (opacitySlider) {
    opacitySlider.addEventListener('input', (e) => {
      const pct = parseInt(e.target.value, 10);
      brushOpacity = pct / 100.0;
      opacityVal.textContent = `${pct}%`;
    });
  }

  if (overlaySlider) {
    overlaySlider.addEventListener('input', (e) => {
      const pct = parseInt(e.target.value, 10);
      overlayOpacity = pct / 100.0;
      overlayVal.textContent = `${pct}%`;
      if (isMaskVisible) {
        maskCanvas.style.opacity = overlayOpacity.toString();
      }
    });
  }

  // History & Actions
  btnUndo.addEventListener('click', () => {
    if (undoStack.length > 1) {
      redoStack.push(undoStack.pop());
      const state = undoStack[undoStack.length - 1];
      maskCtx.putImageData(state, 0, 0);
    }
  });

  btnRedo.addEventListener('click', () => {
    if (redoStack.length > 0) {
      const state = redoStack.pop();
      undoStack.push(state);
      maskCtx.putImageData(state, 0, 0);
    }
  });

  btnToggleMask.addEventListener('click', () => {
    isMaskVisible = !isMaskVisible;
    btnToggleMask.classList.toggle('active', isMaskVisible);
    maskCanvas.style.opacity = isMaskVisible ? overlayOpacity.toString() : '0';
  });

  btnClear.addEventListener('click', () => {
    saveState();
    maskCtx.clearRect(0, 0, imgWidth, imgHeight);
  });

  // --- Grid Rendering Logic ---
  function getGridDimensions() {
    switch (gridPreset) {
      case '1/2': return { rows: 2, cols: 2 };
      case '1/3': return { rows: 3, cols: 3 };
      case '1/4': return { rows: 4, cols: 4 };
      case '3h': return { rows: 3, cols: 1 };
      case '3v': return { rows: 1, cols: 3 };
      case '2h': return { rows: 2, cols: 1 };
      case '2v': return { rows: 1, cols: 2 };
      default: return null;
    }
  }

  function renderGrid() {
    gridCtx.clearRect(0, 0, imgWidth, imgHeight);
    const dims = getGridDimensions();
    if (!dims) return;

    const { rows, cols } = dims;
    const cellW = imgWidth / cols;
    const cellH = imgHeight / rows;

    gridCtx.save();

    // Hover Cell Highlight
    if (hoverGridCell && hoverGridCell.rows === rows && hoverGridCell.cols === cols) {
      const { row, col } = hoverGridCell;
      gridCtx.fillStyle = mode === 'eraser' ? 'rgba(239, 68, 68, 0.35)' : 'rgba(99, 102, 241, 0.35)';
      gridCtx.fillRect(col * cellW, row * cellH, cellW, cellH);

      gridCtx.strokeStyle = mode === 'eraser' ? '#ef4444' : '#6366f1';
      gridCtx.lineWidth = 3;
      gridCtx.strokeRect(col * cellW, row * cellH, cellW, cellH);
    }

    // Grid Lines
    gridCtx.strokeStyle = 'rgba(99, 102, 241, 0.75)';
    gridCtx.lineWidth = Math.max(1, Math.round(2 / zoomLevel));
    gridCtx.setLineDash([6, 4]);

    for (let c = 1; c < cols; c++) {
      const x = c * cellW;
      gridCtx.beginPath();
      gridCtx.moveTo(x, 0);
      gridCtx.lineTo(x, imgHeight);
      gridCtx.stroke();
    }

    for (let r = 1; r < rows; r++) {
      const y = r * cellH;
      gridCtx.beginPath();
      gridCtx.moveTo(0, y);
      gridCtx.lineTo(imgWidth, y);
      gridCtx.stroke();
    }

    gridCtx.restore();
  }

  function fillGridSection(col, row, rows, cols) {
    saveState();
    const cellW = imgWidth / cols;
    const cellH = imgHeight / rows;
    const x = col * cellW;
    const y = row * cellH;

    maskCtx.save();
    maskCtx.globalAlpha = brushOpacity;
    if (mode === 'eraser') {
      maskCtx.globalCompositeOperation = 'destination-out';
      maskCtx.fillRect(x, y, cellW, cellH);
    } else {
      maskCtx.globalCompositeOperation = 'source-over';
      maskCtx.fillStyle = 'red';
      maskCtx.fillRect(x, y, cellW, cellH);
    }
    maskCtx.restore();
  }

  // --- Content-Aware Magic Wand (BFS Flood Fill) ---
  function performMagicWand(startX, startY) {
    if (startX < 0 || startX >= imgWidth || startY < 0 || startY >= imgHeight) return;
    saveState();

    const srcData = bgCtx.getImageData(0, 0, imgWidth, imgHeight);
    const pixels = srcData.data;

    const startIdx = (startY * imgWidth + startX) * 4;
    const targetR = pixels[startIdx];
    const targetG = pixels[startIdx + 1];
    const targetB = pixels[startIdx + 2];

    const maxDistSq = Math.pow((wandTolerance / 100) * 255, 2);

    const visited = new Uint8Array(imgWidth * imgHeight);
    const queue = [startY * imgWidth + startX];
    visited[startY * imgWidth + startX] = 1;

    const maskData = maskCtx.getImageData(0, 0, imgWidth, imgHeight);
    const mPixels = maskData.data;
    const alphaVal = Math.round(brushOpacity * 255);

    let head = 0;
    while (head < queue.length) {
      const curr = queue[head++];
      const cx = curr % imgWidth;
      const cy = Math.floor(curr / imgWidth);

      const pIdx = curr * 4;
      const r = pixels[pIdx];
      const g = pixels[pIdx + 1];
      const b = pixels[pIdx + 2];

      const distSq = Math.pow(r - targetR, 2) + Math.pow(g - targetG, 2) + Math.pow(b - targetB, 2);

      if (distSq <= maxDistSq) {
        if (mode === 'eraser') {
          mPixels[pIdx + 3] = 0;
        } else {
          mPixels[pIdx] = 255;
          mPixels[pIdx + 1] = 0;
          mPixels[pIdx + 2] = 0;
          mPixels[pIdx + 3] = alphaVal;
        }

        // Neighbors: left, right, top, bottom
        if (cx > 0 && !visited[curr - 1]) { visited[curr - 1] = 1; queue.push(curr - 1); }
        if (cx < imgWidth - 1 && !visited[curr + 1]) { visited[curr + 1] = 1; queue.push(curr + 1); }
        if (cy > 0 && !visited[curr - imgWidth]) { visited[curr - imgWidth] = 1; queue.push(curr - imgWidth); }
        if (cy < imgHeight - 1 && !visited[curr + imgWidth]) { visited[curr + imgWidth] = 1; queue.push(curr + imgWidth); }
      }
    }

    maskCtx.putImageData(maskData, 0, 0);
  }

  // --- Lasso Fill Logic ---
  function finishLasso() {
    if (lassoPoints.length < 3) {
      lassoPoints = [];
      cursorCtx.clearRect(0, 0, imgWidth, imgHeight);
      return;
    }

    saveState();
    maskCtx.save();
    maskCtx.globalAlpha = brushOpacity;
    if (mode === 'eraser') {
      maskCtx.globalCompositeOperation = 'destination-out';
    } else {
      maskCtx.globalCompositeOperation = 'source-over';
      maskCtx.fillStyle = 'red';
    }

    maskCtx.beginPath();
    maskCtx.moveTo(lassoPoints[0].x, lassoPoints[0].y);
    for (let i = 1; i < lassoPoints.length; i++) {
      maskCtx.lineTo(lassoPoints[i].x, lassoPoints[i].y);
    }
    maskCtx.closePath();
    maskCtx.fill();
    maskCtx.restore();

    lassoPoints = [];
    cursorCtx.clearRect(0, 0, imgWidth, imgHeight);
  }

  // --- Coordinate Mapping ---
  function getCanvasCoords(e) {
    const rect = stack.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const x = Math.round((clientX - rect.left) * (imgWidth / rect.width));
    const y = Math.round((clientY - rect.top) * (imgHeight / rect.height));
    return { x, y };
  }

  // --- Brush Stamp & Line ---
  function drawStamp(x, y) {
    maskCtx.save();
    maskCtx.globalAlpha = brushOpacity;
    if (mode === 'eraser') {
      maskCtx.globalCompositeOperation = 'destination-out';
    } else {
      maskCtx.globalCompositeOperation = 'source-over';
      maskCtx.fillStyle = 'red';
    }

    const radius = brushSize / 2;

    if (shape === 'circle') {
      maskCtx.beginPath();
      maskCtx.arc(x, y, radius, 0, Math.PI * 2);
      maskCtx.fill();
    } else if (shape === 'square') {
      maskCtx.fillRect(x - radius, y - radius, brushSize, brushSize);
    } else if (shape === 'soft') {
      const grad = maskCtx.createRadialGradient(x, y, radius * 0.2, x, y, radius);
      if (mode === 'eraser') {
        grad.addColorStop(0, `rgba(0,0,0,${brushOpacity})`);
        grad.addColorStop(1, 'rgba(0,0,0,0)');
      } else {
        grad.addColorStop(0, `rgba(255,0,0,${brushOpacity})`);
        grad.addColorStop(1, 'rgba(255,0,0,0)');
      }
      maskCtx.fillStyle = grad;
      maskCtx.beginPath();
      maskCtx.arc(x, y, radius, 0, Math.PI * 2);
      maskCtx.fill();
    }
    maskCtx.restore();
  }

  function drawLine(x1, y1, x2, y2) {
    const dist = Math.hypot(x2 - x1, y2 - y1);
    const step = Math.max(1, brushSize / 4);
    for (let i = 0; i <= dist; i += step) {
      const t = dist === 0 ? 0 : i / dist;
      const px = x1 + (x2 - x1) * t;
      const py = y1 + (y2 - y1) * t;
      drawStamp(px, py);
    }
  }

  function renderCursor(x, y) {
    cursorCtx.clearRect(0, 0, imgWidth, imgHeight);

    if (mode === 'lasso' && lassoPoints.length > 0) {
      cursorCtx.save();
      cursorCtx.strokeStyle = mode === 'eraser' ? '#ef4444' : '#6366f1';
      cursorCtx.lineWidth = 2;
      cursorCtx.setLineDash([4, 4]);
      cursorCtx.beginPath();
      cursorCtx.moveTo(lassoPoints[0].x, lassoPoints[0].y);
      for (let i = 1; i < lassoPoints.length; i++) {
        cursorCtx.lineTo(lassoPoints[i].x, lassoPoints[i].y);
      }
      cursorCtx.lineTo(x, y);
      cursorCtx.stroke();
      cursorCtx.restore();
      return;
    }

    if (x < 0 || x > imgWidth || y < 0 || y > imgHeight) return;

    cursorCtx.save();
    cursorCtx.strokeStyle = mode === 'eraser' ? '#ef4444' : '#ffffff';
    cursorCtx.lineWidth = 2;

    if (mode === 'brush' || mode === 'eraser') {
      const r = brushSize / 2;
      if (shape === 'square') {
        cursorCtx.strokeRect(x - r, y - r, brushSize, brushSize);
      } else {
        cursorCtx.beginPath();
        cursorCtx.arc(x, y, r, 0, Math.PI * 2);
        cursorCtx.stroke();
      }
    } else if (mode === 'wand') {
      cursorCtx.fillStyle = '#6366f1';
      cursorCtx.font = '16px sans-serif';
      cursorCtx.fillText('🪄', x - 8, y + 6);
    }
    cursorCtx.restore();
  }

  // --- Pointer Events ---
  stack.addEventListener('pointerdown', (e) => {
    const { x, y } = getCanvasCoords(e);

    // Pan Mode
    if (mode === 'pan' || e.button === 1 || e.spaceKey) {
      isPanning = true;
      panStartX = e.clientX - panX;
      panStartY = e.clientY - panY;
      return;
    }

    // Grid Fill Mode
    if (mode === 'grid-fill') {
      const dims = getGridDimensions();
      if (dims) {
        const { rows, cols } = dims;
        const cellW = imgWidth / cols;
        const cellH = imgHeight / rows;
        const col = Math.floor(x / cellW);
        const row = Math.floor(y / cellH);
        if (col >= 0 && col < cols && row >= 0 && row < rows) {
          fillGridSection(col, row, rows, cols);
        }
      }
      return;
    }

    // Magic Wand Mode
    if (mode === 'wand') {
      performMagicWand(x, y);
      return;
    }

    // Lasso Mode
    if (mode === 'lasso') {
      isDrawing = true;
      lassoPoints = [{ x, y }];
      return;
    }

    // Brush / Eraser Mode
    isDrawing = true;
    saveState();
    lastX = x;
    lastY = y;
    drawStamp(x, y);
  });

  window.addEventListener('pointermove', (e) => {
    // Handle Panning
    if (isPanning) {
      panX = e.clientX - panStartX;
      panY = e.clientY - panStartY;
      applyTransform();
      return;
    }

    const { x, y } = getCanvasCoords(e);

    // Grid Hover Detection
    const dims = getGridDimensions();
    if (dims && (mode === 'grid-fill' || gridPreset !== 'off')) {
      const { rows, cols } = dims;
      const cellW = imgWidth / cols;
      const cellH = imgHeight / rows;
      const col = Math.floor(x / cellW);
      const row = Math.floor(y / cellH);
      if (col >= 0 && col < cols && row >= 0 && row < rows) {
        if (!hoverGridCell || hoverGridCell.row !== row || hoverGridCell.col !== col) {
          hoverGridCell = { row, col, rows, cols };
          renderGrid();
        }
      } else if (hoverGridCell) {
        hoverGridCell = null;
        renderGrid();
      }
    }

    renderCursor(x, y);

    if (!isDrawing) return;

    if (mode === 'lasso') {
      lassoPoints.push({ x, y });
    } else if (mode === 'brush' || mode === 'eraser') {
      drawLine(lastX, lastY, x, y);
      lastX = x;
      lastY = y;
    }
  });

  window.addEventListener('pointerup', () => {
    if (isPanning) {
      isPanning = false;
      return;
    }

    if (isDrawing) {
      if (mode === 'lasso') {
        finishLasso();
      }
      isDrawing = false;
    }
  });

  // --- Submission Logic ---
  btnSubmit.addEventListener('click', async () => {
    const promptText = promptInput.value.trim();
    if (!promptText) {
      alert("Please enter a prompt describing what to generate in the painted mask area.");
      promptInput.focus();
      return;
    }

    setStatus("Compositing mask and submitting job...", true);

    try {
      // Create pure black/white mask canvas for submission (white = masked area)
      const submitMaskCanvas = document.createElement('canvas');
      submitMaskCanvas.width = imgWidth;
      submitMaskCanvas.height = imgHeight;
      const sCtx = submitMaskCanvas.getContext('2d');

      // Fill black background
      sCtx.fillStyle = 'black';
      sCtx.fillRect(0, 0, imgWidth, imgHeight);

      // Draw mask in white
      const currentMaskData = maskCtx.getImageData(0, 0, imgWidth, imgHeight);
      const maskPixels = currentMaskData.data;
      const whiteMaskData = sCtx.createImageData(imgWidth, imgHeight);

      for (let i = 0; i < maskPixels.length; i += 4) {
        const alpha = maskPixels[i + 3];
        if (alpha > 0) {
          whiteMaskData.data[i] = 255;     // R
          whiteMaskData.data[i + 1] = 255; // G
          whiteMaskData.data[i + 2] = 255; // B
          whiteMaskData.data[i + 3] = alpha; // A
        }
      }
      sCtx.putImageData(whiteMaskData, 0, 0);

      // Convert mask to Data URL
      const maskDataUrl = submitMaskCanvas.toDataURL('image/png');

      // POST to backend API
      const response = await fetch('/api/inpaint/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: sessionToken,
          prompt: promptText,
          mask_data_url: maskDataUrl
        })
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Submission failed");
      }

      setStatus("🎉 Inpaint submitted successfully! Closing window...", false);

      setTimeout(() => {
        try { window.close(); } catch(e) {}
      }, 1200);

    } catch (err) {
      console.error("Submit error:", err);
      setStatus(`❌ Error: ${err.message}`, false);
      setTimeout(() => hideStatus(), 3000);
    }
  });
})();
