/* ==========================================================================
   VIDLOOM INTERACTIVE STUDIO ENGINE — JAVASCRIPT
   Handles Video Niche Switching, Live Player, Audio Previews & ROI Calculator
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

  // --- 1. Video Niche Database ---
  const NICHE_DATA = {
    promo: {
      id: 'promo',
      name: '✨ Luxury Product Promo',
      headline: 'The Luxury Italian Leather Tote',
      videoSrc: 'media/promo_short.mp4',
      poster: 'media/preview_promo.png',
      voice: 'Emma (Warm Commercial)',
      music: 'Inspiring Upbeat Commercial',
      style: 'Gold Punch',
      hookDuration: '23.7s • 7 Scene Cuts',
      badge: '✨ AURORA LUXE • LIMITED COLLECTION'
    },
    reddit: {
      id: 'reddit',
      name: '🔥 Viral Reddit Story',
      headline: 'The Secret Room Behind The Basement Wall',
      videoSrc: 'media/reddit_short.mp4',
      poster: 'media/reddit_card.png',
      voice: 'Brian (Viral Narrator)',
      music: 'Suspense Cinematic Ambient',
      style: 'Hormozi Yellow',
      hookDuration: '32.1s • 10 Scene Cuts',
      badge: 'r/AskReddit • glitched_witness'
    },
    facts: {
      id: 'facts',
      name: '🧠 Mind-Blowing Facts',
      headline: '3 Terrifying Facts About Deep Space',
      videoSrc: 'media/facts_short.mp4',
      poster: 'media/fact_card.png',
      voice: 'Christopher (US Male)',
      music: 'Upbeat Tech Drive',
      style: 'Cyber Cyan',
      hookDuration: '28.4s • 8 Scene Cuts',
      badge: '⚡ VIRAL COSMOS • SPACE FACT #1'
    }
  };

  let currentNiche = 'promo';
  const videoElem = document.getElementById('studioVideo');
  const hudTitle = document.getElementById('hudTitle');
  const hudMeta = document.getElementById('hudMeta');
  const hudPlayBtn = document.getElementById('hudPlayBtn');
  const tabButtons = document.querySelectorAll('.niche-tab-btn');

  // Switch Niche Function
  function switchNiche(nicheKey) {
    if (!NICHE_DATA[nicheKey]) return;
    currentNiche = nicheKey;
    const data = NICHE_DATA[nicheKey];

    // Update Tab UI
    tabButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.niche === nicheKey);
    });

    // Update Video Source & Metadata
    videoElem.pause();
    videoElem.src = data.videoSrc;
    videoElem.load();
    hudTitle.textContent = data.headline;
    hudMeta.textContent = `${data.voice} • ${data.hookDuration}`;
    hudPlayBtn.innerHTML = '▶';

    // Update active chips in controls panel
    updateControlChips(data);
  }

  // Bind tab buttons
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      switchNiche(btn.dataset.niche);
    });
  });

  // Play / Pause HUD Toggle
  hudPlayBtn.addEventListener('click', () => {
    if (videoElem.paused) {
      videoElem.play();
      hudPlayBtn.innerHTML = '❚❚';
    } else {
      videoElem.pause();
      hudPlayBtn.innerHTML = '▶';
    }
  });

  videoElem.addEventListener('play', () => {
    hudPlayBtn.innerHTML = '❚❚';
  });

  videoElem.addEventListener('pause', () => {
    hudPlayBtn.innerHTML = '▶';
  });

  // Helper to sync chips with active video preset
  function updateControlChips(data) {
    // Voice chips
    document.querySelectorAll('[data-voice]').forEach(chip => {
      chip.classList.toggle('active', data.voice.toLowerCase().includes(chip.dataset.voice.toLowerCase()));
    });
    // Style chips
    document.querySelectorAll('[data-sub-style]').forEach(chip => {
      chip.classList.toggle('active', data.style.toLowerCase().includes(chip.dataset.subStyle.toLowerCase()));
    });
  }

  // --- 2. Live Audio Preview Player ---
  const audioSampleBtn = document.getElementById('audioSampleBtn');
  const bgmPlayer = new Audio();
  let isPlayingAudio = false;

  const AUDIO_TRACKS = {
    upbeat: 'media/upbeat_bgm.mp3',
    suspense: 'media/suspense_bgm.mp3',
    whoosh: 'media/whoosh.mp3'
  };

  if (audioSampleBtn) {
    audioSampleBtn.addEventListener('click', () => {
      const selectedTrack = currentNiche === 'reddit' ? AUDIO_TRACKS.suspense : AUDIO_TRACKS.upbeat;
      if (!isPlayingAudio) {
        bgmPlayer.src = selectedTrack;
        bgmPlayer.volume = 0.5;
        bgmPlayer.play();
        isPlayingAudio = true;
        audioSampleBtn.innerHTML = '❚❚ Pause';
        document.querySelector('.soundwave-visualizer')?.classList.add('playing');
      } else {
        bgmPlayer.pause();
        isPlayingAudio = false;
        audioSampleBtn.innerHTML = '▶ Preview';
        document.querySelector('.soundwave-visualizer')?.classList.remove('playing');
      }
    });

    bgmPlayer.addEventListener('ended', () => {
      isPlayingAudio = false;
      audioSampleBtn.innerHTML = '▶ Preview';
      document.querySelector('.soundwave-visualizer')?.classList.remove('playing');
    });
  }

  // --- 3. Interactive ROI & Time Saved Calculator ---
  const calcSlider = document.getElementById('calcSlider');
  const sliderCountVal = document.getElementById('sliderCountVal');
  const calcHoursSaved = document.getElementById('calcHoursSaved');
  const calcMoneySaved = document.getElementById('calcMoneySaved');
  const calcViewsVal = document.getElementById('calcViewsVal');

  function updateCalculator() {
    if (!calcSlider) return;
    const weeklyVideos = parseInt(calcSlider.value, 10);
    const monthlyVideos = Math.round(weeklyVideos * 4.3);

    sliderCountVal.textContent = `${weeklyVideos} ${weeklyVideos === 1 ? 'Short' : 'Shorts'}/wk`;
    
    // Each short takes ~3.5 hours to manually script, voice, find b-roll, subtitle and render
    const hoursSaved = Math.round(monthlyVideos * 3.5);
    // Average freelance video editor charges ~$30 per short
    const moneySaved = monthlyVideos * 30;
    // Average views expected on consistent high-retention shorts
    const viewsPotential = (monthlyVideos * 24000).toLocaleString();

    calcHoursSaved.textContent = `${hoursSaved} hrs`;
    calcMoneySaved.textContent = `$${moneySaved.toLocaleString()}`;
    calcViewsVal.textContent = `${viewsPotential}+`;
  }

  if (calcSlider) {
    calcSlider.addEventListener('input', updateCalculator);
    updateCalculator();
  }

  // --- 4. Bento Box Live Karaoke Animation ---
  const karaokeTokens = document.querySelectorAll('.karaoke-token');
  if (karaokeTokens.length > 0) {
    let tokenIdx = 0;
    setInterval(() => {
      karaokeTokens.forEach((t, i) => {
        if (i === tokenIdx) {
          t.classList.add('karaoke-highlight');
        } else {
          t.classList.remove('karaoke-highlight');
        }
      });
      tokenIdx = (tokenIdx + 1) % karaokeTokens.length;
    }, 450);
  }

  // --- 5. Interactive FAQ Accordion ---
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const questionBtn = item.querySelector('.faq-question');
    questionBtn.addEventListener('click', () => {
      const isOpen = item.classList.contains('active');
      faqItems.forEach(other => other.classList.remove('active'));
      if (!isOpen) {
        item.classList.add('active');
      }
    });
  });

  // --- 6. Quick Interactive Chips Action ---
  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const group = e.target.closest('.chip-group');
      if (group) {
        group.querySelectorAll('.chip-btn').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
      }
    });
  });

});
