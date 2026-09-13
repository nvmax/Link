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

  // Master Audio Transport DOM
  const masterPlayerBar = document.getElementById('master-player-bar');
  const playerTakeBadge = document.getElementById('player-take-badge');
  const playerTrackTitle = document.getElementById('player-track-title');
  const playerTrackSubtitle = document.getElementById('player-track-subtitle');
  const btnPlayerPlay = document.getElementById('btn-player-play');
  const playerPlayIcon = document.getElementById('player-play-icon');
  const playerTimeCurrent = document.getElementById('player-time-current');
  const playerTimeDuration = document.getElementById('player-time-duration');
  const playerTimeline = document.getElementById('player-timeline');
  const playerVolume = document.getElementById('player-volume');
  const btnPlayerDownload = document.getElementById('btn-player-download');
  const btnRegenerateTake = document.getElementById('btn-regenerate-take');
  const audioMaster = document.getElementById('audio-master');
  let currentTake = 1;

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

  // --- Music Studio Preset Fallbacks ---
  const FALLBACK_GENRES = [
    "Custom / Keep Typed Style", "Custom / Keep Only Lyrics", "Rock / Classic Rock", "Rock / Indie Rock",
    "Rock / Arena Rock", "Pop / Pop Funk", "Pop / Indie Pop", "Pop / Dance Pop", "Ballad / Power Ballad",
    "Country / Modern Country", "Country / Country Pop", "Country / Country Americana", "Country / Outlaw Country",
    "Hip-Hop / Rap", "Hip-Hop / Trap", "Hip-Hop / Conscious Rap", "Hip-Hop / Melodic Rap", "Hip-Hop / West Coast",
    "Hip-Hop / Golden Age 90s", "Cinematic / Epic Orchestral", "R&B / Neo-Soul", "Alternative / 90s Alternative",
    "Lo-Fi / Chillhop", "Metal / Heavy Metal", "Metal / Thrash Metal", "Metal / Symphonic Metal",
    "Grunge / 90s Seattle Sound", "Britpop / 90s UK Anthem", "College Rock / 80s-90s Jangle",
    "Synthwave / Retro 80s Electro", "EDM / Melodic Progressive House", "Jazz / Modern Smooth Jazz",
    "Folk / Acoustic Indie Folk", "Reggae / Modern Dub Pop", "Punk / High-Energy Pop Punk"
  ];

  const FALLBACK_VOCALS = [
    "Warm Smooth Baritone (Male)", "Bright Soaring Tenor (Male)", "Deep Resonant Bass (Male)",
    "Airy Crystalline Soprano (Female)", "Velvety Mezzo-Soprano (Female)", "Smoky Deep Alto (Female)",
    "Male & Female Duet (Baritone + Soprano)", "Male Trio Harmonies (Tenor Lead + Backing)",
    "Female Pop Harmony Group", "Emotional Ballad Duo", "None / Pure Instrumental"
  ];

  const FALLBACK_INTROS = [
    "None", "Instrumental Intro", "Vamp / Groove Intro", "Vocal/Lyrical Hook Intro",
    "Vocal / Lyrical Hook Intro", "Turnaround Intro", "Stand-Alone Instrumental",
    'The "Cold Start" (No Intro / Attacca)', "Acapella Intro", "Drone / Ambient Pad Intro",
    "Solo Instrument Feature", "Drum / Percussion Groove", "Count-In / Dialogue Intro",
    "SFX / Found Sound Intro", "Modulating Intro", "Crescendo / Fade-In Intro",
    "Ambient Nature Intro", "Immediate Vocal Entry (No Intro)"
  ];

  const FEATURED_CHIPS = [
    "Custom / Keep Typed Style", "Custom / Keep Only Lyrics", "Rock / Classic Rock",
    "Pop / Pop Funk", "Ballad / Power Ballad", "Hip-Hop / Rap",
    "Synthwave / Retro 80s Electro", "EDM / Melodic Progressive House",
    "R&B / Neo-Soul", "Metal / Heavy Metal"
  ];

  function populateSelect(selectEl, items, selectedVal) {
    if (!selectEl) return;
    const currentVal = selectedVal || selectEl.value;
    selectEl.innerHTML = '';
    items.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item;
      opt.textContent = item;
      if (item === currentVal) opt.selected = true;
      selectEl.appendChild(opt);
    });
    if (!selectEl.value && items.length > 0) {
      selectEl.value = items[0];
    }
  }

  function setupQuickChips(chipsList, activeVal) {
    if (!genreQuickChips) return;
    genreQuickChips.innerHTML = '';
    chipsList.forEach(chipName => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip' + (chipName === activeVal ? ' active' : '');
      btn.textContent = chipName.split('/')[1] ? chipName.split('/')[1].trim() : chipName;
      btn.dataset.genre = chipName;
      btn.addEventListener('click', () => {
        onGenrePresetSelected(chipName);
      });
      genreQuickChips.appendChild(btn);
    });
  }

  let isEnhancingPreset = false;
  async function enhanceLyricsWithPreset(genreName) {
    if (isEnhancingPreset) return;
    const currentText = editorLyrics ? editorLyrics.value.trim() : "";
    if (!currentText || currentText === "No lyrics generated yet.") return;

    isEnhancingPreset = true;
    const genreShort = genreName.split('/')[1] ? genreName.split('/')[1].trim() : genreName;
    showToast(`✨ Enhancing lyrics with ${genreShort} arrangement tags... (Your lyrics preserved)`, 3000);

    try {
      const titleInput = document.getElementById('input-song-title') || inputSongTitle;
      const payload = {
        token: sessionToken,
        song_title: titleInput ? titleInput.value.trim() : "",
        genre_preset: genreName,
        vocal_profile: selectVocal ? selectVocal.value : "Warm Smooth Baritone (Male)",
        bpm: parseInt(bpmSlider ? bpmSlider.value : 120),
        intro_style: selectIntro ? selectIntro.value : "None",
        custom_style: inputCustomStyle ? inputCustomStyle.value : "",
        lyrics: currentText,
        action: "Polish & Arrange Lyrics"
      };

      const res = await fetch('/api/music/lyrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) return;

      const result = await res.json();
      if (result.lyrics && editorLyrics) {
        editorLyrics.value = result.lyrics;
        updateCharCount();
        if (node14TextDisplay) {
          node14TextDisplay.textContent = result.lyrics;
        }

        if (editorLyrics.parentElement) {
          editorLyrics.parentElement.classList.remove('live-updated-glow');
          void editorLyrics.parentElement.offsetWidth;
          editorLyrics.parentElement.classList.add('live-updated-glow');
          setTimeout(() => editorLyrics.parentElement.classList.remove('live-updated-glow'), 1900);
        }

        if (titleInput && !titleInput.value.trim() && result.suggested_title) {
          titleInput.value = result.suggested_title;
        }

        appendChatBubble('ai', `Applied **${genreName}** acoustic & vocal arrangement tags! Every single word of your original lyrics is 100% preserved.`, {
          changedSection: "Arrangement Tags"
        });
        showToast(`✨ ${genreShort} style tags applied! Your lyrics preserved.`);
      }
    } catch (e) {
      console.warn("Enhance preset error:", e);
    } finally {
      isEnhancingPreset = false;
    }
  }

  async function onGenrePresetSelected(genreName) {
    if (!selectGenre) return;
    selectGenre.value = genreName;

    // Sync quick chip active states
    document.querySelectorAll('#genre-quick-chips .chip').forEach(c => {
      const chipLabel = c.textContent.trim();
      const genrePart = genreName.split('/')[1] ? genreName.split('/')[1].trim() : genreName;
      c.classList.toggle('active', chipLabel === genrePart || c.dataset.genre === genreName);
    });

    // Check if Custom / Keep Only Lyrics
    if (genreName === "Custom / Keep Only Lyrics") {
      showToast("🎵 Custom / Keep Only Lyrics: Your lyrics will remain 100% untouched.");
      return;
    }

    // Check if there are user lyrics in editor
    const text = editorLyrics ? editorLyrics.value.trim() : "";
    if (text && text.length > 20) {
      await enhanceLyricsWithPreset(genreName);
    }
  }

  // --- State Variables ---
  const urlParams = new URLSearchParams(window.location.search);
  const sessionToken = urlParams.get('token');
  let currentAudioUrl = null;
  let tapTimestamps = [];
  let pollInterval = null;
  let audioContext = null;
  let audioBuffer = null;

  // --- Active Session Heartbeat & Window Close Beacon ---
  if (sessionToken) {
    // 1. Send keep-alive heartbeat every 15s while studio window is open
    setInterval(async () => {
      try {
        const resp = await fetch('/api/music/session/heartbeat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: sessionToken })
        });
        if (!resp.ok && (resp.status === 403 || resp.status === 404)) {
          console.warn("[YuE2 Studio] Active session closed on server");
          showToast("🔒 Studio session has ended. Run /music in Discord for a new session.", 6000);
          if (btnGenerateSong) {
            btnGenerateSong.disabled = true;
          }
        }
      } catch (err) {
        console.debug("[YuE2 Studio] Heartbeat check:", err);
      }
    }, 15000);

    // 2. Invalidate session link when user closes tab or navigates away
    const closeSessionBeacon = () => {
      try {
        const closeUrl = `/api/music/session/close?token=${encodeURIComponent(sessionToken)}`;
        if (navigator.sendBeacon) {
          navigator.sendBeacon(closeUrl);
        } else {
          fetch(closeUrl, { method: 'POST', keepalive: true }).catch(() => {});
        }
      } catch (_) {}
    };

    window.addEventListener('pagehide', closeSessionBeacon);
    window.addEventListener('beforeunload', closeSessionBeacon);
  }

  function showToast(msg, duration = 3000) {
    toastMessage.textContent = msg;
    toast.classList.remove('hidden');
    setTimeout(() => {
      toast.classList.add('hidden');
    }, duration);
  }

  function updateCharCount() {
    const text = editorLyrics ? editorLyrics.value || '' : '';
    const chars = text.length;
    const lines = text ? text.split('\n').length : 0;
    if (lyricsCharCount) {
      lyricsCharCount.textContent = `${chars.toLocaleString()} characters | ${lines} lines`;
    }

    // Dynamic button label & subtext based on whether user has lyrics
    if (btnGenerateLyrics) {
      const textSpan = btnGenerateLyrics.querySelector('.btn-text');
      const subSpan = btnGenerateLyrics.querySelector('.btn-subtext');
      if (text.trim().length > 0) {
        if (textSpan) textSpan.textContent = "Enhance Lyrics";
        if (subSpan) subSpan.textContent = "Keep User Lyrics";
        btnGenerateLyrics.title = "Enhance your lyrics with acoustic & vocal performance tags without changing your words.";
      } else {
        if (textSpan) textSpan.textContent = "Generate Lyrics";
        if (subSpan) subSpan.textContent = "From Scratch";
        btnGenerateLyrics.title = "Generate a complete song concept & lyrics structure from scratch.";
      }
    }

    // Dynamic chat input placeholder
    if (inputRevisionPrompt) {
      if (text.trim().length === 0) {
        inputRevisionPrompt.placeholder = "Tell the AI what song to create (e.g. 'Write an indie pop song with 2 verses, chorus, bridge, and outro')...";
      } else {
        inputRevisionPrompt.placeholder = "Tell the AI what to change (e.g. 'Change verse 2 out for something different' or 'Make chorus more dramatic')...";
      }
    }
  }

  // --- Initial Data Load ---
  async function initStudio() {
    // 1. Ensure presets and quick chips are immediately active in DOM
    if (selectGenre && selectGenre.options.length === 0) {
      populateSelect(selectGenre, FALLBACK_GENRES, "Custom / Keep Only Lyrics");
    }
    if (selectVocal && selectVocal.options.length === 0) {
      populateSelect(selectVocal, FALLBACK_VOCALS, "Warm Smooth Baritone (Male)");
    }
    if (selectIntro && selectIntro.options.length === 0) {
      populateSelect(selectIntro, FALLBACK_INTROS, "None");
    }
    setupQuickChips(FEATURED_CHIPS, selectGenre ? selectGenre.value : "Custom / Keep Only Lyrics");

    if (selectGenre) {
      selectGenre.addEventListener('change', () => {
        onGenrePresetSelected(selectGenre.value);
      });
    }
    try {
      const res = await fetch('/api/music/options');
      if (!res.ok) throw new Error("Failed to load options");
      const data = await res.json();

      // Update monitor badges
      if (badgeComfy && statusComfyText) {
        const dot = badgeComfy.querySelector('.indicator-dot');
        if (data.comfy_connected) {
          if (dot) dot.className = 'indicator-dot online';
          statusComfyText.textContent = "Online";
          badgeComfy.title = "ComfyUI is reachable and ready";
        } else {
          if (dot) dot.className = 'indicator-dot offline';
          statusComfyText.textContent = "Offline";
          badgeComfy.title = "Cannot reach ComfyUI";
        }
      }

      if (badgeLlm && statusLlmText) {
        const dot = badgeLlm.querySelector('.indicator-dot');
        if (data.lmstudio_connected) {
          if (dot) dot.className = 'indicator-dot online';
          statusLlmText.textContent = data.lm_model ? `Online (${data.lm_model})` : "Online";
          badgeLlm.title = `Connected to ${data.lm_base_url || 'LM Studio'}`;
        } else {
          if (dot) dot.className = 'indicator-dot offline';
          statusLlmText.textContent = "Offline";
          badgeLlm.title = `Cannot reach LM Studio at ${data.lm_base_url || 'port 1234'}`;
        }
      }

      // Sync Presets from backend
      if (data.genre_presets && data.genre_presets.length > 0) {
        populateSelect(selectGenre, data.genre_presets, selectGenre ? selectGenre.value : data.default_genre);
      }
      if (data.vocal_profiles && data.vocal_profiles.length > 0) {
        populateSelect(selectVocal, data.vocal_profiles, selectVocal ? selectVocal.value : data.default_vocal);
      }
      if (data.intro_styles && data.intro_styles.length > 0) {
        populateSelect(selectIntro, data.intro_styles, selectIntro ? selectIntro.value : data.default_intro);
      }
      setupQuickChips(FEATURED_CHIPS, selectGenre ? selectGenre.value : (data.default_genre || "Custom / Keep Only Lyrics"));

      // Set defaults if empty
      if (bpmSlider && !bpmSlider.value) {
        bpmSlider.value = data.bpm_default || 120;
        if (bpmVal) bpmVal.textContent = data.bpm_default || 120;
      }
      if (inputCustomStyle && !inputCustomStyle.value) {
        inputCustomStyle.value = data.default_custom_style || "Style of Bruno Mars song Risk It All";
      }
      if (selectOdeSteps && !selectOdeSteps.value) {
        selectOdeSteps.value = String(data.default_ode_steps || 24);
      }
      // Keep empty if user starts fresh so placeholder shows and bottom chat can create a song
      updateCharCount();

    } catch (e) {
      console.warn("Init studio options fetch warning:", e);
      if (badgeComfy && statusComfyText) {
        const dot = badgeComfy.querySelector('.indicator-dot');
        if (dot) dot.className = 'indicator-dot offline';
        statusComfyText.textContent = "Offline";
      }
      if (badgeLlm && statusLlmText) {
        const dot = badgeLlm.querySelector('.indicator-dot');
        if (dot) dot.className = 'indicator-dot offline';
        statusLlmText.textContent = "Offline";
      }
    } finally {
      // Check for Discord Session always, even if options fetch warned
      if (sessionToken) {
        loadDiscordSession(sessionToken);
      }
    }
  }

  // Periodic status poller to keep monitor badges dynamic (every 12 seconds)
  setInterval(async () => {
    try {
      const res = await fetch('/api/music/options');
      if (!res.ok) return;
      const data = await res.json();
      if (badgeComfy && statusComfyText) {
        const dot = badgeComfy.querySelector('.indicator-dot');
        if (data.comfy_connected) {
          if (dot) dot.className = 'indicator-dot online';
          statusComfyText.textContent = "Online";
        } else {
          if (dot) dot.className = 'indicator-dot offline';
          statusComfyText.textContent = "Offline";
        }
      }
      if (badgeLlm && statusLlmText) {
        const dot = badgeLlm.querySelector('.indicator-dot');
        if (data.lmstudio_connected) {
          if (dot) dot.className = 'indicator-dot online';
          statusLlmText.textContent = data.lm_model ? `Online (${data.lm_model})` : "Online";
        } else {
          if (dot) dot.className = 'indicator-dot offline';
          statusLlmText.textContent = "Offline";
        }
      }
    } catch (_) {}
  }, 12000);

  // --- Master Audio Player Management ---
  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  function loadAudioTrack(audioUrl, title, takeNum) {
    if (!audioMaster) return;
    try {
      if (takeNum) currentTake = parseInt(takeNum) || currentTake;
      audioMaster.src = audioUrl;
      audioMaster.load();

      if (playerTrackTitle) {
        playerTrackTitle.textContent = title || "Studio Master Track";
      }
      if (playerTakeBadge) {
        playerTakeBadge.textContent = `Take #${currentTake}`;
      }
      if (playerTrackSubtitle) {
        playerTrackSubtitle.textContent = `24-bit Studio Master • Take #${currentTake} Audition Ready`;
      }
      if (btnPlayerDownload) {
        btnPlayerDownload.href = audioUrl;
        const cleanTitle = (title || "studio_master").toLowerCase().replace(/[^a-z0-9_-]/g, "_");
        btnPlayerDownload.download = `${cleanTitle}_Take${currentTake}.mp3`;
      }

      if (masterPlayerBar) {
        masterPlayerBar.classList.remove('hidden');
        masterPlayerBar.classList.remove('just-loaded');
        void masterPlayerBar.offsetWidth; // trigger reflow
        masterPlayerBar.classList.add('just-loaded');
      }

      // Update button labels to highlight seamless multi-take workflow
      if (btnGenerateSong) {
        const textSpan = btnGenerateSong.querySelector('.btn-text');
        if (textSpan) textSpan.textContent = `Generate Next Take (#${currentTake + 1})`;
      }
      if (btnPushEditorSong) {
        btnPushEditorSong.textContent = `🚀 Generate Next Take (#${currentTake + 1})`;
      }
      if (btnRegenerateTake) {
        btnRegenerateTake.textContent = `🚀 Generate Take #${currentTake + 1}`;
      }

      console.log(`[YuE2 Studio] Loaded master audio track: ${audioUrl} (Take #${currentTake})`);
    } catch (err) {
      console.warn("[YuE2 Studio] loadAudioTrack error:", err);
    }
  }

  // Audio Playback Controls
  if (btnPlayerPlay && audioMaster) {
    btnPlayerPlay.addEventListener('click', () => {
      if (audioMaster.paused) {
        audioMaster.play().catch(e => console.warn("Audio play blocked:", e));
      } else {
        audioMaster.pause();
      }
    });

    audioMaster.addEventListener('play', () => {
      btnPlayerPlay.classList.add('playing');
      if (playerPlayIcon) playerPlayIcon.textContent = '⏸';
    });

    audioMaster.addEventListener('pause', () => {
      btnPlayerPlay.classList.remove('playing');
      if (playerPlayIcon) playerPlayIcon.textContent = '▶';
    });

    audioMaster.addEventListener('ended', () => {
      btnPlayerPlay.classList.remove('playing');
      if (playerPlayIcon) playerPlayIcon.textContent = '▶';
      if (playerTimeline) playerTimeline.value = 0;
      if (playerTimeCurrent) playerTimeCurrent.textContent = "0:00";
    });

    audioMaster.addEventListener('timeupdate', () => {
      if (audioMaster.duration && !isNaN(audioMaster.duration)) {
        const pct = (audioMaster.currentTime / audioMaster.duration) * 100;
        if (playerTimeline) playerTimeline.value = pct;
        if (playerTimeCurrent) playerTimeCurrent.textContent = formatTime(audioMaster.currentTime);
      }
    });

    audioMaster.addEventListener('loadedmetadata', () => {
      if (playerTimeDuration && audioMaster.duration && !isNaN(audioMaster.duration)) {
        playerTimeDuration.textContent = formatTime(audioMaster.duration);
      }
    });
  }

  if (playerTimeline && audioMaster) {
    playerTimeline.addEventListener('input', (e) => {
      if (audioMaster.duration && !isNaN(audioMaster.duration)) {
        const targetSec = (parseFloat(e.target.value) / 100) * audioMaster.duration;
        audioMaster.currentTime = targetSec;
        if (playerTimeCurrent) playerTimeCurrent.textContent = formatTime(targetSec);
      }
    });
  }

  if (playerVolume && audioMaster) {
    playerVolume.addEventListener('input', (e) => {
      audioMaster.volume = parseFloat(e.target.value);
    });
  }

  if (btnRegenerateTake) {
    btnRegenerateTake.addEventListener('click', () => {
      runSongGeneration();
    });
  }

  // --- Load Session From Discord Interaction ---
  async function loadDiscordSession(token) {
    try {
      const res = await fetch(`/api/music/session/${token}`);
      if (!res.ok) {
        console.warn("Discord session not found or closed:", res.status);
        showToast("🔒 Studio session ended or closed. Please run /music in Discord.", 8000);
        if (btnGenerateSong) {
          btnGenerateSong.disabled = true;
          btnGenerateSong.title = "Session closed. Please run /music in Discord to start a new session.";
        }
        return;
      }
      const s = await res.json();
      if (s && s.token) {
        const titleInput = document.getElementById('input-song-title') || inputSongTitle;
        if (s.song_title && titleInput) {
          titleInput.value = s.song_title;
        }
        if (s.genre_preset && selectGenre) {
          selectGenre.value = s.genre_preset;
          setupQuickChips(FEATURED_CHIPS, s.genre_preset);
        }
        if (s.vocal_profile && selectVocal) selectVocal.value = s.vocal_profile;
        if (s.intro_style && selectIntro) selectIntro.value = s.intro_style;
        if (s.bpm && bpmSlider) {
          bpmSlider.value = s.bpm;
          if (bpmVal) bpmVal.textContent = s.bpm;
          updateActiveTempoChip(s.bpm);
        }
        if (s.custom_style && inputCustomStyle) inputCustomStyle.value = s.custom_style;
        if (s.lyrics && editorLyrics) editorLyrics.value = s.lyrics;
        if (s.ode_steps && selectOdeSteps) selectOdeSteps.value = String(s.ode_steps);
        updateCharCount();
        if (s.take_count) {
          currentTake = parseInt(s.take_count) || 1;
        }
        showToast(`Loaded Discord session for ${s.user_name || 'User'}`);
        if (s.audio_url) {
          loadAudioTrack(s.audio_url, s.song_title || "Discord Session Track", currentTake);
        }
      }
    } catch (e) {
      console.warn("Discord session fetch error:", e);
    }
  }

  // --- Tempo / BPM Controls ---
  if (bpmSlider) {
    bpmSlider.addEventListener('input', (e) => {
      if (bpmVal) bpmVal.textContent = e.target.value;
      updateActiveTempoChip(parseInt(e.target.value));
    });
  }

  if (tempoChips && tempoChips.length > 0) {
    tempoChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const val = parseInt(chip.dataset.bpm);
        if (bpmSlider) bpmSlider.value = val;
        if (bpmVal) bpmVal.textContent = val;
        updateActiveTempoChip(val);
      });
    });
  }

  function updateActiveTempoChip(val) {
    if (tempoChips) {
      tempoChips.forEach(c => {
        if (parseInt(c.dataset.bpm) === val) c.classList.add('active');
        else c.classList.remove('active');
      });
    }
  }

  // Tap Tempo
  if (btnTapTempo) {
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
        if (bpmSlider) bpmSlider.value = calculatedBpm;
        if (bpmVal) bpmVal.textContent = calculatedBpm;
        updateActiveTempoChip(calculatedBpm);
      }
    });
  }

  // Advanced Drawer Toggle
  if (btnToggleAdvanced && advancedDrawer) {
    btnToggleAdvanced.addEventListener('click', () => {
      const isCollapsed = advancedDrawer.classList.contains('collapsed');
      advancedDrawer.classList.toggle('collapsed');
      const arrow = btnToggleAdvanced.querySelector('.accordion-arrow');
      if (arrow) arrow.textContent = isCollapsed ? '▲' : '▼';
    });
  }

  if (checkRandomSeed && seedInputRow) {
    checkRandomSeed.addEventListener('change', (e) => {
      seedInputRow.style.display = e.target.checked ? 'none' : 'flex';
    });
  }

  // --- Tag Insertion in Lyrics Editor ---
  const tagButtons = document.querySelectorAll('.tag-btn, .tag-chip');
  if (tagButtons && tagButtons.length > 0) {
    tagButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const tag = btn.dataset.tag;
        if (tag && editorLyrics) {
          insertTextAtCursor(editorLyrics, `\n${tag}\n`);
          updateCharCount();
        }
      });
    });
  }

  function insertTextAtCursor(textarea, textToInsert) {
    if (!textarea) return;
    const startPos = textarea.selectionStart || 0;
    const endPos = textarea.selectionEnd || 0;
    const currentVal = textarea.value || '';
    textarea.value = currentVal.substring(0, startPos) + textToInsert + currentVal.substring(endPos);
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = startPos + textToInsert.length;
  }

  if (editorLyrics) {
    editorLyrics.addEventListener('input', updateCharCount);
  }

  if (btnCopyLyrics) {
    btnCopyLyrics.addEventListener('click', () => {
      if (!editorLyrics || !editorLyrics.value) return;
      navigator.clipboard.writeText(editorLyrics.value).then(() => {
        showToast("📋 Lyrics copied to clipboard!");
      });
    });
  }

  if (btnClearLyrics) {
    btnClearLyrics.addEventListener('click', () => {
      if (confirm("Reset lyrics editor to default template?")) {
        initStudio();
      }
    });
  }

  // --- Tab Switching (Editor vs Node 14) ---
  if (tabLyrics) {
    tabLyrics.addEventListener('click', () => {
      tabLyrics.classList.add('active');
      if (tabNode14) tabNode14.classList.remove('active');
      if (viewLyrics) viewLyrics.classList.remove('hidden');
      if (viewNode14) viewNode14.classList.add('hidden');
    });
  }

  if (tabNode14) {
    tabNode14.addEventListener('click', () => {
      tabNode14.classList.add('active');
      if (tabLyrics) tabLyrics.classList.remove('active');
      if (viewNode14) viewNode14.classList.remove('hidden');
      if (viewLyrics) viewLyrics.classList.add('hidden');
    });
  }

  if (btnApplyToEditor) {
    btnApplyToEditor.addEventListener('click', () => {
      const rawText = node14TextDisplay ? node14TextDisplay.textContent : "";
      if (!rawText || rawText.startsWith("No lyrics generated")) {
        showToast("No generated lyrics available to apply.");
        return;
      }
      if (editorLyrics) editorLyrics.value = rawText;
      updateCharCount();
      if (tabLyrics) tabLyrics.click();
      showToast("✍️ Applied Node 14 lyrics to editor!");
    });
  }

  // --- Modal Progress Overlay Helpers ---
  function showProgressModal(title, desc) {
    if (modalTitle) modalTitle.textContent = title;
    if (modalDesc) modalDesc.textContent = desc;
    if (progressFill) progressFill.style.width = '10%';
    if (progressStageText) progressStageText.textContent = "Initializing...";
    if (progressPercentText) progressPercentText.textContent = "10%";
    if (btnDismissOverlay) {
      btnDismissOverlay.textContent = "Close & View Track";
      btnDismissOverlay.classList.add('hidden');
    }
    if (progressOverlay) progressOverlay.classList.remove('hidden');
    if (btnGenerateLyrics) btnGenerateLyrics.disabled = true;
    if (btnGenerateSong) btnGenerateSong.disabled = true;
    if (btnPushEditorSong) btnPushEditorSong.disabled = true;
    if (btnRegenerateTake) btnRegenerateTake.disabled = true;
  }

  function updateProgressModal(percent, stageText, desc) {
    if (progressFill) progressFill.style.width = `${percent}%`;
    if (progressPercentText) progressPercentText.textContent = `${percent}%`;
    if (progressStageText) progressStageText.textContent = stageText;
    if (desc && modalDesc) modalDesc.textContent = desc;

    // Step indicators matching 3-stage studio pipeline
    if (percent < 20) {
      if (stepLlm) stepLlm.className = 'pipeline-step active';
      if (stepSynth) stepSynth.className = 'pipeline-step';
      if (stepExport) stepExport.className = 'pipeline-step';
    } else if (percent < 93) {
      if (stepLlm) stepLlm.className = 'pipeline-step';
      if (stepSynth) stepSynth.className = 'pipeline-step active';
      if (stepExport) stepExport.className = 'pipeline-step';
    } else {
      if (stepLlm) stepLlm.className = 'pipeline-step';
      if (stepSynth) stepSynth.className = 'pipeline-step';
      if (stepExport) stepExport.className = 'pipeline-step active';
    }
  }

  function hideProgressModal() {
    if (progressOverlay) progressOverlay.classList.add('hidden');
    if (btnGenerateLyrics) btnGenerateLyrics.disabled = false;
    if (btnGenerateSong) btnGenerateSong.disabled = false;
    if (btnPushEditorSong) btnPushEditorSong.disabled = false;
    if (btnRegenerateTake) btnRegenerateTake.disabled = false;
    const titleInput = document.getElementById('input-song-title') || inputSongTitle;
    if (titleInput) titleInput.disabled = false;
    if (editorLyrics) editorLyrics.disabled = false;
  }

  if (btnDismissOverlay) {
    btnDismissOverlay.addEventListener('click', hideProgressModal);
  }

  // ==========================================================================
  // BUTTON 1: ✨ GENERATE LYRICS ONLY (Disables Node 5)
  // ==========================================================================
  if (btnGenerateLyrics) {
    btnGenerateLyrics.addEventListener('click', async () => {
      const titleInput = document.getElementById('input-song-title') || inputSongTitle;
      const songTitleVal = titleInput ? titleInput.value.trim() : "";
      const currentLyrics = editorLyrics ? editorLyrics.value.trim() : "";
      const hasExistingLyrics = Boolean(currentLyrics && currentLyrics !== "No lyrics generated yet.");
      const isKeepOnly = (selectGenre ? selectGenre.value : "") === "Custom / Keep Only Lyrics";

      // If Custom / Keep Only Lyrics and user has lyrics, preserve verbatim immediately!
      if (isKeepOnly && hasExistingLyrics) {
        let cleanText = currentLyrics;
        if (!cleanText.match(/\[End\]\s*$/i)) {
          cleanText = cleanText + "\n\n[End]";
          editorLyrics.value = cleanText;
          updateCharCount();
        }
        if (node14TextDisplay) node14TextDisplay.textContent = cleanText;
        showToast("🎵 Preserved your lyrics verbatim (Custom / Keep Only Lyrics).");
        appendChatBubble('ai', "Your lyrics are preserved 100% untouched for Custom / Keep Only Lyrics mode. Concluded with [End] marker.", {
          changedSection: "Keep Only Lyrics"
        });
        return;
      }

      const payload = {
        token: sessionToken,
        song_title: songTitleVal,
        genre_preset: selectGenre ? selectGenre.value : "Custom / Keep Only Lyrics",
        vocal_profile: selectVocal ? selectVocal.value : "Warm Smooth Baritone (Male)",
        bpm: parseInt(bpmSlider ? bpmSlider.value : 120),
        intro_style: selectIntro ? selectIntro.value : "None",
        custom_style: inputCustomStyle ? inputCustomStyle.value : "",
        lyrics: currentLyrics,
        action: hasExistingLyrics ? "Polish & Arrange Lyrics" : "Generate Full Song Concept"
      };

      if (hasExistingLyrics) {
        showProgressModal(
          "Enhancing Lyrics Structure...",
          "Injecting acoustic and vocal production tags matching your genre preset while keeping your lyrics 100% intact."
        );
        updateProgressModal(35, "Arranging Production Tags...", "Injecting [Instrumentation: ...] and [Vocal: ...] tags above each verse...");
      } else {
        showProgressModal(
          "Co-Producing Full Song...",
          "Generating complete song concept and structure from scratch..."
        );
        updateProgressModal(35, "Composing Concept...", "Structuring verse, chorus, bridge, and vocal hooks...");
      }

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

        updateProgressModal(100, hasExistingLyrics ? "Lyrics Enhanced!" : "Lyrics Complete!", "Node 14 captured full output lyrics.");
        
        // Update Node 14 viewer
        if (node14TextDisplay) node14TextDisplay.textContent = generatedLyrics;
        if (node14Badge) {
          node14Badge.textContent = "New!";
          node14Badge.style.background = "rgba(16, 185, 129, 0.2)";
          node14Badge.style.color = "#10b981";
        }

        // Update editor lyrics and keep focus on main lyrics sheet so user sees it live
        if (editorLyrics) {
          editorLyrics.value = generatedLyrics;
          updateCharCount();
        }
        if (tabLyrics) tabLyrics.click();
        if (checkDirectLyrics) checkDirectLyrics.checked = true;

        // Visual flash on screen
        if (editorLyrics && editorLyrics.parentElement) {
          editorLyrics.parentElement.classList.remove('live-updated-glow');
          void editorLyrics.parentElement.offsetWidth;
          editorLyrics.parentElement.classList.add('live-updated-glow');
          setTimeout(() => editorLyrics.parentElement.classList.remove('live-updated-glow'), 1900);
        }

        // Smart Song Title Auto-Population (if not already set by user)
        if (titleInput && !titleInput.value.trim() && result.suggested_title) {
          titleInput.value = result.suggested_title;
        }

        // Add AI Co-Producer notification to revision console
        const activeTitle = (titleInput && titleInput.value.trim()) || "your track";
        if (hasExistingLyrics) {
          appendChatBubble('ai', `Enhanced lyrics for "${activeTitle}" with acoustic & vocal arrangement tags! Every single word of your original lyrics has been preserved. What would you like to refine?`, {
            changedSection: "Arrangement Tags",
            allowPushToSong: true
          });
        } else {
          appendChatBubble('ai', `Generated full song lyrics for "${activeTitle}"! What would you like to refine? You can chat with me below to adjust any section, or select a genre preset above.`, {
            changedSection: "Full Song Lyrics",
            allowPushToSong: true
          });
        }

        setTimeout(() => {
          hideProgressModal();
          showToast(hasExistingLyrics ? "✨ Enhanced lyrics on screen! (Your lyrics preserved)" : "✨ Lyrics generated on screen!");
        }, 700);

      } catch (e) {
        console.error("Lyrics generation error:", e);
        alert(`Lyrics generation error: ${e.message}`);
        hideProgressModal();
      }
    });
  }

  // ==========================================================================
  // BUTTON 2: 🚀 GENERATE FINAL SONG (Runs Full Workflow)
  // ==========================================================================
  async function runSongGeneration() {
    // Pause existing audio playback if playing
    if (audioMaster && !audioMaster.paused) {
      audioMaster.pause();
    }

    let seedVal = null;
    if (checkRandomSeed && !checkRandomSeed.checked && inputSeed && inputSeed.value) {
      seedVal = parseInt(inputSeed.value);
    }

    const titleInput = document.getElementById('input-song-title') || inputSongTitle;
    const songTitleVal = titleInput ? titleInput.value.trim() : "";
    const nextTakeNum = (masterPlayerBar && !masterPlayerBar.classList.contains('hidden')) ? currentTake + 1 : currentTake;
    console.log(`[YuE2 Studio] Submitting song generation for "${songTitleVal || 'Studio Song'}" (Take #${nextTakeNum})`);

    const payload = {
      token: sessionToken,
      song_title: songTitleVal,
      genre_preset: selectGenre ? selectGenre.value : "Custom / Keep Only Lyrics",
      vocal_profile: selectVocal ? selectVocal.value : "Warm Smooth Baritone (Male)",
      bpm: parseInt(bpmSlider ? bpmSlider.value : 120),
      intro_style: selectIntro ? selectIntro.value : "None",
      custom_style: inputCustomStyle ? inputCustomStyle.value : "",
      lyrics: editorLyrics ? editorLyrics.value : "",
      action: "Generate Full Song Concept",
      direct_lyrics: true,
      seed: seedVal,
      cot: selectCot ? selectCot.value : "full",
      ode_steps: parseInt(selectOdeSteps ? selectOdeSteps.value : 24) || 24
    };

    showProgressModal(
      `Producing Studio Track (Take #${nextTakeNum})...`,
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

  if (btnGenerateSong) {
    btnGenerateSong.addEventListener('click', runSongGeneration);
  }
  if (btnPushEditorSong) {
    btnPushEditorSong.addEventListener('click', runSongGeneration);
  }

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
          currentTake = info.take_count || (currentTake + 1);

          if (info.audio_url) {
            loadAudioTrack(info.audio_url, trackName, currentTake);
          }

          appendChatBubble('ai', `🎉 Master audio for "${trackName}" (Take #${currentTake}) has been generated and delivered directly to your Discord channel! You can audition the track above, adjust lyrics or production parameters, and generate next takes anytime.`);

          if (btnDismissOverlay) {
            btnDismissOverlay.textContent = `🎧 Audition Take #${currentTake} & Continue Editing`;
            btnDismissOverlay.classList.remove('hidden');
          }

          setTimeout(() => {
            hideProgressModal();
            showToast(`🚀 Take #${currentTake} generated and delivered to Discord!`);
          }, 1400);
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
        custom_style: inputCustomStyle ? inputCustomStyle.value : ""
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
