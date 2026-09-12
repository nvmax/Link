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
  const selectModel = document.getElementById('select-model');
  const modelLiveIndicator = document.getElementById('model-live-indicator');
  
  const btnToggleAdvanced = document.getElementById('btn-toggle-advanced');
  const advancedDrawer = document.getElementById('advanced-drawer');
  const checkRandomSeed = document.getElementById('check-random-seed');
  const seedInputRow = document.getElementById('seed-input-row');
  const inputSeed = document.getElementById('input-seed');
  const checkDirectLyrics = document.getElementById('check-direct-lyrics');
  const selectCot = document.getElementById('select-cot');
  const selectOdeSteps = document.getElementById('select-ode-steps');

  const editorLyrics = document.getElementById('editor-lyrics');
  const lyricsCharCount = document.getElementById('lyrics-char-count');
  const btnCopyLyrics = document.getElementById('btn-copy-lyrics');
  const btnClearLyrics = document.getElementById('btn-clear-lyrics');

  const tabLyrics = document.getElementById('tab-lyrics');
  const tabNode14 = document.getElementById('tab-node14');
  const viewLyrics = document.getElementById('view-lyrics');
  const viewNode14 = document.getElementById('view-node14');
  const node14Badge = document.getElementById('node14-badge');
  const node14TextDisplay = document.getElementById('node14-text-display');
  const btnApplyToEditor = document.getElementById('btn-apply-to-editor');

  const btnGenerateLyrics = document.getElementById('btn-generate-lyrics');
  const btnGenerateSong = document.getElementById('btn-generate-song');
  const btnPushEditorSong = document.getElementById('btn-push-editor-song');

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

  // AI Co-Producer Revision DOM
  const revisionChatLog = document.getElementById('revision-chat-log');
  const inputRevisionPrompt = document.getElementById('input-revision-prompt');
  const btnSendRevision = document.getElementById('btn-send-revision');
  const chatTypingIndicator = document.getElementById('chat-typing-indicator');
  const btnClearChat = document.getElementById('btn-clear-chat');

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
        "Custom / Keep Typed Style",
        "Custom / Keep Only Lyrics",
        "Rock / Classic Rock",
        "Pop / Pop Funk",
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

      // Populate Live Models from LM Studio / ComfyUI
      if (selectModel) {
        selectModel.innerHTML = '';
        const modelsList = (data.lm_models && data.lm_models.length > 0) ? data.lm_models : [data.lm_model || "gemma-4-e4b-it"];
        modelsList.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m;
          opt.textContent = m;
          if (m === data.lm_model) opt.selected = true;
          selectModel.appendChild(opt);
        });
        if (modelLiveIndicator) {
          modelLiveIndicator.textContent = data.lm_models_live ? `Live (${modelsList.length} models)` : `Node 3: model`;
          if (data.lm_models_live) modelLiveIndicator.style.color = 'var(--accent-emerald)';
        }
        selectModel.addEventListener('change', () => {
          if (statusLlmText) {
            statusLlmText.textContent = selectModel.value ? `Online (${selectModel.value})` : "Online";
          }
          showToast(`Co-Producer model: ${selectModel.value}`);
        });
      }

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

    // Step indicators matching 3-stage studio pipeline
    if (percent < 20) {
      stepLlm.className = 'pipeline-step active';
      stepSynth.className = 'pipeline-step';
      stepExport.className = 'pipeline-step';
    } else if (percent < 93) {
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
      action: selectAction.value,
      model: selectModel ? selectModel.value : null
    };

    const activeModelName = (selectModel && selectModel.value) ? selectModel.value : "LLM Co-Producer";
    showProgressModal(
      "Co-Producing Lyrics...",
      `Executing Node 1 (Studio) & Node 3 (${activeModelName}). Node 5 Neural Audio is DISABLED.`
    );
    updateProgressModal(25, "Reasoning & Arranging...", `${activeModelName} is analyzing your concept and lyrics structure...`);

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

      // Update editor lyrics and keep focus on main lyrics sheet so user sees it live
      editorLyrics.value = generatedLyrics;
      updateCharCount();
      if (tabLyrics) tabLyrics.click();
      if (checkDirectLyrics) checkDirectLyrics.checked = true;

      // Visual flash on screen
      if (editorLyrics.parentElement) {
        editorLyrics.parentElement.classList.remove('live-updated-glow');
        void editorLyrics.parentElement.offsetWidth;
        editorLyrics.parentElement.classList.add('live-updated-glow');
        setTimeout(() => editorLyrics.parentElement.classList.remove('live-updated-glow'), 1900);
      }

      // Smart Song Title Auto-Population (if not already set by user)
      const titleInput = document.getElementById('input-song-title') || inputSongTitle;
      if (titleInput && !titleInput.value.trim() && result.suggested_title) {
        titleInput.value = result.suggested_title;
        console.log("[YuE2 Studio] Auto-populated song title with:", result.suggested_title);
      }

      // Add AI Co-Producer notification to revision console
      const activeTitle = (titleInput && titleInput.value.trim()) || "your track";
      appendChatBubble('ai', `Generated song lyrics for "${activeTitle}"! What would you like to refine? You can ask me to change a specific verse, add sections, or adjust themes.`, {
        changedSection: "Full Song Lyrics",
        allowPushToSong: true
      });

      setTimeout(() => {
        hideProgressModal();
        showToast("✨ Lyrics generated on screen! Ready for Co-Producer chat.");
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
  async function runSongGeneration() {
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
      direct_lyrics: true,
      seed: seedVal,
      cot: selectCot ? selectCot.value : "full",
      ode_steps: parseInt(selectOdeSteps.value) || 32
    };

    showProgressModal(
      "Producing Full Studio Track...",
      "Running complete YuE2 pipeline: Node 1 -> Node 16 (Native Neural Generator) -> Node 6 (Audio Saver)."
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
  }

  btnGenerateSong.addEventListener('click', runSongGeneration);
  if (btnPushEditorSong) btnPushEditorSong.addEventListener('click', runSongGeneration);

  function pollSongProgress(promptId) {
    if (pollInterval) clearInterval(pollInterval);
    let pollCount = 0;
    let lastPercent = 10;

    pollInterval = setInterval(async () => {
      pollCount++;
      try {
        const res = await fetch(`/api/music/status/${promptId}`);
        if (!res.ok) return;
        const info = await res.json();

        if (info.stage === "completed") {
          clearInterval(pollInterval);
          updateProgressModal(100, "Master Audio Ready!", "Synthesized 24-bit studio MP3 output dispatched to Discord.");
          
          if (info.lyrics) {
            node14TextDisplay.textContent = info.lyrics;
            node14Badge.textContent = "Final";
          }

          const trackName = info.song_title || (inputSongTitle && inputSongTitle.value.trim()) || "YuE2 Studio Master Track";
          appendChatBubble('ai', `🎉 Master audio for "${trackName}" has been generated and delivered directly to your Discord channel!`);

          setTimeout(() => {
            hideProgressModal();
            showToast("🚀 Master song generated and delivered to Discord!");
          }, 800);
          return;
        }

        if (info.stage === "failed") {
          clearInterval(pollInterval);
          hideProgressModal();
          alert(`Song generation failed: ${info.status || info.error}`);
          return;
        }

        // Determine accurate progress percentage
        let targetPercent = lastPercent;
        if (typeof info.percent === 'number' && info.percent > 0) {
          targetPercent = Math.max(lastPercent, info.percent);
        } else {
          // Asymptotic progress that smoothly approaches 93% over time without stalling at 88%
          const asymptotic = Math.round(12 + (81 * (1 - Math.exp(-pollCount / 30))));
          targetPercent = Math.max(lastPercent, Math.min(93, asymptotic));
        }
        lastPercent = targetPercent;

        // Dynamic status & description
        let stageLabel = info.status || "YuE2 ODE Neural Diffusion in progress...";
        let descLabel = `Synthesizing vocal harmony and instrument stems (${pollCount * 2}s elapsed)...`;
        if (info.current_step && info.total_steps) {
          const stepPct = Math.round((info.current_step / info.total_steps) * 100);
          stageLabel = `Neural Diffusion: Step ${info.current_step}/${info.total_steps} (${stepPct}%)`;
          descLabel = `ODE Step ${info.current_step} of ${info.total_steps} • Synthesizing vocal timbre and instrument layers (${pollCount * 2}s elapsed)...`;
        }

        updateProgressModal(targetPercent, stageLabel, descLabel);

      } catch (err) {
        console.warn("Poll status error:", err);
      }
    }, 2000);
  }

  // ==========================================================================
  // AI CO-PRODUCER LYRICS REVISION CHAT CONTROLLER
  // ==========================================================================
  function appendChatBubble(role, text, options = {}) {
    if (!revisionChatLog) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role === 'user' ? 'user-bubble' : 'ai-bubble'}`;
    
    const header = document.createElement('div');
    header.className = 'bubble-header';

    const sender = document.createElement('span');
    sender.className = 'bubble-sender';
    sender.textContent = role === 'user' ? 'You' : 'AI Co-Producer';
    header.appendChild(sender);

    if (role === 'ai') {
      const tag = document.createElement('span');
      tag.className = 'bubble-tag';
      tag.textContent = options.changedSection ? `✨ ${options.changedSection} on Screen` : 'Co-Producer';
      header.appendChild(tag);
    }
    bubble.appendChild(header);

    const body = document.createElement('div');
    body.className = 'bubble-text';
    body.innerHTML = text.replace(/\n/g, '<br>');
    bubble.appendChild(body);

    revisionChatLog.appendChild(bubble);
    revisionChatLog.scrollTop = revisionChatLog.scrollHeight;
  }

  async function submitRevision(customInstruction = null) {
    const text = (customInstruction || (inputRevisionPrompt ? inputRevisionPrompt.value : "")).trim();
    if (!text) {
      showToast("Please enter what you'd like changed in the lyrics.");
      return;
    }

    appendChatBubble('user', text);
    if (inputRevisionPrompt) {
      inputRevisionPrompt.value = "";
      inputRevisionPrompt.style.height = 'auto';
    }

    // Show animated typing indicator
    if (chatTypingIndicator) {
      chatTypingIndicator.classList.remove('hidden');
      if (revisionChatLog) revisionChatLog.scrollTop = revisionChatLog.scrollHeight;
    }

    if (btnSendRevision) btnSendRevision.disabled = true;

    try {
      const titleInput = document.getElementById('input-song-title') || inputSongTitle;
      const payload = {
        instruction: text,
        current_lyrics: editorLyrics ? editorLyrics.value : "",
        song_title: titleInput ? titleInput.value.trim() : "",
        genre_preset: selectGenre.value,
        vocal_profile: selectVocal.value,
        bpm: parseInt(bpmSlider.value),
        custom_style: inputCustomStyle.value,
        model: selectModel ? selectModel.value : null
      };

      const res = await fetch('/api/music/revise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || "Revision request failed");
      }

      const data = await res.json();
      if (data.revised_lyrics && editorLyrics) {
        editorLyrics.value = data.revised_lyrics;
        updateCharCount();

        // Flash visual live update glow on lyrics sheet above
        if (editorLyrics.parentElement) {
          editorLyrics.parentElement.classList.remove('live-updated-glow');
          void editorLyrics.parentElement.offsetWidth;
          editorLyrics.parentElement.classList.add('live-updated-glow');
          setTimeout(() => editorLyrics.parentElement.classList.remove('live-updated-glow'), 1900);
        }
      }

      // Smart Song Title Auto-Population if currently empty
      if (titleInput && !titleInput.value.trim() && data.suggested_title) {
        titleInput.value = data.suggested_title;
        showToast(`💡 Title suggested: "${data.suggested_title}"`);
      }

      const note = data.producer_note || "Lyrics updated on screen!";
      appendChatBubble('ai', note, {
        changedSection: data.changed_section || "Updated Section"
      });
      showToast("✨ Lyrics updated on screen!");

    } catch (err) {
      console.error("Revision error:", err);
      appendChatBubble('ai', `⚠️ Revision error: ${err.message}`);
      showToast(`⚠️ Revision error: ${err.message}`);
    } finally {
      if (chatTypingIndicator) chatTypingIndicator.classList.add('hidden');
      if (btnSendRevision) btnSendRevision.disabled = false;
      if (revisionChatLog) revisionChatLog.scrollTop = revisionChatLog.scrollHeight;
    }
  }

  // Bind Send Button and Enter Key
  if (btnSendRevision) {
    btnSendRevision.addEventListener('click', () => submitRevision());
  }

  if (inputRevisionPrompt) {
    inputRevisionPrompt.addEventListener('input', () => {
      inputRevisionPrompt.style.height = 'auto';
      inputRevisionPrompt.style.height = Math.min(inputRevisionPrompt.scrollHeight, 100) + 'px';
    });

    inputRevisionPrompt.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitRevision();
      }
    });
  }

  // Bind Clear Chat Button
  if (btnClearChat) {
    btnClearChat.addEventListener('click', () => {
      if (revisionChatLog) {
        revisionChatLog.innerHTML = `
          <div class="chat-bubble ai-bubble welcome-card">
            <div class="bubble-header">
              <span class="bubble-sender">AI Co-Producer</span>
              <span class="bubble-tag">Ready</span>
            </div>
            <div class="bubble-text">
              👋 Chat cleared. Ready for your next lyric instruction!<br><br>
              Tell me what you'd like changed in the lyrics above and I will update them directly on screen.
            </div>
          </div>
        `;
        showToast("💬 Chat cleared.");
      }
    });
  }

  // Boot up studio
  initStudio();

})();
