// State
const tvState = {
  videos: [],
  songs: [],
  currentTab: 'home',
  focusedIndex: 0,
  navElements: [],
  isPlaying: false,
  activeMedia: null,
  connectUrl: window.location.origin
};

// DOM Elements
const tvMain = document.getElementById('tv-main');
const tvClock = document.getElementById('tv-clock');
const tvIpBadge = document.getElementById('tv-ip-badge');
const heroTitle = document.getElementById('hero-title');
const heroSubtitle = document.getElementById('hero-subtitle');
const heroBackdrop = document.getElementById('hero-backdrop');
const heroPlayBtn = document.getElementById('hero-play-btn');
const tvVideoRow = document.getElementById('tv-video-row');
const tvMusicRow = document.getElementById('tv-music-row');
const tvVideosCount = document.getElementById('tv-videos-count');
const tvMusicCount = document.getElementById('tv-music-count');
const tvVlcUrl = document.getElementById('tv-vlc-url');

// TV Player Elements
const tvPlayerModal = document.getElementById('tv-player-modal');
const tvPlayerVideo = document.getElementById('tv-player-video');
const tvPlayerTitle = document.getElementById('tv-player-title');
const tvPlayerProgressFill = document.getElementById('tv-player-progress-fill');
const tvPlayerCurrentTime = document.getElementById('tv-player-current-time');
const tvPlayerDuration = document.getElementById('tv-player-duration');
const tvPlayerControls = document.getElementById('tv-player-controls');

let controlsTimeout = null;

// Helpers
function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

