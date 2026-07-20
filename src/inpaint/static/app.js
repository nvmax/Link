// LINK Inpaint Studio — Canvas Application Logic

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
  const stack = document.getElementById('canvas-stack');
  const bgCanvas = document.getElementById('bg-canvas');
  const maskCanvas = document.getElementById('mask-canvas');
  const cursorCanvas = document.getElementById('cursor-canvas');

  const bgCtx = bgCanvas.getContext('2d');
  const maskCtx = maskCanvas.getContext('2d');
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
  [bgCanvas, maskCanvas, cursorCanvas].forEach(c => {
    c.width = imgWidth;
    c.height = imgHeight;
  });

  // Draw background image
  bgCtx.drawImage(img, 0, 0, imgWidth, imgHeight);

  // Setup stack dimensions in container
  const viewport = document.getElementById('viewport');
  const maxW = viewport.clientWidth - 40;
  const maxH = viewport.clientHeight - 40;
  const scale = Math.min(maxW / imgWidth, maxH / imgHeight, 1.0);

  const displayW = Math.round(imgWidth * scale);
  const displayH = Math.round(imgHeight * scale);

  stack.style.width = `${displayW}px`;
  stack.style.height = `${displayH}px`;

  hideStatus();

  // --- Drawing State ---
  let mode = 'brush'; // 'brush' | 'eraser'
  let shape = 'circle'; // 'circle' | 'square' | 'soft'
  let brushSize = 40;
  let brushOpacity = 1.0; // 0.1 to 1.0
  let overlayOpacity = 0.65; // 0.1 to 1.0
  let isDrawing = false;
  let lastX = 0;
  let lastY = 0;
  let isMaskVisible = true;

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
  const btnShapeCircle = document.getElementById('btn-shape-circle');
  const btnShapeSquare = document.getElementById('btn-shape-square');
  const btnShapeSoft = document.getElementById('btn-shape-soft');
  const sizeSlider = document.getElementById('size-slider');
  const sizeVal = document.getElementById('size-val');
  const opacitySlider = document.getElementById('opacity-slider');
  const opacityVal = document.getElementById('opacity-val');
  const overlaySlider = document.getElementById('overlay-slider');
  const overlayVal = document.getElementById('overlay-val');
  const btnUndo = document.getElementById('btn-undo');
  const btnRedo = document.getElementById('btn-redo');
  const btnToggleMask = document.getElementById('btn-toggle-mask');
  const btnClear = document.getElementById('btn-clear');
  const btnSubmit = document.getElementById('btn-submit');

  btnBrush.addEventListener('click', () => {
    mode = 'brush';
    btnBrush.classList.add('active');
    btnEraser.classList.remove('active');
  });

  btnEraser.addEventListener('click', () => {
    mode = 'eraser';
    btnEraser.classList.add('active');
    btnBrush.classList.remove('active');
  });

  function setShape(s, btn) {
    shape = s;
    [btnShapeCircle, btnShapeSquare, btnShapeSoft].forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }

  btnShapeCircle.addEventListener('click', () => setShape('circle', btnShapeCircle));
  btnShapeSquare.addEventListener('click', () => setShape('square', btnShapeSquare));
  btnShapeSoft.addEventListener('click', () => setShape('soft', btnShapeSoft));

  sizeSlider.addEventListener('input', (e) => {
    brushSize = parseInt(e.target.value, 10);
    sizeVal.textContent = `${brushSize}px`;
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

  // --- Drawing Logic ---
  function getCanvasCoords(e) {
    const rect = stack.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    const x = Math.round((clientX - rect.left) * (imgWidth / rect.width));
    const y = Math.round((clientY - rect.top) * (imgHeight / rect.height));
    return { x, y };
  }

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
    if (x < 0 || x > imgWidth || y < 0 || y > imgHeight) return;

    cursorCtx.save();
    cursorCtx.strokeStyle = mode === 'eraser' ? '#ef4444' : '#ffffff';
    cursorCtx.lineWidth = 2;
    const r = brushSize / 2;

    if (shape === 'square') {
      cursorCtx.strokeRect(x - r, y - r, brushSize, brushSize);
    } else {
      cursorCtx.beginPath();
      cursorCtx.arc(x, y, r, 0, Math.PI * 2);
      cursorCtx.stroke();
    }
    cursorCtx.restore();
  }

  // Pointer Events
  stack.addEventListener('pointerdown', (e) => {
    isDrawing = true;
    saveState();
    const { x, y } = getCanvasCoords(e);
    lastX = x;
    lastY = y;
    drawStamp(x, y);
  });

  window.addEventListener('pointermove', (e) => {
    const { x, y } = getCanvasCoords(e);
    renderCursor(x, y);
    if (!isDrawing) return;
    drawLine(lastX, lastY, x, y);
    lastX = x;
    lastY = y;
  });

  window.addEventListener('pointerup', () => {
    if (isDrawing) {
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
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = imgWidth;
      tempCanvas.height = imgHeight;
      const tCtx = tempCanvas.getContext('2d');
      tCtx.putImageData(currentMaskData, 0, 0);

      // Use source-over with white fill
      sCtx.globalCompositeOperation = 'source-over';
      // Create a white silhouette of the mask alpha channel
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

      // Close the browser window / tab
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
