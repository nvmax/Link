// LINK YuE2 Music Studio — Advanced Digital Audio Workstation Application Logic

(async function () {
  // --- DOM References ---
  const inputSongTitle = document.getElementById('input-song-title');
  const selectGenre = document.getElementById('select-genre');
  const genreQuickChips = document.getElementById('genre-quick-chips');
  const selectVocal = document.getElementById('select-vocal');
  const bpmSlider = document.getElementById('bpm-slider');
  const bpmVal = document.getElementById('bpm-val');
  const btnTapTempo = document.getElementById('btn-tap-tempo');
  const tempoChips = document.querySelectorAll('.tempo-chip');
  const selectIntro = document.getElementById('select-intro');
  const inputCustomStyle = document.getElementById('input-custom-style');
  const selectAction = document.getElementById('select-action');
  
  const btnToggleAdvanced = document.getElementById('btn-toggle-advanced');
  const advancedDrawer = document.getElementById('advanced-drawer');
  const checkRandomSeed = document.getElementById('check-random-seed');
  const seedInputRow = document.getElementById('seed-input-row');
  const inputSeed = document.getElementById('input-seed');
  const checkDirectLyrics = document.getElementById('check-direct-lyrics');
  const selectOdeSteps = document.getElementById('select-ode-steps');

  const editorLyrics = document.getElementById('editor-lyrics');
  const lyricsCharCount = document.getElementById('lyrics-char-count');
  const btnCopyLyrics = document.getElementById('btn-copy-lyrics');
  const btnClearLyrics = document.getElementById('btn-clear-lyrics');
  const tagButtons = document.querySelectorAll('.tag-btn');

  const tabLyrics = document.getElementById('tab-lyrics');
  const tabNode14 = document.getElementById('tab-node14');
  const viewLyrics = document.getElementById('view-lyrics');
  const viewNode14 = document.getElementById('view-node14');
  const node14Badge = document.getElementById('node14-badge');
  const node14TextDisplay = document.getElementById('node14-text-display');
  const btnApplyToEditor = document.getElementById('btn-apply-to-editor');

  const btnGenerateLyrics = document.getElementById('btn-generate-lyrics');
  const btnGenerateSong = document.getElementById('btn-generate-song');

  const progressOverlay = document.getElementById('progress-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalDesc = document.getElementById('modal-desc');
  const progressFill = document.getElementById('progress-fill');
  const progressStageText = document.getElementById('progress-stage-text');
  const progressPercentText = document.getElementById('progress-percent-text');
  const btnDismissOverlay = document.getElementById('btn-dismiss-overlay');

  const stepLlm = document.getElementById('step-llm');
  const stepSynth = document.getElementById('step-synth');
  const stepExport = document.getElementById('step-export');

  const badgeComfy = document.getElementById('badge-comfy');
  const statusComfyText = document.getElementById('status-comfy-text');
  const badgeLlm = document.getElementById('badge-llm');
  const statusLlmText = document.getElementById('status-llm-text');

  // Player DOM
  const nativeAudio = document.getElementById('native-audio');
  const btnPlayPause = document.getElementById('btn-play-pause');
  const playIcon = document.getElementById('play-icon');
  const playerSeek = document.getElementById('player-seek');
  const playerVol = document.getElementById('player-vol');
  const playerTimeCurrent = document.getElementById('player-time-current');
  const playerTimeTotal = document.getElementById('player-time-total');
  const waveformCanvas = document.getElementById('waveform-canvas');
  const playbackScrubber = document.getElementById('playback-scrubber');
  const btnDownloadAudio = document.getElementById('btn-download-audio');
  const btnCopyAudioLink = document.getElementById('btn-copy-audio-link');
  const trackTitle = document.getElementById('track-title');

  const toast = document.getElementById('toast');
  const toastMessage = document.getElementById('toast-message');

  // --- State Variables ---
  const urlParams = new URLSearchParams(window.location.search);
  const sessionToken = urlParams.get('token');
  let currentAudioUrl = null;
  let tapTimestamps = [];
  let pollInterval = null;
  let audioContext = null;
  let audioBuffer = null;

  function showToast(msg, duration = 3000) {
    toastMessage.textContent = msg;
    toast.classList.remove('hidden');
    setTimeout(() => {
      toast.classList.add('hidden');
    }, duration);
  }

  function updateCharCount() {
    const text = editorLyrics.value || '';
    const chars = text.length;
    const lines = text ? text.split('\n').length : 0;
    lyricsCharCount.textContent = `${chars.toLocaleString()} characters | ${lines} lines`;
  }

  // --- Initial Data Load ---
  async function initStudio() {
    try {
      const res = await fetch('/api/music/options');
      if (!res.ok) throw new Error("Failed to load options");
      const data = await res.json();

      // Update monitor badges
      if (data.comfy_connected) {
        badgeComfy.querySelector('.indicator-dot').className = 'indicator-dot online';
        statusComfyText.textContent = "Online";
      } else {
        badgeComfy.querySelector('.indicator-dot').className = 'indicator-dot offline';
        statusComfyText.textContent = "Offline";
      }

      if (data.lmstudio_connected) {
        badgeLlm.querySelector('.indicator-dot').className = 'indicator-dot online';
        statusLlmText.textContent = data.lm_model ? `Online (${data.lm_model})` : "Online";
        badgeLlm.title = `Connected to ${data.lm_base_url || 'LM Studio'}`;
      } else {
        badgeLlm.querySelector('.indicator-dot').className = 'indicator-dot offline';
        statusLlmText.textContent = "Offline";
        badgeLlm.title = `Cannot reach LM Studio at ${data.lm_base_url || 'port 1234'}`;
      }

      // Populate Genres
      selectGenre.innerHTML = '';
      data.genre_presets.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g;
        opt.textContent = g;
        if (g === data.default_genre) opt.selected = true;
        selectGenre.appendChild(opt);
      });

      // Populate Quick Chips
      const featuredChips = [
        "Custom / Keep Only Lyrics",
        "Pop / Dance Pop",
        "Pop / Pop Funk",
        "Rock / Classic Rock",
        "Ballad / Power Ballad",
        "Hip-Hop / Rap",
        "Synthwave / Retro 80s Electro",
        "EDM / Melodic Progressive House",
        "R&B / Neo-Soul",
        "Metal / Heavy Metal"
      ];
      genreQuickChips.innerHTML = '';
      featuredChips.forEach(chipName => {
        const btn = document.createElement('button');
        btn.className = 'chip' + (chipName === data.default_genre ? ' active' : '');
        btn.textContent = chipName.split('/')[1] ? chipName.split('/')[1].trim() : chipName;
        btn.addEventListener('click', () => {
          selectGenre.value = chipName;
          document.querySelectorAll('#genre-quick-chips .chip').forEach(c => c.classList.remove('active'));
          btn.classList.add('active');
        });
        genreQuickChips.appendChild(btn);
      });

      // Populate Vocal Profiles
      selectVocal.innerHTML = '';
      data.vocal_profiles.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        if (v === data.default_vocal) opt.selected = true;
        selectVocal.appendChild(opt);
      });

      // Populate Intro Styles
      selectIntro.innerHTML = '';
      data.intro_styles.forEach(i => {
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = i;
        if (i === data.default_intro) opt.selected = true;
        selectIntro.appendChild(opt);
      });

      // Populate Actions
      selectAction.innerHTML = '';
      data.actions.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a;
        opt.textContent = a;
        if (a === data.default_action) opt.selected = true;
        selectAction.appendChild(opt);
      });

      // Set defaults
      bpmSlider.value = data.bpm_default || 120;
      bpmVal.textContent = data.bpm_default || 120;
      inputCustomStyle.value = data.default_custom_style || "Style of Bruno Mars song Risk It All";
      editorLyrics.value = data.default_lyrics || "";
      updateCharCount();

      // Check for Discord Session
      if (sessionToken) {
        loadDiscordSession(sessionToken);
      }

    } catch (e) {
      console.error("Init studio error:", e);
      showToast("Could not connect to studio server. Please verify backend is running.");
    }
  }

  async function loadDiscordSession(token) {
    try {
      const res = await fetch(`/api/music/session/${token}`);
      if (res.ok) {
        const s = await res.json();
        if (s.song_title && inputSongTitle) inputSongTitle.value = s.song_title;
        if (s.genre_preset) selectGenre.value = s.genre_preset;
        if (s.vocal_profile) selectVocal.value = s.vocal_profile;
        if (s.bpm) {
          bpmSlider.value = s.bpm;
          bpmVal.textContent = s.bpm;
        }
        if (s.intro_style) selectIntro.value = s.intro_style;
        if (s.custom_style) inputCustomStyle.value = s.custom_style;
        if (s.lyrics) editorLyrics.value = s.lyrics;
        if (s.action) selectAction.value = s.action;
        updateCharCount();
        showToast(`Loaded Discord session for ${s.user_name || 'User'}`);
        if (s.audio_url) {
          loadAudioTrack(s.audio_url, s.song_title || "Discord Session Track");
        }
      }
    } catch (e) {
      console.warn("Discord session fetch error:", e);
    }
  }

  // --- Tempo / BPM Controls ---
  bpmSlider.addEventListener('input', (e) => {
    bpmVal.textContent = e.target.value;
    updateActiveTempoChip(parseInt(e.target.value));
  });

  tempoChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const val = parseInt(chip.dataset.bpm);
      bpmSlider.value = val;
      bpmVal.textContent = val;
      updateActiveTempoChip(val);
    });
  });

  function updateActiveTempoChip(val) {
    tempoChips.forEach(c => {
      if (parseInt(c.dataset.bpm) === val) c.classList.add('active');
      else c.classList.remove('active');
    });
  }

  // Tap Tempo
  btnTapTempo.addEventListener('click', () => {
    const now = Date.now();
    tapTimestamps.push(now);
    if (tapTimestamps.length > 5) tapTimestamps.shift();

    if (tapTimestamps.length >= 2) {
      const diffs = [];
      for (let i = 1; i < tapTimestamps.length; i++) {
        const diff = tapTimestamps[i] - tapTimestamps[i - 1];
        if (diff > 2500) {
          tapTimestamps = [now];
          return;
        }
        diffs.push(diff);
      }
      const avgMs = diffs.reduce((a, b) => a + b, 0) / diffs.length;
      let calculatedBpm = Math.round(60000 / avgMs);
      calculatedBpm = Math.max(40, Math.min(240, calculatedBpm));
      bpmSlider.value = calculatedBpm;
      bpmVal.textContent = calculatedBpm;
      updateActiveTempoChip(calculatedBpm);
    }
  });

  // Advanced Drawer Toggle
  btnToggleAdvanced.addEventListener('click', () => {
    const isCollapsed = advancedDrawer.classList.contains('collapsed');
    advancedDrawer.classList.toggle('collapsed');
    btnToggleAdvanced.querySelector('.accordion-arrow').textContent = isCollapsed ? '▲' : '▼';
  });

  checkRandomSeed.addEventListener('change', (e) => {
    seedInputRow.style.display = e.target.checked ? 'none' : 'flex';
  });

  // --- Tag Insertion in Lyrics Editor ---
  tagButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tag = btn.dataset.tag;
      insertTextAtCursor(editorLyrics, `\n${tag}\n`);
      updateCharCount();
    });
  });

  function insertTextAtCursor(textarea, textToInsert) {
    const startPos = textarea.selectionStart;
    const endPos = textarea.selectionEnd;
    const currentVal = textarea.value;
    textarea.value = currentVal.substring(0, startPos) + textToInsert + currentVal.substring(endPos);
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = startPos + textToInsert.length;
  }

  editorLyrics.addEventListener('input', updateCharCount);

  btnCopyLyrics.addEventListener('click', () => {
    if (!editorLyrics.value) return;
    navigator.clipboard.writeText(editorLyrics.value).then(() => {
      showToast("📋 Lyrics copied to clipboard!");
    });
  });

  btnClearLyrics.addEventListener('click', () => {
    if (confirm("Reset lyrics editor to default template?")) {
      initStudio();
    }
  });

  // --- Tab Switching (Editor vs Node 14) ---
  tabLyrics.addEventListener('click', () => {
    tabLyrics.classList.add('active');
    tabNode14.classList.remove('active');
    viewLyrics.classList.remove('hidden');
    viewNode14.classList.add('hidden');
  });

  tabNode14.addEventListener('click', () => {
    tabNode14.classList.add('active');
    tabLyrics.classList.remove('active');
    viewNode14.classList.remove('hidden');
    viewLyrics.classList.add('hidden');
  });

  btnApplyToEditor.addEventListener('click', () => {
    const rawText = node14TextDisplay.textContent;
    if (!rawText || rawText.startsWith("No lyrics generated")) {
      showToast("No generated lyrics available to apply.");
      return;
    }
    editorLyrics.value = rawText;
    updateCharCount();
    tabLyrics.click();
    showToast("✍️ Applied Node 14 lyrics to editor!");
  });

  // --- Modal Progress Overlay Helpers ---
  function showProgressModal(title, desc) {
    modalTitle.textContent = title;
    modalDesc.textContent = desc;
    progressFill.style.width = '10%';
    progressStageText.textContent = "Initializing...";
    progressPercentText.textContent = "10%";
    btnDismissOverlay.classList.add('hidden');
    progressOverlay.classList.remove('hidden');
    btnGenerateLyrics.disabled = true;
    btnGenerateSong.disabled = true;
  }

  function updateProgressModal(percent, stageText, desc) {
    progressFill.style.width = `${percent}%`;
    progressPercentText.textContent = `${percent}%`;
    progressStageText.textContent = stageText;
    if (desc) modalDesc.textContent = desc;

    // Step indicators
    if (percent < 35) {
      stepLlm.className = 'pipeline-step active';
      stepSynth.className = 'pipeline-step';
      stepExport.className = 'pipeline-step';
    } else if (percent < 90) {
      stepLlm.className = 'pipeline-step';
      stepSynth.className = 'pipeline-step active';
      stepExport.className = 'pipeline-step';
    } else {
      stepLlm.className = 'pipeline-step';
      stepSynth.className = 'pipeline-step';
      stepExport.className = 'pipeline-step active';
    }
  }

  function hideProgressModal() {
    progressOverlay.classList.add('hidden');
    btnGenerateLyrics.disabled = false;
    btnGenerateSong.disabled = false;
  }

  btnDismissOverlay.addEventListener('click', hideProgressModal);

  // ==========================================================================
  // BUTTON 1: ✨ GENERATE LYRICS ONLY (Disables Node 5)
  // ==========================================================================
  btnGenerateLyrics.addEventListener('click', async () => {
    const titleInput = document.getElementById('input-song-title') || inputSongTitle;
    const songTitleVal = titleInput ? titleInput.value.trim() : "";
    const payload = {
      token: sessionToken,
      song_title: songTitleVal,
      genre_preset: selectGenre.value,
      vocal_profile: selectVocal.value,
      bpm: parseInt(bpmSlider.value),
      intro_style: selectIntro.value,
      custom_style: inputCustomStyle.value,
      lyrics: editorLyrics.value,
      action: selectAction.value
    };

    showProgressModal(
      "Co-Producing Lyrics...",
      "Executing Node 1 (Studio) & Node 3 (LLM Co-Producer). Node 5 Neural Audio is DISABLED."
    );
    updateProgressModal(25, "Reasoning & Arranging...", "LM Studio (gemma-4-e4b-it) is analyzing your concept and lyrics structure...");

    try {
      const res = await fetch('/api/music/lyrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || "Lyrics generation failed");
      }

      const result = await res.json();
      const generatedLyrics = result.lyrics;

      updateProgressModal(100, "Lyrics Complete!", "Node 14 captured full output lyrics.");
      
      // Update Node 14 viewer
      node14TextDisplay.textContent = generatedLyrics;
      node14Badge.textContent = "New!";
      node14Badge.style.background = "rgba(16, 185, 129, 0.2)";
      node14Badge.style.color = "#10b981";

      // Also update editor and switch to Node 14 tab so user can review immediately
      editorLyrics.value = generatedLyrics;
      updateCharCount();
      tabNode14.click();

      setTimeout(() => {
        hideProgressModal();
        showToast("✨ Lyrics generated successfully and loaded into editor!");
      }, 700);

    } catch (e) {
      console.error("Lyrics generation error:", e);
      alert(`Lyrics generation error: ${e.message}`);
      hideProgressModal();
    }
  });

  // ==========================================================================
  // BUTTON 2: 🚀 GENERATE FINAL SONG (Runs Full Workflow)
  // ==========================================================================
  btnGenerateSong.addEventListener('click', async () => {
    let seedVal = null;
    if (!checkRandomSeed.checked && inputSeed.value) {
      seedVal = parseInt(inputSeed.value);
    }

    const titleInput = document.getElementById('input-song-title') || inputSongTitle;
    const songTitleVal = titleInput ? titleInput.value.trim() : "";
    console.log("[YuE2 Studio] Submitting song generation with title:", songTitleVal);

    const payload = {
      token: sessionToken,
      song_title: songTitleVal,
      genre_preset: selectGenre.value,
      vocal_profile: selectVocal.value,
      bpm: parseInt(bpmSlider.value),
      intro_style: selectIntro.value,
      custom_style: inputCustomStyle.value,
      lyrics: editorLyrics.value,
      action: selectAction.value,
      direct_lyrics: checkDirectLyrics.checked,
      seed: seedVal,
      ode_steps: parseInt(selectOdeSteps.value) || 24
    };

    showProgressModal(
      "Producing Full Studio Track...",
      "Running complete YuE2 pipeline: Node 1 -> Node 3 -> Node 5 (Neural Generator) -> Node 6 (Audio Saver)."
    );
    updateProgressModal(10, "Submitting to ComfyUI...", "Queuing prompt and reserving GPU memory...");

    try {
      const res = await fetch('/api/music/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || "Song generation failed");
      }

      const initResult = await res.json();
      const promptId = initResult.prompt_id;
      console.log("Song generation queued:", promptId);

      // Start polling for progress & completion
      pollSongProgress(promptId);

    } catch (e) {
      console.error("Song generation error:", e);
      alert(`Song generation error: ${e.message}`);
      hideProgressModal();
    }
  });

  function pollSongProgress(promptId) {
    if (pollInterval) clearInterval(pollInterval);
    let pollCount = 0;

    pollInterval = setInterval(async () => {
      pollCount++;
      try {
        const res = await fetch(`/api/music/status/${promptId}`);
        if (!res.ok) return;
        const info = await res.json();

        if (info.stage === "completed") {
          clearInterval(pollInterval);
          updateProgressModal(100, "Master Audio Ready!", "Synthesized 24-bit studio MP3 output.");
          
          if (info.lyrics) {
            node14TextDisplay.textContent = info.lyrics;
            node14Badge.textContent = "Final";
          }

          if (info.audio_url) {
            const trackName = info.song_title || (inputSongTitle && inputSongTitle.value.trim()) || info.clean_title || "YuE2 Studio Master Track";
            loadAudioTrack(info.audio_url, trackName, info.clean_title);
          }

          setTimeout(() => {
            hideProgressModal();
            showToast("🚀 Master song generated and ready to play!");
          }, 800);
          return;
        }

        if (info.stage === "failed") {
          clearInterval(pollInterval);
          hideProgressModal();
          alert(`Song generation failed: ${info.status || info.error}`);
          return;
        }

        // Incremental visual progress during long synthesis
        let simulatedPercent = Math.min(88, 15 + pollCount * 3);
        updateProgressModal(
          simulatedPercent,
          info.status || "YuE2 ODE Neural Diffusion in progress...",
          `Synthesizing vocal harmony and instrument stems (${pollCount * 2}s elapsed)...`
        );

      } catch (err) {
        console.warn("Poll status error:", err);
      }
    }, 2000);
  }

  // ==========================================================================
  // MASTER AUDIO PLAYER & WAVEFORM VISUALIZER
  // ==========================================================================
  let currentDownloadFilename = "YuE2_Studio_Master_Track.mp3";

  function loadAudioTrack(audioUrl, title = "Master Track", downloadName = null) {
    currentAudioUrl = audioUrl;
    trackTitle.textContent = title;
    
    if (downloadName) {
      currentDownloadFilename = downloadName.endsWith('.mp3') ? downloadName : `${downloadName}.mp3`;
    } else {
      const sanitized = title.replace(/[^\w\s-]/g, '').trim().replace(/[-\s]+/g, '_');
      currentDownloadFilename = `${sanitized || 'YuE2_Studio_Master_Track'}.mp3`;
    }

    nativeAudio.src = audioUrl;

    btnPlayPause.disabled = false;
    playerSeek.disabled = false;
    btnDownloadAudio.disabled = false;
    btnCopyAudioLink.disabled = false;

    // Draw initial waveform
    drawWaveformCanvas();

    // Auto-play
    nativeAudio.play().then(() => {
      playIcon.textContent = "⏸";
    }).catch(e => {
      console.log("Autoplay prevented:", e);
      playIcon.textContent = "▶";
    });
  }

  btnPlayPause.addEventListener('click', () => {
    if (nativeAudio.paused) {
      nativeAudio.play();
      playIcon.textContent = "⏸";
    } else {
      nativeAudio.pause();
      playIcon.textContent = "▶";
    }
  });

  nativeAudio.addEventListener('ended', () => {
    playIcon.textContent = "▶";
    playbackScrubber.style.left = "0%";
    playerSeek.value = 0;
  });

  nativeAudio.addEventListener('timeupdate', () => {
    if (!nativeAudio.duration) return;
    const progress = (nativeAudio.currentTime / nativeAudio.duration) * 100;
    playerSeek.value = progress;
    playbackScrubber.style.left = `${progress}%`;
    playerTimeCurrent.textContent = formatTime(nativeAudio.currentTime);
  });

  nativeAudio.addEventListener('loadedmetadata', () => {
    playerTimeTotal.textContent = formatTime(nativeAudio.duration);
    drawWaveformCanvas();
  });

  playerSeek.addEventListener('input', (e) => {
    if (!nativeAudio.duration) return;
    const targetTime = (e.target.value / 100) * nativeAudio.duration;
    nativeAudio.currentTime = targetTime;
  });

  playerVol.addEventListener('input', (e) => {
    nativeAudio.volume = parseFloat(e.target.value);
  });

  btnDownloadAudio.addEventListener('click', () => {
    if (!currentAudioUrl) return;
    const a = document.createElement('a');
    a.href = currentAudioUrl;
    a.download = currentDownloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  });

  btnCopyAudioLink.addEventListener('click', () => {
    if (!currentAudioUrl) return;
    const fullUrl = window.location.origin + currentAudioUrl;
    navigator.clipboard.writeText(fullUrl).then(() => {
      showToast("🔗 Audio link copied to clipboard!");
    });
  });

  // Waveform Canvas Rendering
  function drawWaveformCanvas() {
    const ctx = waveformCanvas.getContext('2d');
    const width = waveformCanvas.parentElement.clientWidth;
    const height = waveformCanvas.parentElement.clientHeight;
    waveformCanvas.width = width;
    waveformCanvas.height = height;

    ctx.clearRect(0, 0, width, height);

    const bars = Math.floor(width / 4);
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, '#8b5cf6');
    grad.addColorStop(0.5, '#06b6d4');
    grad.addColorStop(1, '#3b82f6');

    ctx.fillStyle = grad;

    // Generate pseudo-waveform bars for sleek visual look
    for (let i = 0; i < bars; i++) {
      const x = i * 4;
      const seed = Math.sin(i * 0.15) * Math.cos(i * 0.08);
      const barHeight = Math.max(4, Math.abs(seed) * (height * 0.75));
      const y = (height - barHeight) / 2;
      ctx.fillRect(x, y, 2.5, barHeight);
    }
  }

  // Click on waveform canvas to seek
  waveformCanvas.addEventListener('click', (e) => {
    if (!nativeAudio.duration) return;
    const rect = waveformCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percent = clickX / rect.width;
    nativeAudio.currentTime = percent * nativeAudio.duration;
  });

  window.addEventListener('resize', () => {
    if (waveformCanvas) drawWaveformCanvas();
  });

  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  // Boot up studio
  initStudio();

})();