function updateClock() {
  const now = new Date();
  tvClock.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
setInterval(updateClock, 1000);
updateClock();

function getCoverUrl(item) {
  if (item && item.cover_hash) {
    return `/api/cover/${item.id}`;
  }
  return '/icon.svg';
}

function escapeHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Fetch Data
async function loadTvHub() {
  try {
    const [statusRes, vidRes, songRes] = await Promise.all([
      fetch('/api/status'),
      fetch('/api/videos'),
      fetch('/api/songs')
    ]);

    const statusData = await statusRes.json();
    const vidData = await vidRes.json();
    const songData = await songRes.json();

    tvState.connectUrl = statusData.connect_url || window.location.origin;
    tvState.videos = vidData.videos || [];
    tvState.songs = songData.songs || [];

    tvIpBadge.textContent = tvState.connectUrl.replace('http://', '');
    if (tvVlcUrl) tvVlcUrl.textContent = `${tvState.connectUrl}/api/playlist.m3u`;

    renderHero(tvState.videos[0] || tvState.songs[0]);
    renderVideoRow(tvState.videos);
    renderMusicRow(tvState.songs);

    updateFocusableElements();
    focusElement(heroPlayBtn || document.querySelector('.tv-card'));
  } catch (err) {
    console.error('Failed to load TV data:', err);
  }
}

function renderHero(item) {
  if (!item) return;
  heroTitle.textContent = item.title || 'Welcome to MediaHub';
  heroSubtitle.textContent = item.artist || (item.media_type === 'video' ? 'Movie / Video' : 'Music');
  const coverUrl = getCoverUrl(item);
  heroBackdrop.src = coverUrl;

  heroPlayBtn.onclick = () => playMedia(item);
}

function renderVideoRow(videos) {
  tvVideoRow.innerHTML = '';
  tvVideosCount.textContent = `${videos.length} videos`;

  if (videos.length === 0) {
    tvVideoRow.innerHTML = '<p style="color:var(--text-muted); padding:20px 0;">No movies or videos shared yet.</p>';
    return;
  }

  videos.forEach(v => {
    const card = document.createElement('div');
    card.className = 'tv-card focusable';
    card.tabIndex = 0;
    card.innerHTML = `
      <div class="tv-card-thumb">
        <img src="${getCoverUrl(v)}" alt="" loading="lazy">
        ${v.duration ? `<span class="tv-card-duration">${formatTime(v.duration)}</span>` : ''}
      </div>
      <div class="tv-card-body">
        <h4 class="tv-card-title">${escapeHtml(v.title)}</h4>
        <span class="tv-card-subtitle">${v.artist || 'Local Video'}</span>
      </div>
    `;
    card.onclick = () => playMedia(v);
    tvVideoRow.appendChild(card);
  });
}

function renderMusicRow(songs) {
  tvMusicRow.innerHTML = '';
  tvMusicCount.textContent = `${songs.length} songs`;

  if (songs.length === 0) {
    tvMusicRow.innerHTML = '<p style="color:var(--text-muted); padding:20px 0;">No music shared yet.</p>';
    return;
  }

  songs.forEach(s => {
    const card = document.createElement('div');
    card.className = 'tv-card music-card focusable';
    card.tabIndex = 0;
    card.innerHTML = `
      <div class="tv-card-thumb">
        <img src="${getCoverUrl(s)}" alt="" loading="lazy">
      </div>
      <div class="tv-card-body">
        <h4 class="tv-card-title">${escapeHtml(s.title)}</h4>
        <span class="tv-card-subtitle">${escapeHtml(s.artist || 'Unknown Artist')}</span>
      </div>
    `;
    card.onclick = () => playMedia(s);
    tvMusicRow.appendChild(card);
  });
}

// Spatial Navigation Engine (D-Pad TV Remote)
function updateFocusableElements() {
  tvState.navElements = Array.from(document.querySelectorAll('.focusable, .tv-menu-btn, .tv-hero-btn'));
}

function getFocusedElement() {
  return document.activeElement;
}

function focusElement(el) {
  if (!el) return;
  el.focus();
  document.querySelectorAll('.focused').forEach(n => n.classList.remove('focused'));
  el.classList.add('focused');

  // Scroll into view if needed
  el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
}

function navigateSpatial(direction) {
  const current = getFocusedElement();
  if (!current) {
    focusElement(document.querySelector('.focusable'));
    return;
  }

  const currentRect = current.getBoundingClientRect();
  const candidates = tvState.navElements.filter(el => el !== current && el.offsetParent !== null);

  let bestCandidate = null;
  let bestDistance = Infinity;

  candidates.forEach(cand => {
    const rect = cand.getBoundingClientRect();

    let isDirectionValid = false;
    let mainAxisDist = 0;
    let crossAxisDist = 0;

    if (direction === 'right') {
      isDirectionValid = rect.left >= currentRect.left + 5;
      mainAxisDist = rect.left - currentRect.right;
      crossAxisDist = Math.abs((rect.top + rect.height / 2) - (currentRect.top + currentRect.height / 2));
    } else if (direction === 'left') {
      isDirectionValid = rect.right <= currentRect.right - 5;
      mainAxisDist = currentRect.left - rect.right;
      crossAxisDist = Math.abs((rect.top + rect.height / 2) - (currentRect.top + currentRect.height / 2));
    } else if (direction === 'down') {
      isDirectionValid = rect.top >= currentRect.top + 5;
      mainAxisDist = rect.top - currentRect.bottom;
      crossAxisDist = Math.abs((rect.left + rect.width / 2) - (currentRect.left + currentRect.width / 2));
    } else if (direction === 'up') {
      isDirectionValid = rect.bottom <= currentRect.bottom - 5;
      mainAxisDist = currentRect.top - rect.bottom;
      crossAxisDist = Math.abs((rect.left + rect.width / 2) - (currentRect.left + currentRect.width / 2));
    }

    if (isDirectionValid) {
      const distance = Math.sqrt(Math.pow(Math.max(0, mainAxisDist), 2) + Math.pow(crossAxisDist * 1.5, 2));
      if (distance < bestDistance) {
        bestDistance = distance;
        bestCandidate = cand;
      }
    }
  });

  if (bestCandidate) {
    focusElement(bestCandidate);
  }
}

// Media Playback
function playMedia(item) {
  tvState.activeMedia = item;
  tvPlayerTitle.textContent = item.title || 'Playing';
  tvPlayerVideo.src = `/api/stream/${item.id}`;
  tvPlayerModal.classList.remove('hidden');
  tvPlayerVideo.play().catch(e => console.warn(e));
  showPlayerControls();
}

function closePlayer() {
  tvPlayerVideo.pause();
  tvPlayerVideo.src = '';
  tvPlayerModal.classList.add('hidden');
  tvState.activeMedia = null;
  focusElement(heroPlayBtn || document.querySelector('.tv-card'));
}

function showPlayerControls() {
  clearTimeout(controlsTimeout);
  tvPlayerControls.classList.remove('fade-out');
  controlsTimeout = setTimeout(() => {
    if (!tvPlayerVideo.paused) {
      tvPlayerControls.classList.add('fade-out');
    }
  }, 4000);
}

// TV Player Progress
tvPlayerVideo.addEventListener('timeupdate', () => {
  if (!tvPlayerVideo.duration) return;
  const cur = tvPlayerVideo.currentTime;
  const dur = tvPlayerVideo.duration;
  tvPlayerProgressFill.style.width = `${(cur / dur) * 100}%`;
  tvPlayerCurrentTime.textContent = formatTime(cur);
  tvPlayerDuration.textContent = formatTime(dur);
});

// Global D-Pad Remote & Keyboard Handler
window.addEventListener('keydown', (e) => {
  const isPlaying = !tvPlayerModal.classList.contains('hidden');

  if (isPlaying) {
    // Player Controls
    if (e.key === 'Escape' || e.key === 'Back' || e.key === 'BrowserBack' || e.keyCode === 10009 || e.keyCode === 27) {
      e.preventDefault();
      closePlayer();
      return;
    }

    if (e.key === 'Enter' || e.key === ' ' || e.keyCode === 13) {
      e.preventDefault();
      if (tvPlayerVideo.paused) {
        tvPlayerVideo.play();
      } else {
        tvPlayerVideo.pause();
      }
      showPlayerControls();
      return;
    }

    if (e.key === 'ArrowRight' || e.keyCode === 39) {
      e.preventDefault();
      tvPlayerVideo.currentTime = Math.min(tvPlayerVideo.duration, tvPlayerVideo.currentTime + 10);
      showPlayerControls();
      return;
    }

    if (e.key === 'ArrowLeft' || e.keyCode === 37) {
      e.preventDefault();
      tvPlayerVideo.currentTime = Math.max(0, tvPlayerVideo.currentTime - 10);
      showPlayerControls();
      return;
    }

    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      showPlayerControls();
      return;
    }
    return;
  }

  // Browse Navigation
  switch (e.key) {
    case 'ArrowRight':
      e.preventDefault();
      navigateSpatial('right');
      break;
    case 'ArrowLeft':
      e.preventDefault();
      navigateSpatial('left');
      break;
    case 'ArrowDown':
      e.preventDefault();
      navigateSpatial('down');
      break;
    case 'ArrowUp':
      e.preventDefault();
      navigateSpatial('up');
      break;
    case 'Enter':
      const cur = getFocusedElement();
      if (cur) cur.click();
      break;
    case 'Escape':
    case 'Back':
    case 'BrowserBack':
      window.location.href = '/';
      break;
  }
});

// Menu button switching
document.querySelectorAll('.tv-menu-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tv-menu-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const view = btn.dataset.view;
    if (view === 'movies') {
      document.getElementById('movies-section').scrollIntoView({ behavior: 'smooth' });
    } else if (view === 'music') {
      document.getElementById('music-section').scrollIntoView({ behavior: 'smooth' });
    } else if (view === 'vlc') {
      document.getElementById('vlc-section').scrollIntoView({ behavior: 'smooth' });
    } else if (view === 'exit') {
      window.location.href = '/';
    }
  });
});

// Start Hub on load
loadTvHub();
