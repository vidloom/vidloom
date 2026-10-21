/**
 * Vidloom Studio — InVideo AI Split-Screen Desktop Workstation
 * Left: Interactive Script Storyboard & Docked Magic Box Command Console
 * Right: Dominant 4K Vertical Video Player & Mini Timeline
 */

document.addEventListener('DOMContentLoaded', () => {
  // =========================================================================
  // 1. DATASETS
  // =========================================================================
  const projectsData = {
    promo: {
      id: 'promo',
      title: 'The Luxury Italian Leather Tote',
      videoSrc: 'media/promo_short.mp4',
      duration: 23.7,
      formatBadge: '9:16 • 1080×1920 • 60fps',
      aspect: '9:16',
      voice: 'Emma (US English, Conversational Female)',
      music: 'Acoustic Commercial',
      scenes: [
        { id: 1, start: 0.0, end: 4.0, name: 'Hook & Bag Reveal', text: 'Tired of bags that look great but fall apart in months?', media: 'Luxury Leather Tote Close-up', thumb: 'media/preview_promo.png' },
        { id: 2, start: 4.0, end: 7.6, name: 'Artisan Craftsmanship', text: 'Meet the Aurelia Tote — handcrafted from 100% full-grain Tuscan hide.', media: 'Tuscan Leather Artisan Stitching', thumb: 'media/promo_card.png' },
        { id: 3, start: 7.6, end: 11.3, name: 'Street Commute', text: 'Engineered for the daily commute, refined for evening dinners.', media: 'Urban Commute Lifestyle 4K', thumb: 'media/preview_promo.png' },
        { id: 4, start: 11.3, end: 15.0, name: 'Tech & Compartments', text: 'Dedicated 14-inch laptop compartment & magnetic quick pockets.', media: 'Interior Organization & Hardware', thumb: 'media/promo_card.png' },
        { id: 5, start: 15.0, end: 18.6, name: 'Velvet Lining Detail', text: 'Plush Italian velvet interior protects your valuables with pure luxury.', media: 'Italian Velvet Lining Macro', thumb: 'media/preview_promo.png' },
        { id: 6, start: 18.6, end: 21.9, name: 'Everyday Styling', text: 'Seamlessly matches any wardrobe, from casual denim to tailored suits.', media: 'Fashion Model Outfit Transition', thumb: 'media/promo_card.png' },
        { id: 7, start: 21.9, end: 23.7, name: 'Limited 30% Offer', text: 'Limited production run. Claim yours today with 30% off.', media: 'Gold Badge Packshot & Discount', thumb: 'media/promo_card.png' }
      ]
    },
    facts: {
      id: 'facts',
      title: 'Deep Space Cosmic Mysteries',
      videoSrc: 'media/facts_short.mp4',
      duration: 28.4,
      formatBadge: '9:16 • 1080×1920 • 60fps',
      aspect: '9:16',
      voice: 'Christopher (US English, Deep Male)',
      music: 'Deep Space Ambient',
      scenes: [
        { id: 1, start: 0.0, end: 5.0, name: 'The Cosmic Void', text: 'Did you know the universe contains regions of complete nothingness spanning billions of light-years?', media: 'Deep Space Galaxy Cluster', thumb: 'media/fact_card.png' },
        { id: 2, start: 5.0, end: 10.0, name: 'The Bootes Void', text: 'The Boötes Void is so vast that if the Milky Way were in its center, we wouldn\'t have known other galaxies existed until the 1960s.', media: 'Supercluster Simulation 4K', thumb: 'media/fact_card.png' },
        { id: 3, start: 10.0, end: 15.5, name: 'Black Hole Echoes', text: 'At the heart of the Perseus cluster, a supermassive black hole emits sound waves 57 octaves below middle C.', media: 'Black Hole Gravitational Lensing', thumb: 'media/fact_card.png' },
        { id: 4, start: 15.5, end: 20.0, name: 'Diamond Planet', text: '55 Cancri e is an exoplanet twice the size of Earth believed to be largely composed of crystallized diamond.', media: 'Exoplanet Atmospheric Rendering', thumb: 'media/fact_card.png' },
        { id: 5, start: 20.0, end: 24.5, name: 'Time Dilation', text: 'Near the event horizon, a few seconds for an observer equals thousands of years on Earth.', media: 'Spacetime Curvature Grid', thumb: 'media/fact_card.png' },
        { id: 6, start: 24.5, end: 28.4, name: 'Subscribe Follower CTA', text: 'Follow for daily cosmic discoveries that redefine reality.', media: 'Cosmic Nebula Final Outro', thumb: 'media/fact_card.png' }
      ]
    },
    reddit: {
      id: 'reddit',
      title: 'Subterranean Basement Story',
      videoSrc: 'media/reddit_short.mp4',
      duration: 32.1,
      formatBadge: '9:16 • 1080×1920 • 60fps',
      aspect: '9:16',
      voice: 'Brian (Storyteller, Dynamic Male)',
      music: 'Dark Ambient Suspense',
      scenes: [
        { id: 1, start: 0.0, end: 4.5, name: 'The Moving In Day', text: 'I bought a 1920s Victorian home, but the previous owner left one strict instruction: never open the cellar padlock.', media: 'Old Victorian House Exterior', thumb: 'media/reddit_card.png' },
        { id: 2, start: 4.5, end: 9.0, name: 'The Midnight Scratching', text: 'Three days in, at exactly 2:14 AM, scratching sounds began coming up through the floorboards.', media: 'Dark Staircase Dim Lighting', thumb: 'media/reddit_card.png' },
        { id: 3, start: 9.0, end: 14.0, name: 'The Steel Lock', text: 'I took a crowbar down to the cellar. The padlock wasn\'t locking the door from the outside. It was locked from the inside.', media: 'Rusted Padlock & Chains', thumb: 'media/reddit_card.png' },
        { id: 4, start: 14.0, end: 19.0, name: 'The Concrete Hatch', text: 'Behind the wooden door was a modern reinforced vault door sealed with fresh concrete.', media: 'Concrete Bunker Tunnel', thumb: 'media/reddit_card.png' },
        { id: 5, start: 19.0, end: 24.0, name: 'The Chiseled Note', text: 'Chiseled into the concrete was a single message: It is sleeping. Do not make noise.', media: 'Flashlight Beam on Wall', thumb: 'media/reddit_card.png' },
        { id: 6, start: 24.0, end: 28.0, name: 'The Tap Response', text: 'I accidentally dropped my flashlight. From the other side of the concrete came two loud taps.', media: 'Dust Falling Underground', thumb: 'media/reddit_card.png' },
        { id: 7, start: 28.0, end: 32.1, name: 'Part 2 Cliffhanger', text: 'Like and subscribe for Part 2 to see what the inspection camera found inside.', media: 'Dark Shadows Closing', thumb: 'media/reddit_card.png' }
      ]
    }
  };

  let currentProject = projectsData.promo;

  // =========================================================================
  // 2. DOM ELEMENTS
  // =========================================================================
  const btnSwitchPrompt = document.getElementById('btnSwitchPrompt');
  const btnSwitchEditor = document.getElementById('btnSwitchEditor');
  const viewPromptConsole = document.getElementById('viewPromptConsole');
  const viewEditorWorkspace = document.getElementById('viewEditorWorkspace');
  const projectTitleInput = document.getElementById('projectTitleInput');
  const projectFormatBadge = document.getElementById('projectFormatBadge');
  const btnQuickSwapProject = document.getElementById('btnQuickSwapProject');

  // Video & Controls
  const studioMainVideo = document.getElementById('studioMainVideo');
  const btnCenterPlayOverlay = document.getElementById('btnCenterPlayOverlay');
  const btnPlayPause = document.getElementById('btnPlayPause');
  const iconPlay = document.getElementById('iconPlay');
  const iconPause = document.getElementById('iconPause');
  const txtTimeElapsed = document.getElementById('txtTimeElapsed');
  const txtTimeDuration = document.getElementById('txtTimeDuration');
  const scrubTrackContainer = document.getElementById('scrubTrackContainer');
  const scrubProgressBar = document.getElementById('scrubProgressBar');
  const scrubThumb = document.getElementById('scrubThumb');
  const btnVolumeToggle = document.getElementById('btnVolumeToggle');
  const iconVolumeHigh = document.getElementById('iconVolumeHigh');
  const iconVolumeMute = document.getElementById('iconVolumeMute');
  const btnFullscreen = document.getElementById('btnFullscreen');

  // Left Pane Tabs
  const tabBtnScript = document.getElementById('tabBtnScript');
  const tabBtnMedia = document.getElementById('tabBtnMedia');
  const tabBtnAudio = document.getElementById('tabBtnAudio');
  const paneScriptContent = document.getElementById('paneScriptContent');
  const paneMediaContent = document.getElementById('paneMediaContent');
  const paneAudioContent = document.getElementById('paneAudioContent');
  const scriptScenesStream = document.getElementById('scriptScenesStream');
  const mediaAssetsGrid = document.getElementById('mediaAssetsGrid');
  const badgeSceneCount = document.getElementById('badgeSceneCount');

  // Mini Timeline
  const miniSegmentsTrack = document.getElementById('miniSegmentsTrack');
  const txtTimelineCuts = document.getElementById('txtTimelineCuts');

  // Magic Box Command Console
  const commandInstructionInput = document.getElementById('commandInstructionInput');
  const btnSubmitCommand = document.getElementById('btnSubmitCommand');
  const commandFeedbackToast = document.getElementById('commandFeedbackToast');
  const toastFeedbackText = document.getElementById('toastFeedbackText');
  const cmdChips = document.querySelectorAll('.cmd-chip');

  // Audio Sliders
  const sliderVoiceoverVol = document.getElementById('sliderVoiceoverVol');
  const valVoiceoverVol = document.getElementById('valVoiceoverVol');
  const sliderMusicVol = document.getElementById('sliderMusicVol');
  const valMusicVol = document.getElementById('valMusicVol');
  const sliderSfxVol = document.getElementById('sliderSfxVol');
  const valSfxVol = document.getElementById('valSfxVol');

  // Direct Download & Copy Meta
  const btnDirectDownload = document.getElementById('btnDirectDownload');
  const btnCopyMeta = document.getElementById('btnCopyMeta');

  // Modal Export
  const btnExportModal = document.getElementById('btnExportModal');
  const modalExportContainer = document.getElementById('modalExportContainer');
  const btnCloseExportModal = document.getElementById('btnCloseExportModal');
  const btnCancelExport = document.getElementById('btnCancelExport');
  const btnStartExport = document.getElementById('btnStartExport');
  const renderProgressBox = document.getElementById('renderProgressBox');
  const renderBarFill = document.getElementById('renderBarFill');
  const renderStatusMsg = document.getElementById('renderStatusMsg');
  const renderPercentMsg = document.getElementById('renderPercentMsg');

  // Prompt Console
  const promptTextarea = document.getElementById('promptTextarea');
  const presetChips = document.querySelectorAll('.preset-chip');
  const btnGenerateProject = document.getElementById('btnGenerateProject');
  const recentCards = document.querySelectorAll('.recent-card');

  // =========================================================================
  // 3. UTILITY FORMATTERS
  // =========================================================================
  function formatTimecode(seconds) {
    if (isNaN(seconds)) return '00:00.0';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    const mm = String(m).padStart(2, '0');
    const ss = String(s).padStart(2, '0');
    return `${mm}:${ss}.${ms}`;
  }

  // =========================================================================
  // 4. VIEW SWITCHING
  // =========================================================================
  function switchView(viewName) {
    if (viewName === 'prompt') {
      viewPromptConsole.style.display = 'flex';
      viewEditorWorkspace.style.display = 'none';
      btnSwitchPrompt.classList.add('active');
      btnSwitchEditor.classList.remove('active');
      studioMainVideo.pause();
    } else {
      viewPromptConsole.style.display = 'none';
      viewEditorWorkspace.style.display = 'grid';
      btnSwitchEditor.classList.add('active');
      btnSwitchPrompt.classList.remove('active');
    }
  }

  btnSwitchPrompt.addEventListener('click', () => switchView('prompt'));
  btnSwitchEditor.addEventListener('click', () => switchView('editor'));

  // Left Pane Subtabs
  function switchPaneTab(tabName) {
    [tabBtnScript, tabBtnMedia, tabBtnAudio].forEach(b => b.classList.remove('active'));
    [paneScriptContent, paneMediaContent, paneAudioContent].forEach(p => p.style.display = 'none');

    if (tabName === 'script') {
      tabBtnScript.classList.add('active');
      paneScriptContent.style.display = 'block';
    } else if (tabName === 'media') {
      tabBtnMedia.classList.add('active');
      paneMediaContent.style.display = 'block';
    } else if (tabName === 'audio') {
      tabBtnAudio.classList.add('active');
      paneAudioContent.style.display = 'block';
    }
  }

  tabBtnScript.addEventListener('click', () => switchPaneTab('script'));
  tabBtnMedia.addEventListener('click', () => switchPaneTab('media'));
  tabBtnAudio.addEventListener('click', () => switchPaneTab('audio'));

  // =========================================================================
  // 5. LOAD PROJECT IN WORKSPACE
  // =========================================================================
  function loadProject(projectKey) {
    if (!projectsData[projectKey]) return;
    currentProject = projectsData[projectKey];

    // Metadata
    projectTitleInput.value = currentProject.title;
    projectFormatBadge.textContent = currentProject.formatBadge;
    badgeSceneCount.textContent = currentProject.scenes.length;
    txtTimelineCuts.textContent = `${currentProject.scenes.length} Cuts • ${currentProject.duration}s`;

    // Video Source
    studioMainVideo.src = currentProject.videoSrc;
    studioMainVideo.load();
    txtTimeElapsed.textContent = '00:00.0';
    txtTimeDuration.textContent = formatTimecode(currentProject.duration);
    scrubProgressBar.style.width = '0%';
    scrubThumb.style.left = '0%';

    // Hydrate Left Pane Script Stream
    renderScriptStream();

    // Hydrate Left Pane Media Grid
    renderMediaGrid();

    // Hydrate Right Pane Mini Timeline
    renderMiniTimeline();

    // Recent Cards
    recentCards.forEach(card => {
      card.classList.toggle('active-card', card.dataset.project === projectKey);
    });

    switchView('editor');
  }

  // =========================================================================
  // 6. RENDER SCRIPT STREAM & SYNCHRONIZED SCRUBBING
  // =========================================================================
  function renderScriptStream() {
    scriptScenesStream.innerHTML = '';
    currentProject.scenes.forEach((scene, index) => {
      const card = document.createElement('div');
      card.className = `script-scene-card ${index === 0 ? 'active' : ''}`;
      card.dataset.scene = scene.id;
      card.dataset.start = scene.start;
      card.dataset.end = scene.end;

      card.innerHTML = `
        <div class="scene-header-row">
          <div class="scene-title-group">
            <span class="scene-num-badge">Cut 0${scene.id}</span>
            <span class="scene-title-text">${scene.name}</span>
          </div>
          <div class="scene-meta-group">
            <span class="scene-time-pill">${scene.start.toFixed(1)}s - ${scene.end.toFixed(1)}s</span>
          </div>
        </div>
        <div class="scene-body-row">
          <img src="${scene.thumb}" alt="${scene.name}" class="scene-thumb-preview">
          <textarea class="scene-text-input" rows="2" data-scene-id="${scene.id}">${scene.text}</textarea>
        </div>
        <div class="scene-footer-actions">
          <span class="scene-media-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
            ${scene.media}
          </span>
          <button class="btn-scene-action btn-swap-cut" data-scene-id="${scene.id}">Swap Footage</button>
        </div>
      `;

      // 1-Click Timestamp Seeking (InVideo Signature Sync)
      card.addEventListener('click', (e) => {
        if (e.target.tagName !== 'TEXTAREA' && !e.target.classList.contains('btn-swap-cut')) {
          studioMainVideo.currentTime = scene.start;
          updateActiveScene(scene.start);
        }
      });

      card.querySelector('.btn-swap-cut').addEventListener('click', (e) => {
        e.stopPropagation();
        alert(`Opened Pexels 4K Library for Cut 0${scene.id} (${scene.name}).`);
      });

      card.querySelector('.scene-text-input').addEventListener('input', (e) => {
        scene.text = e.target.value;
      });

      scriptScenesStream.appendChild(card);
    });
  }

  // Render Media Grid
  function renderMediaGrid() {
    mediaAssetsGrid.innerHTML = '';
    currentProject.scenes.forEach(scene => {
      const card = document.createElement('div');
      card.className = 'media-asset-card';
      card.innerHTML = `
        <div class="media-thumb-box">
          <img src="${scene.thumb}" alt="${scene.name}" class="media-thumb-img">
          <span class="media-dur-tag">${(scene.end - scene.start).toFixed(1)}s</span>
        </div>
        <div class="media-meta-box">
          <h4 class="media-card-title">Cut 0${scene.id}: ${scene.name}</h4>
          <span class="media-card-sub">${scene.media} • 4K 60fps</span>
        </div>
        <button class="btn-swap-media" data-scene-id="${scene.id}">Replace B-Roll</button>
      `;

      card.querySelector('.btn-swap-media').addEventListener('click', () => {
        alert(`Opening 4K Pexels B-roll replacement for Cut 0${scene.id}.`);
      });

      mediaAssetsGrid.appendChild(card);
    });
  }

  // Render Mini Timeline Under Player
  function renderMiniTimeline() {
    miniSegmentsTrack.innerHTML = '';
    currentProject.scenes.forEach((scene, index) => {
      const block = document.createElement('div');
      block.className = `mini-segment-block ${index === 0 ? 'active' : ''}`;
      block.dataset.scene = scene.id;
      block.dataset.start = scene.start;
      block.dataset.end = scene.end;
      block.title = `Cut 0${scene.id}: ${scene.name} (${scene.start.toFixed(1)}s - ${scene.end.toFixed(1)}s)`;

      block.innerHTML = `<div class="mini-segment-fill" style="width: 0%;"></div>`;

      block.addEventListener('click', () => {
        studioMainVideo.currentTime = scene.start;
        updateActiveScene(scene.start);
      });

      miniSegmentsTrack.appendChild(block);
    });
  }

  function updateActiveScene(currentTime) {
    // Update Script Stream Cards
    const scriptCards = scriptScenesStream.querySelectorAll('.script-scene-card');
    scriptCards.forEach(card => {
      const start = parseFloat(card.dataset.start);
      const end = parseFloat(card.dataset.end);
      if (currentTime >= start && currentTime < end) {
        card.classList.add('active');
      } else {
        card.classList.remove('active');
      }
    });

    // Update Mini Timeline Segments
    const segBlocks = miniSegmentsTrack.querySelectorAll('.mini-segment-block');
    segBlocks.forEach(block => {
      const start = parseFloat(block.dataset.start);
      const end = parseFloat(block.dataset.end);
      const fill = block.querySelector('.mini-segment-fill');

      if (currentTime >= start && currentTime < end) {
        block.classList.add('active');
        const pct = Math.min(100, Math.max(0, ((currentTime - start) / (end - start)) * 100));
        if (fill) fill.style.width = `${pct}%`;
      } else if (currentTime >= end) {
        block.classList.remove('active');
        if (fill) fill.style.width = '100%';
      } else {
        block.classList.remove('active');
        if (fill) fill.style.width = '0%';
      }
    });
  }

  // =========================================================================
  // 7. VIDEO PLAYBACK & SCRUBBER
  // =========================================================================
  function togglePlay() {
    if (studioMainVideo.paused || studioMainVideo.ended) {
      studioMainVideo.play().catch(e => console.warn('Play interrupted:', e));
    } else {
      studioMainVideo.pause();
    }
  }

  btnPlayPause.addEventListener('click', togglePlay);
  btnCenterPlayOverlay.addEventListener('click', togglePlay);
  studioMainVideo.addEventListener('click', togglePlay);

  studioMainVideo.addEventListener('play', () => {
    iconPlay.style.display = 'none';
    iconPause.style.display = 'block';
    btnCenterPlayOverlay.style.opacity = '0';
    btnCenterPlayOverlay.style.pointerEvents = 'none';
  });

  studioMainVideo.addEventListener('pause', () => {
    iconPlay.style.display = 'block';
    iconPause.style.display = 'none';
    btnCenterPlayOverlay.style.opacity = '1';
    btnCenterPlayOverlay.style.pointerEvents = 'auto';
  });

  studioMainVideo.addEventListener('loadedmetadata', () => {
    txtTimeDuration.textContent = formatTimecode(studioMainVideo.duration || currentProject.duration);
  });

  studioMainVideo.addEventListener('timeupdate', () => {
    const cur = studioMainVideo.currentTime;
    const dur = studioMainVideo.duration || currentProject.duration;
    txtTimeElapsed.textContent = formatTimecode(cur);

    if (dur > 0) {
      const pct = (cur / dur) * 100;
      scrubProgressBar.style.width = `${pct}%`;
      scrubThumb.style.left = `${pct}%`;
    }

    updateActiveScene(cur);
  });

  // Custom Scrubber Track
  let isScrubbing = false;
  function handleScrub(e) {
    const rect = scrubTrackContainer.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const dur = studioMainVideo.duration || currentProject.duration;
    studioMainVideo.currentTime = pos * dur;
    scrubProgressBar.style.width = `${pos * 100}%`;
    scrubThumb.style.left = `${pos * 100}%`;
  }

  scrubTrackContainer.addEventListener('mousedown', (e) => {
    isScrubbing = true;
    handleScrub(e);
  });

  window.addEventListener('mousemove', (e) => {
    if (isScrubbing) handleScrub(e);
  });

  window.addEventListener('mouseup', () => {
    if (isScrubbing) isScrubbing = false;
  });

  // Volume & Fullscreen
  btnVolumeToggle.addEventListener('click', () => {
    studioMainVideo.muted = !studioMainVideo.muted;
    if (studioMainVideo.muted) {
      iconVolumeHigh.style.display = 'none';
      iconVolumeMute.style.display = 'block';
    } else {
      iconVolumeHigh.style.display = 'block';
      iconVolumeMute.style.display = 'none';
    }
  });

  btnFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      studioMainVideo.requestFullscreen().catch(err => alert(`Fullscreen error: ${err.message}`));
    } else {
      document.exitFullscreen();
    }
  });

  // Spacebar Play/Pause
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      togglePlay();
    }
    if (e.key === 'Escape') {
      closeExportModal();
    }
  });

  // =========================================================================
  // 8. THE INVIDEO SIGNATURE "MAGIC BOX" COMMAND CONSOLE
  // =========================================================================
  function executeCommand(instruction) {
    if (!instruction.trim()) return;

    toastFeedbackText.textContent = `Applied instruction: "${instruction}"`;
    commandFeedbackToast.style.display = 'flex';
    
    if (instruction.toLowerCase().includes('energetic') || instruction.toLowerCase().includes('voice')) {
      toastFeedbackText.textContent = 'Voiceover profile updated to High-Energy commercial tone.';
    } else if (instruction.toLowerCase().includes('music') || instruction.toLowerCase().includes('quieter') || instruction.toLowerCase().includes('volume') || instruction.toLowerCase().includes('10%')) {
      sliderMusicVol.value = 10;
      valMusicVol.textContent = '10%';
      toastFeedbackText.textContent = 'Background soundtrack volume lowered to 10% (-20dB ducking).';
    } else if (instruction.toLowerCase().includes('scene 3') || instruction.toLowerCase().includes('footage')) {
      toastFeedbackText.textContent = 'Cut 03 B-roll swapped with 4K Boutique Interior clip.';
    } else if (instruction.toLowerCase().includes('subtitle') || instruction.toLowerCase().includes('clean')) {
      toastFeedbackText.textContent = 'Subtitle typography switched to Minimalist Clean Sans.';
    }

    setTimeout(() => {
      commandFeedbackToast.style.display = 'none';
    }, 4500);

    commandInstructionInput.value = '';
  }

  btnSubmitCommand.addEventListener('click', () => {
    executeCommand(commandInstructionInput.value);
  });

  commandInstructionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      executeCommand(commandInstructionInput.value);
    }
  });

  cmdChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const cmd = chip.dataset.cmd;
      commandInstructionInput.value = cmd;
      executeCommand(cmd);
    });
  });

  // Quick Project Swap in Topbar
  btnQuickSwapProject.addEventListener('click', () => {
    const keys = ['promo', 'facts', 'reddit'];
    const nextKey = keys[(keys.indexOf(currentProject.id) + 1) % keys.length];
    loadProject(nextKey);
  });

  // Audio Sliders
  sliderVoiceoverVol.addEventListener('input', (e) => { valVoiceoverVol.textContent = `${e.target.value}%`; });
  sliderMusicVol.addEventListener('input', (e) => { valMusicVol.textContent = `${e.target.value}%`; });
  sliderSfxVol.addEventListener('input', (e) => { valSfxVol.textContent = `${e.target.value}%`; });

  // Direct Download
  btnDirectDownload.addEventListener('click', () => {
    const a = document.createElement('a');
    a.href = currentProject.videoSrc;
    a.download = `${currentProject.title.replace(/\s+/g, '_')}_4K.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  });

  // Copy Metadata
  btnCopyMeta.addEventListener('click', () => {
    const metaText = `Title: ${currentProject.title}\n\nDescription: Explore ${currentProject.title}. Handcrafted 4K vertical short generated with Vidloom Studio.\n\n#Shorts #Viral #Production #4K`;
    navigator.clipboard.writeText(metaText).then(() => {
      btnCopyMeta.innerHTML = `<span>✓ Copied</span>`;
      setTimeout(() => {
        btnCopyMeta.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          <span>Copy Metadata</span>
        `;
      }, 2500);
    });
  });

  // =========================================================================
  // 9. EXPORT MODAL
  // =========================================================================
  function openExportModal() {
    modalExportContainer.style.display = 'flex';
    renderProgressBox.style.display = 'none';
    btnStartExport.style.display = 'flex';
  }

  function closeExportModal() {
    modalExportContainer.style.display = 'none';
  }

  btnExportModal.addEventListener('click', openExportModal);
  btnCloseExportModal.addEventListener('click', closeExportModal);
  btnCancelExport.addEventListener('click', closeExportModal);

  btnStartExport.addEventListener('click', () => {
    renderProgressBox.style.display = 'flex';
    btnStartExport.disabled = true;
    let progress = 0;

    const interval = setInterval(() => {
      progress += Math.floor(Math.random() * 15) + 12;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        renderBarFill.style.width = '100%';
        renderPercentMsg.textContent = '100%';
        renderStatusMsg.textContent = 'Render completed! Downloading MP4...';

        setTimeout(() => {
          const a = document.createElement('a');
          a.href = currentProject.videoSrc;
          a.download = `${currentProject.title.replace(/\s+/g, '_')}_4K.mp4`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          closeExportModal();
          btnStartExport.disabled = false;
        }, 1200);
      } else {
        renderBarFill.style.width = `${progress}%`;
        renderPercentMsg.textContent = `${progress}%`;
        if (progress < 40) renderStatusMsg.textContent = 'Encoding 4K video layers...';
        else if (progress < 75) renderStatusMsg.textContent = 'Multiplexing audio master & ducking...';
        else renderStatusMsg.textContent = 'Finalizing MP4 container...';
      }
    }, 180);
  });

  // =========================================================================
  // 10. PROMPT CONSOLE PRESETS
  // =========================================================================
  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      presetChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const presetKey = chip.dataset.preset;

      if (presetKey === 'promo') {
        promptTextarea.value = 'Create a luxury promotional video for an Italian full-grain leather tote bag. Focus on artisan craftsmanship, commute durability, interior compartments, and a limited 30% off collection offer.';
      } else if (presetKey === 'facts') {
        promptTextarea.value = 'Create a mind-bending educational short about 3 cosmic mysteries of deep space. Explore the Boötes void, Perseus black hole acoustic frequencies, and diamond planets.';
      } else if (presetKey === 'reddit') {
        promptTextarea.value = 'Create a suspenseful first-person mystery narration about discovering a padlocked underground cellar in a 1920s Victorian house where the lock was on the inside.';
      }
    });
  });

  btnGenerateProject.addEventListener('click', () => {
    const activeChip = document.querySelector('.preset-chip.active');
    const presetKey = activeChip ? activeChip.dataset.preset : 'promo';
    loadProject(presetKey);
  });

  recentCards.forEach(card => {
    card.addEventListener('click', () => {
      const pKey = card.dataset.project;
      loadProject(pKey);
    });
  });

  // Initial load
  loadProject('promo');

  // URL View Param Check
  if (window.location.hash === '#prompt' || window.location.search.includes('view=prompt')) {
    switchView('prompt');
  }
});
