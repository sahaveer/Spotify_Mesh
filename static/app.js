// State
const state = {
  allSongs: [],
  filteredSongs: [],
  videos: [],
  favorites: [],
  favFilter: 'all',
  mediaScope: 'all',
  mySongs: [],
  myVideos: [],
  localTracks: [],
  myMediaFilter: 'all',
  queue: [],
  currentIndex: -1,
  currentTrack: null,
  isPlaying: false,
  isShuffle: false,
  repeatMode: 'off',
  currentView: 'songs',
  artists: [],
  albums: [],
  playlists: [],
  peers: [],
  clients: [],
  connectUrl: '',
  availableIps: [],
  settings: {},
  downloads: []
};

// Client Heartbeat Identifier
let clientId = localStorage.getItem('mediahub_client_id');
if (!clientId) {
  clientId = 'client_' + Math.random().toString(36).substring(2, 10);
  localStorage.setItem('mediahub_client_id', clientId);
}

function getDeviceType() {
  const ua = navigator.userAgent;
  if (/android/i.test(ua)) return 'Android Device';
  if (/iPad|iPhone|iPod/.test(ua)) return 'iPhone / iPad';
  if (/Macintosh/.test(ua)) return 'Mac Web Player';
  if (/Windows/.test(ua)) return 'Windows Web Player';
  return 'Web Player';
}

function apiFetch(url, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};
  headers['X-Client-Id'] = clientId;
  return fetch(url, { ...options, headers });
}

async function sendClientHeartbeat() {
  try {
    await apiFetch('/api/client/ping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: clientId,
        device_name: getDeviceType(),
        user_agent: navigator.userAgent
      })
    });
  } catch (e) {}
}
setInterval(sendClientHeartbeat, 15000);
sendClientHeartbeat();

// DOM Elements
const audio = document.getElementById('audio-engine');
const videoEngine = document.getElementById('video-engine');
const videoModal = document.getElementById('video-player-modal');
const videoModalTitle = document.getElementById('video-modal-title');
const videoModalClose = document.getElementById('video-modal-close');

const songListEl = document.getElementById('song-list');
const videoGridEl = document.getElementById('video-grid');
const favoritesSongListEl = document.getElementById('favorites-song-list');
const favoritesVideoGridEl = document.getElementById('favorites-video-grid');
const favoritesCountBadge = document.getElementById('favorites-count-badge');
const favoritesEmptyEl = document.getElementById('favorites-empty');

// My Device View Elements
const myDeviceTypeLabel = document.getElementById('my-device-type-label');
const myDeviceHeadline = document.getElementById('my-device-headline');
const quickShareBtn = document.getElementById('quick-share-btn');
const quickLocalBtn = document.getElementById('quick-local-btn');
const quickMeshBtn = document.getElementById('quick-mesh-btn');
const localPlaybackInput = document.getElementById('local-playback-input');
const addMoreLocalBtn = document.getElementById('add-more-local-btn');
const localTracksListEl = document.getElementById('local-tracks-list');
const localTracksCountEl = document.getElementById('local-tracks-count');
const mySharedSongListEl = document.getElementById('my-shared-song-list');
const mySharedVideoGridEl = document.getElementById('my-shared-video-grid');
const mySharedCountEl = document.getElementById('my-shared-count');
const mySharedEmptyEl = document.getElementById('my-shared-empty');
const emptyShareTriggerBtn = document.getElementById('empty-share-trigger-btn');

const artistsGridEl = document.getElementById('artists-grid');
const albumsGridEl = document.getElementById('albums-grid');
const playlistsGridEl = document.getElementById('playlists-grid');
const peersListEl = document.getElementById('peers-list');
const clientsListEl = document.getElementById('clients-list');
const clientsCountBadge = document.getElementById('clients-count-badge');
const meshCountBadge = document.getElementById('mesh-count-badge');
const refreshPeersBtn = document.getElementById('refresh-peers-btn');
const sharedFoldersListEl = document.getElementById('shared-folders-list');
const downloadsQueueEl = document.getElementById('downloads-queue');

const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search');
const sortSelect = document.getElementById('sort-select');
const serverBadge = document.getElementById('server-badge');
const brandDeviceName = document.getElementById('brand-device-name');
const libraryStatsHeader = document.getElementById('library-stats-header');
const videosCountBadge = document.getElementById('videos-count-badge');

// Mini Audio Player Elements
const miniPlayer = document.getElementById('mini-player');
const miniCover = document.getElementById('mini-cover');
const miniTitle = document.getElementById('mini-title');
const miniArtist = document.getElementById('mini-artist');
const miniPlayBtn = document.getElementById('mini-play-btn');
const miniPlayIcon = document.getElementById('mini-play-icon');
const miniPrevBtn = document.getElementById('mini-prev-btn');
const miniNextBtn = document.getElementById('mini-next-btn');
const miniLoveBtn = document.getElementById('mini-love-btn');
const miniProgressFill = document.getElementById('mini-progress-fill');
const miniPlayerClickTarget = document.getElementById('mini-player-click-target');

// Full Audio Player Elements
const fullPlayer = document.getElementById('full-player');
const fullPlayerClose = document.getElementById('full-player-close');
const fullCover = document.getElementById('full-cover');
const fullTitle = document.getElementById('full-title');
const fullArtist = document.getElementById('full-artist');
const fullAlbum = document.getElementById('full-album');
const fullLoveBtn = document.getElementById('full-love-btn');
const seekSlider = document.getElementById('seek-slider');
const currentTimeEl = document.getElementById('current-time');
const totalDurationEl = document.getElementById('total-duration');
const playBtn = document.getElementById('play-btn');
const fullPlayIcon = document.getElementById('full-play-icon');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const shuffleBtn = document.getElementById('shuffle-btn');
const repeatBtn = document.getElementById('repeat-btn');
const volumeSlider = document.getElementById('volume-slider');
const queueToggleBtn = document.getElementById('queue-toggle-btn');
const queuePanel = document.getElementById('queue-panel');
const queueListEl = document.getElementById('queue-list');
const clearQueueBtn = document.getElementById('clear-queue-btn');

// Detail View
const detailBackBtn = document.getElementById('detail-back-btn');
const detailCoverImg = document.getElementById('detail-cover-img');
const detailType = document.getElementById('detail-type');
const detailTitle = document.getElementById('detail-title');
const detailSubtitle = document.getElementById('detail-subtitle');
const detailSongList = document.getElementById('detail-song-list');
const detailPlayBtn = document.getElementById('detail-play-btn');

// Downloader Elements
const dlUrlInput = document.getElementById('dl-url-input');
const dlQualitySelect = document.getElementById('dl-quality-select');
const startDownloadBtn = document.getElementById('start-download-btn');

// Privacy Elements
const masterSharingToggle = document.getElementById('master-sharing-toggle');
const deviceNameInput = document.getElementById('device-name-input');
const saveDeviceNameBtn = document.getElementById('save-device-name-btn');
const addFolderBtn = document.getElementById('add-folder-btn');

// Helper: Format Seconds to mm:ss
function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 MB';
  const mb = bytes / (1024 * 1024);
  if (mb > 1024) {
    return `${(mb / 1024).toFixed(2)} GB`;
  }
  return `${mb.toFixed(1)} MB`;
}

function getCoverUrl(song) {
  if (song && song.cover_hash) {
    return `/api/cover/${song.id}`;
  }
  return '/icon.svg';
}

function escapeHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// --- API Calls ---
async function fetchStatus() {
  try {
    const res = await apiFetch('/api/status');
    const data = await res.json();
    if (data.status === 'online') {
      state.connectUrl = data.connect_url;
      state.availableIps = data.available_ips || [data.local_ip];
      
      const clientText = data.connected_clients > 0 ? ` (${data.connected_clients} client${data.connected_clients > 1 ? 's' : ''})` : '';
      serverBadge.textContent = data.sharing_enabled ? `Sharing Active${clientText}` : 'Stealth Mode';
      serverBadge.style.color = data.sharing_enabled ? '#10b981' : '#f59e0b';
      brandDeviceName.textContent = data.device_name || 'MediaHub';
      const stats = data.stats;
      const hours = (stats.total_duration / 3600).toFixed(1);
      libraryStatsHeader.textContent = `${stats.total_songs} songs • ${stats.total_videos} videos • ${hours} hrs`;
    }
  } catch (err) {
    serverBadge.textContent = 'Offline';
    serverBadge.style.color = '#ef4444';
  }
}

async function fetchSongs(query = '', sortBy = 'title', scope = null) {
  try {
    const activeScope = scope || state.mediaScope || 'all';
    const url = `/api/songs?query=${encodeURIComponent(query)}&sort_by=${sortBy}&scope=${activeScope}`;
    const res = await apiFetch(url);
    const data = await res.json();
    state.allSongs = data.songs;
    state.filteredSongs = data.songs;
    renderSongList(state.filteredSongs, songListEl);
  } catch (err) {
    console.error('Error fetching songs:', err);
  }
}

async function fetchVideos(query = '', scope = null) {
  try {
    const activeScope = scope || state.mediaScope || 'all';
    const url = `/api/videos?query=${encodeURIComponent(query)}&scope=${activeScope}`;
    const res = await apiFetch(url);
    const data = await res.json();
    state.videos = data.videos;
    if (videosCountBadge) videosCountBadge.textContent = `${data.count} videos`;
    renderVideos(state.videos);
  } catch (err) {
    console.error('Error fetching videos:', err);
  }
}

async function fetchMyMedia() {
  try {
    const res = await apiFetch('/api/my-media');
    const data = await res.json();
    state.mySongs = data.songs || [];
    state.myVideos = data.videos || [];
    renderMyMedia();
  } catch (err) {
    console.error('Error fetching my media:', err);
  }
}

function renderMyMedia() {
  const filter = state.myMediaFilter || 'all';
  const showSongs = filter === 'all' || filter === 'audio';
  const showVideos = filter === 'all' || filter === 'video';

  const totalCount = state.mySongs.length + state.myVideos.length;
  if (mySharedCountEl) {
    mySharedCountEl.textContent = `${totalCount} file${totalCount === 1 ? '' : 's'} shared by you`;
  }

  if (myDeviceTypeLabel) {
    myDeviceTypeLabel.textContent = `${getDeviceType()} (${clientId.substring(0, 8)})`;
  }

  const hasItems = (showSongs && state.mySongs.length > 0) || (showVideos && state.myVideos.length > 0);
  if (mySharedEmptyEl) {
    mySharedEmptyEl.classList.toggle('hidden', hasItems);
  }

  if (mySharedSongListEl) {
    if (showSongs && state.mySongs.length > 0) {
      mySharedSongListEl.classList.remove('hidden');
      renderSongList(state.mySongs, mySharedSongListEl);
    } else {
      mySharedSongListEl.innerHTML = '';
      mySharedSongListEl.classList.add('hidden');
    }
  }

  if (mySharedVideoGridEl) {
    if (showVideos && state.myVideos.length > 0) {
      mySharedVideoGridEl.classList.remove('hidden');
      renderVideos(state.myVideos, mySharedVideoGridEl);
    } else {
      mySharedVideoGridEl.innerHTML = '';
      mySharedVideoGridEl.classList.add('hidden');
    }
  }
}

function handleLocalDeviceFiles(files) {
  if (!files || files.length === 0) return;

  for (const file of files) {
    const isVideo = file.type.startsWith('video/') || /\.(mp4|mkv|webm|mov|avi)$/i.test(file.name);
    const objectUrl = URL.createObjectURL(file);
    const localId = 'local_' + Math.random().toString(36).substring(2, 10);

    const trackObj = {
      id: localId,
      title: file.name.replace(/\.[^/.]+$/, ""),
      artist: 'Local Phone File',
      album: 'Phone Storage',
      duration: 0,
      filesize: file.size,
      url: objectUrl,
      file: file,
      isLocal: true,
      media_type: isVideo ? 'video' : 'audio',
      is_owner: true,
      owner_name: 'This Device'
    };

    state.localTracks.push(trackObj);
  }

  renderLocalTracks();
}

function renderLocalTracks() {
  if (localTracksCountEl) {
    localTracksCountEl.textContent = `${state.localTracks.length} local file${state.localTracks.length === 1 ? '' : 's'}`;
  }

  if (!localTracksListEl) return;
  localTracksListEl.innerHTML = '';

  if (state.localTracks.length === 0) {
    localTracksListEl.innerHTML = `
      <div class="placeholder-text" style="padding: 20px; text-align: center;">
        <p>No local files picked yet.</p>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">Click "Play Local Phone Files" above to play songs or videos from your phone storage instantly.</p>
      </div>
    `;
    return;
  }

  state.localTracks.forEach((track, idx) => {
    const isCurrent = state.currentIndex !== -1 && state.queue[state.currentIndex]?.id === track.id;
    const row = document.createElement('div');
    row.className = `song-row ${isCurrent ? 'playing' : ''}`;
    row.dataset.songId = track.id;

    const isVideo = track.media_type === 'video';
    const iconSvg = isVideo 
      ? '<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line>'
      : '<path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>';

    row.innerHTML = `
      <div class="song-cover-thumb" style="display:flex; align-items:center; justify-content:center; background: rgba(236, 72, 153, 0.15); border-radius: 8px; width:44px; height:44px; color:#f472b6;">
        <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none">
          ${iconSvg}
        </svg>
      </div>
      <div class="song-details">
        <span class="song-title">${escapeHtml(track.title)} <span class="local-track-badge">⚡ Phone Storage</span></span>
        <span class="song-subtitle">${isVideo ? 'Local Video' : 'Local Audio'} • ${formatBytes(track.filesize)}</span>
      </div>
      <div class="song-meta-right">
        <button class="share-track-now-btn" title="Upload and share with everyone on Wi-Fi">
          <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <span>Share to Mesh</span>
        </button>
      </div>
    `;

    row.addEventListener('click', (e) => {
      if (e.target.closest('.share-track-now-btn')) return;
      if (track.media_type === 'video') {
        openVideoPlayer(track);
      } else {
        const audioTracks = state.localTracks.filter(t => t.media_type === 'audio');
        playFromList(audioTracks, audioTracks.indexOf(track));
      }
    });

    const shareBtn = row.querySelector('.share-track-now-btn');
    if (shareBtn) {
      shareBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await uploadLocalFileDirectly(track.file, shareBtn);
      });
    }

    localTracksListEl.appendChild(row);
  });
}

async function uploadLocalFileDirectly(file, btnEl = null) {
  if (!file) return;
  const originalText = btnEl ? btnEl.innerHTML : '';
  if (btnEl) {
    btnEl.innerHTML = '<span>Uploading...</span>';
    btnEl.style.opacity = '0.7';
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('client_id', clientId);
  formData.append('device_name', getDeviceType());

  try {
    serverBadge.textContent = `Sharing ${file.name}...`;
    serverBadge.style.color = '#f59e0b';

    const res = await apiFetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    if (res.ok) {
      if (btnEl) {
        btnEl.innerHTML = '<span>✓ Shared</span>';
        btnEl.style.background = 'rgba(16, 185, 129, 0.2)';
        btnEl.style.color = '#34d399';
        btnEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
      }
      fetchMyMedia();
      fetchSongs();
      fetchVideos();
      fetchStatus();
    } else {
      alert(`Failed to share ${file.name}`);
      if (btnEl) btnEl.innerHTML = originalText;
    }
  } catch (err) {
    alert(`Upload error: ${err}`);
    if (btnEl) btnEl.innerHTML = originalText;
  }
}

async function fetchFavorites() {
  try {
    const filter = state.favFilter || 'all';
    const res = await apiFetch(`/api/favorites?media_type=${filter}`);
    const data = await res.json();
    state.favorites = data.favorites || [];
    if (favoritesCountBadge) favoritesCountBadge.textContent = `${state.favorites.length} items`;
    renderFavorites(state.favorites);
  } catch (err) {
    console.error('Error fetching favorites:', err);
  }
}

async function fetchArtists() {
  try {
    const res = await apiFetch('/api/artists');
    const data = await res.json();
    state.artists = data.artists;
    renderArtists(state.artists);
  } catch (err) {
    console.error('Error fetching artists:', err);
  }
}

async function fetchAlbums() {
  try {
    const res = await apiFetch('/api/albums');
    const data = await res.json();
    state.albums = data.albums;
    renderAlbums(state.albums);
  } catch (err) {
    console.error('Error fetching albums:', err);
  }
}

async function fetchPlaylists() {
  try {
    const res = await apiFetch('/api/playlists');
    const data = await res.json();
    state.playlists = data.playlists;
    renderPlaylists(state.playlists);
  } catch (err) {
    console.error('Error fetching playlists:', err);
  }
}

async function fetchPeers() {
  try {
    const res = await apiFetch('/api/mesh/peers');
    const data = await res.json();
    state.peers = data.peers || [];
    state.clients = data.clients || [];
    renderPeers(state.peers, state.clients);
  } catch (err) {
    console.error('Error fetching peers:', err);
  }
}

async function fetchSettings() {
  try {
    const res = await apiFetch('/api/settings');
    const data = await res.json();
    state.settings = data;
    masterSharingToggle.checked = data.sharing_enabled !== false;
    deviceNameInput.value = data.device_name || '';
    renderSharedFolders(data.shared_folders || []);
  } catch (err) {
    console.error('Error fetching settings:', err);
  }
}

async function triggerScan() {
  serverBadge.textContent = 'Scanning...';
  serverBadge.style.color = '#f59e0b';
  try {
    await apiFetch('/api/scan', { method: 'POST' });
    setTimeout(() => {
      fetchStatus();
      fetchSongs();
      fetchVideos();
      fetchFavorites();
      fetchArtists();
      fetchAlbums();
    }, 1500);
  } catch (err) {
    console.error('Scan error:', err);
  }
}

// --- Favorite & Delete Logic ---
async function toggleFavorite(mediaId, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  try {
    const res = await apiFetch(`/api/media/${mediaId}/favorite`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      updateMediaFavoriteState(mediaId, data.is_favorite);
      if (state.currentView === 'favorites') {
        fetchFavorites();
      }
    }
  } catch (err) {
    console.error('Error toggling favorite:', err);
  }
}

function updateMediaFavoriteState(mediaId, isFav) {
  [state.allSongs, state.filteredSongs, state.videos, state.queue, state.favorites].forEach(list => {
    if (list) {
      const item = list.find(i => i.id === mediaId);
      if (item) item.is_favorite = isFav;
    }
  });

  document.querySelectorAll(`.love-btn[data-song-id="${mediaId}"], .love-btn[data-video-id="${mediaId}"]`).forEach(btn => {
    btn.classList.toggle('loved', isFav);
    btn.classList.toggle('active', isFav);
    btn.title = isFav ? 'Remove from Favorites' : 'Add to Favorites';
  });

  if (state.currentTrack && state.currentTrack.id === mediaId) {
    state.currentTrack.is_favorite = isFav;
    updatePlayerLoveButton(isFav);
  }
}

function updatePlayerLoveButton(isFav) {
  if (fullLoveBtn) {
    fullLoveBtn.classList.toggle('loved', !!isFav);
    fullLoveBtn.classList.toggle('active', !!isFav);
    fullLoveBtn.title = isFav ? 'Remove from Favorites' : 'Add to Favorites';
  }
  if (miniLoveBtn) {
    miniLoveBtn.classList.toggle('loved', !!isFav);
    miniLoveBtn.classList.toggle('active', !!isFav);
    miniLoveBtn.title = isFav ? 'Remove from Favorites' : 'Add to Favorites';
  }
}

async function deleteMedia(mediaId, mediaTitle, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  if (!confirm(`Are you sure you want to permanently delete "${mediaTitle}" from the library?`)) return;
  
  try {
    const res = await apiFetch(`/api/media/${mediaId}`, { method: 'DELETE' });
    if (res.ok) {
      if (state.currentTrack && state.currentTrack.id === mediaId) {
        pauseAudio();
        state.currentIndex = -1;
        state.currentTrack = null;
      }
      fetchMyMedia();
      fetchSongs();
      fetchVideos();
      fetchFavorites();
      fetchStatus();
    } else if (res.status === 403) {
      const err = await res.json();
      alert(err.detail || "Permission denied. Only the owner who shared this file can delete it.");
    } else {
      alert("Could not delete file.");
    }
  } catch (err) {
    alert(`Error deleting media: ${err}`);
  }
}

// --- Render Functions ---
function renderSongList(songs, container, isDetail = false) {
  container.innerHTML = '';
  if (!songs || songs.length === 0) {
    container.innerHTML = `
      <div style="padding: 40px; text-align: center; color: var(--text-muted);">
        <p>No songs found.</p>
        <p style="font-size: 0.85rem; margin-top: 8px;">Add folders in "Privacy & Folders", share audio, or use the Downloader.</p>
      </div>
    `;
    return;
  }

  songs.forEach((song, idx) => {
    const isCurrent = state.currentIndex !== -1 && state.queue[state.currentIndex]?.id === song.id;
    const row = document.createElement('div');
    row.className = `song-row ${isCurrent ? 'playing' : ''}`;
    row.dataset.songId = song.id;

    const isFav = !!song.is_favorite;
    const isOwner = !!song.is_owner;
    const ownerBadge = (song.owner_name && song.owner_name !== 'Host') 
      ? `<span class="owner-badge">Shared by ${escapeHtml(song.owner_name)}</span>` 
      : '';

    row.innerHTML = `
      <img class="song-cover-thumb" src="${getCoverUrl(song)}" alt="" loading="lazy">
      <div class="song-details">
        <span class="song-title">${escapeHtml(song.title || 'Unknown Title')}</span>
        <span class="song-subtitle">${escapeHtml(song.artist || 'Unknown Artist')} • ${escapeHtml(song.album || 'Unknown Album')}${ownerBadge}</span>
      </div>
      <div class="song-meta-right">
        <span class="song-duration">${formatTime(song.duration)}</span>
        <button class="icon-btn love-btn ${isFav ? 'loved active' : ''}" data-song-id="${song.id}" title="${isFav ? 'Remove from Favorites' : 'Add to Favorites'}">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
        </button>
        <a href="/api/stream/${song.id}?download=true" class="icon-btn download-direct-btn" title="Save to Device over Wi-Fi" download>
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </a>
        <button class="icon-btn add-to-pl-btn" data-song-id="${song.id}" title="Add to Playlist">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
        ${isOwner ? `
          <button class="icon-btn delete-media-btn" data-song-id="${song.id}" title="Delete file from server">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        ` : ''}
      </div>
    `;

    row.addEventListener('click', (e) => {
      if (e.target.closest('.add-to-pl-btn') || e.target.closest('.download-direct-btn') || e.target.closest('.love-btn') || e.target.closest('.delete-media-btn')) return;
      playFromList(songs, idx);
    });

    const loveBtn = row.querySelector('.love-btn');
    if (loveBtn) {
      loveBtn.addEventListener('click', (e) => toggleFavorite(song.id, e));
    }

    const deleteBtn = row.querySelector('.delete-media-btn');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', (e) => deleteMedia(song.id, song.title || 'audio track', e));
    }

    const addBtn = row.querySelector('.add-to-pl-btn');
    if (addBtn) {
      addBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openAddToPlaylistModal(song);
      });
    }

    container.appendChild(row);
  });
}

function renderVideos(videos, targetEl = videoGridEl) {
  targetEl.innerHTML = '';
  if (!videos || videos.length === 0) {
    targetEl.innerHTML = `
      <div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--text-muted);">
        <p>No movies or videos shared yet.</p>
        <p style="font-size: 0.85rem; margin-top: 8px;">Add video folders in "Privacy & Folders" or download videos from YouTube.</p>
      </div>
    `;
    return;
  }

  videos.forEach(video => {
    const card = document.createElement('div');
    card.className = 'video-card';
    const coverUrl = getCoverUrl(video);
    const isFav = !!video.is_favorite;
    const isOwner = !!video.is_owner;
    const ownerBadge = (video.owner_name && video.owner_name !== 'Host') 
      ? ` • <span style="color: #a5b4fc;">Shared by ${escapeHtml(video.owner_name)}</span>` 
      : '';

    card.innerHTML = `
      <div class="video-thumb-wrapper">
        <img src="${coverUrl}" alt="" loading="lazy">
        <div class="video-play-overlay">
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
        </div>
        ${video.duration ? `<span class="video-duration-tag">${formatTime(video.duration)}</span>` : ''}
      </div>
      <div class="video-details">
        <div class="video-info-text">
          <h4 class="video-title">${escapeHtml(video.title)}</h4>
          <span class="video-meta">${formatBytes(video.filesize)}${ownerBadge}</span>
        </div>
        <div style="display:flex; align-items:center; gap:4px;">
          <button class="icon-btn love-btn ${isFav ? 'loved active' : ''}" data-video-id="${video.id}" title="${isFav ? 'Remove from Favorites' : 'Add to Favorites'}">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
            </svg>
          </button>
          <a href="/api/stream/${video.id}?download=true" class="icon-btn" title="Save Video to Device over Wi-Fi" download>
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          </a>
          ${isOwner ? `
            <button class="icon-btn delete-media-btn" data-video-id="${video.id}" title="Delete file from server">
              <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          ` : ''}
        </div>
      </div>
    `;

    card.querySelector('.video-thumb-wrapper').addEventListener('click', () => {
      openVideoPlayer(video);
    });

    const loveBtn = card.querySelector('.love-btn');
    if (loveBtn) {
      loveBtn.addEventListener('click', (e) => toggleFavorite(video.id, e));
    }

    const deleteBtn = card.querySelector('.delete-media-btn');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', (e) => deleteMedia(video.id, video.title || 'video', e));
    }

    targetEl.appendChild(card);
  });
}

function renderFavorites(items) {
  const musicItems = items.filter(i => (i.media_type || 'audio') === 'audio');
  const videoItems = items.filter(i => i.media_type === 'video');

  if (!items || items.length === 0) {
    if (favoritesEmptyEl) favoritesEmptyEl.classList.remove('hidden');
    if (favoritesSongListEl) favoritesSongListEl.innerHTML = '';
    if (favoritesVideoGridEl) favoritesVideoGridEl.innerHTML = '';
    return;
  }
  if (favoritesEmptyEl) favoritesEmptyEl.classList.add('hidden');

  if (musicItems.length > 0) {
    renderSongList(musicItems, favoritesSongListEl);
  } else {
    if (favoritesSongListEl) favoritesSongListEl.innerHTML = '';
  }

  if (videoItems.length > 0) {
    renderVideos(videoItems, favoritesVideoGridEl);
  } else {
    if (favoritesVideoGridEl) favoritesVideoGridEl.innerHTML = '';
  }
}

function openVideoPlayer(video) {
  pauseAudio();
  videoModalTitle.textContent = video.title || 'Playing Video';
  videoEngine.src = video.isLocal ? video.url : `/api/stream/${video.id}`;
  videoModal.classList.remove('hidden');
  videoEngine.play().catch(e => console.warn('Video autoplay prevented:', e));
}

videoModalClose.addEventListener('click', () => {
  videoEngine.pause();
  videoEngine.src = '';
  videoModal.classList.add('hidden');
});

function renderPeers(peers, clients = []) {
  if (clientsCountBadge) clientsCountBadge.textContent = `${clients.length}`;
  if (meshCountBadge) meshCountBadge.textContent = `${peers.length}`;

  if (clientsListEl) {
    clientsListEl.innerHTML = '';
    if (!clients || clients.length === 0) {
      clientsListEl.innerHTML = `
        <div style="grid-column: 1/-1; padding: 24px; text-align: center; color: var(--text-muted); background: var(--bg-surface); border-radius: 12px; border: 1px solid var(--border-subtle);">
          <p>No mobile phones or other web players connected yet.</p>
          <p style="font-size: 0.85rem; margin-top: 6px;">Scan the QR code from your phone camera to connect!</p>
        </div>
      `;
    } else {
      clients.forEach(c => {
        const card = document.createElement('div');
        card.className = 'peer-card';
        card.innerHTML = `
          <div class="peer-icon" style="color: #818cf8;">
            <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
              <line x1="12" y1="18" x2="12.01" y2="18"></line>
            </svg>
          </div>
          <div class="peer-info">
            <div style="display:flex; align-items:center; gap:6px;">
              <h4 style="margin:0;">${escapeHtml(c.device_name)}</h4>
              <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981;"></span>
            </div>
            <p style="margin:2px 0 0;">IP: ${c.ip} • Online Web Player</p>
          </div>
        `;
        clientsListEl.appendChild(card);
      });
    }
  }

  peersListEl.innerHTML = '';
  if (!peers || peers.length === 0) {
    peersListEl.innerHTML = `
      <div style="grid-column: 1/-1; padding: 24px; text-align: center; color: var(--text-muted); background: var(--bg-surface); border-radius: 12px; border: 1px solid var(--border-subtle);">
        <p>No other laptop servers broadcasting on this Wi-Fi.</p>
        <p style="font-size: 0.85rem; margin-top: 6px;">Run MediaHub on other computers to automatically mesh libraries!</p>
      </div>
    `;
    return;
  }

  peers.forEach(peer => {
    const card = document.createElement('div');
    card.className = 'peer-card';
    card.innerHTML = `
      <div class="peer-icon" style="color: #34d399;">
        <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
          <line x1="8" y1="21" x2="16" y2="21"></line>
          <line x1="12" y1="17" x2="12" y2="21"></line>
        </svg>
      </div>
      <div class="peer-info">
        <h4>${escapeHtml(peer.device_name)}</h4>
        <p>${peer.host}:${peer.port} • ${peer.music_count} songs • ${peer.video_count} videos</p>
      </div>
    `;
    peersListEl.appendChild(card);
  });
}

if (refreshPeersBtn) {
  refreshPeersBtn.addEventListener('click', () => {
    fetchPeers();
    fetchStatus();
  });
}

function renderSharedFolders(folders) {
  sharedFoldersListEl.innerHTML = '';
  if (!folders || folders.length === 0) {
    sharedFoldersListEl.innerHTML = '<p class="placeholder-text">No folders shared yet. Click "Add Folder" to share.</p>';
    return;
  }

  folders.forEach(folder => {
    const item = document.createElement('div');
    item.className = 'folder-item';
    item.innerHTML = `
      <div>
        <strong>${escapeHtml(folder.name || 'Folder')}</strong>
        <div class="folder-path">${escapeHtml(folder.path)} (${folder.type})</div>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <label class="switch" style="transform: scale(0.8);">
          <input type="checkbox" class="folder-toggle" ${folder.enabled ? 'checked' : ''}>
          <span class="slider round"></span>
        </label>
        <button class="icon-btn delete-folder-btn" title="Remove Folder">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="#ef4444" stroke-width="2" fill="none">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;

    item.querySelector('.folder-toggle').addEventListener('change', async (e) => {
      await apiFetch(`/api/settings/folders/${folder.id}/toggle?enabled=${e.target.checked}`, { method: 'POST' });
      fetchSettings();
    });

    item.querySelector('.delete-folder-btn').addEventListener('click', async () => {
      if (confirm(`Remove folder "${folder.name}" from sharing?`)) {
        await apiFetch(`/api/settings/folders/${folder.id}`, { method: 'DELETE' });
        fetchSettings();
      }
    });

    sharedFoldersListEl.appendChild(item);
  });
}

// --- Downloader Operations ---
startDownloadBtn.addEventListener('click', async () => {
  const url = dlUrlInput.value.trim();
  if (!url) {
    alert('Please paste a YouTube or Spotify link');
    return;
  }

  const format = document.querySelector('input[name="dl-format"]:checked').value;
  const quality = dlQualitySelect.value;

  try {
    startDownloadBtn.disabled = true;
    startDownloadBtn.textContent = 'Starting...';

    const res = await apiFetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        format,
        quality,
        client_id: clientId,
        device_name: getDeviceType()
      })
    });

    const data = await res.json();
    dlUrlInput.value = '';
    pollDownloads();
  } catch (err) {
    alert(`Download failed to start: ${err}`);
  } finally {
    startDownloadBtn.disabled = false;
    startDownloadBtn.innerHTML = `
      <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      <span>Download</span>
    `;
  }
});

let dlPollInterval = null;
let lastKnownCompleted = new Set();

async function pollDownloads() {
  try {
    const res = await apiFetch('/api/downloads/status');
    const data = await res.json();
    state.downloads = data.tasks;
    renderDownloads(data.tasks);

    let hasNewCompletion = false;
    data.tasks.forEach(t => {
      if (t.status === 'completed' && !lastKnownCompleted.has(t.id)) {
        lastKnownCompleted.add(t.id);
        hasNewCompletion = true;
      }
    });

    if (hasNewCompletion) {
      fetchStatus();
      fetchSongs();
      fetchVideos();
      fetchFavorites();
    }

    const hasActive = data.tasks.some(t => t.status === 'downloading' || t.status === 'pending' || t.status === 'processing');
    if (hasActive && !dlPollInterval) {
      dlPollInterval = setInterval(pollDownloads, 1500);
    } else if (!hasActive && dlPollInterval) {
      clearInterval(dlPollInterval);
      dlPollInterval = null;
      fetchStatus();
      fetchSongs();
      fetchVideos();
      fetchFavorites();
    }
  } catch (e) {}
}

async function playSongById(songId) {
  try {
    const res = await apiFetch(`/api/song/${songId}`);
    if (res.ok) {
      const song = await res.json();
      const existingIdx = state.allSongs.findIndex(s => s.id === song.id);
      if (existingIdx !== -1) {
        playFromList(state.allSongs, existingIdx);
      } else {
        playFromList([song, ...state.allSongs], 0);
      }
    }
  } catch (e) {
    console.error('Error playing downloaded song:', e);
  }
}

function renderDownloads(tasks) {
  if (!tasks || tasks.length === 0) {
    downloadsQueueEl.innerHTML = '<p class="placeholder-text">No active downloads.</p>';
    return;
  }

  downloadsQueueEl.innerHTML = '';
  tasks.slice().reverse().forEach(task => {
    const item = document.createElement('div');
    item.className = 'download-task-item';
    const isDone = task.status === 'completed';

    item.innerHTML = `
      <div class="download-task-header">
        <span class="task-title">${escapeHtml(task.title || task.url)}</span>
        <div style="display:flex; align-items:center; gap:8px;">
          ${isDone && task.song_id ? `
            <button class="primary-btn play-dl-btn" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px;">
              ▶️ Play
            </button>
          ` : ''}
          <span class="task-status-badge ${task.status}">${task.status}</span>
        </div>
      </div>
      <div class="download-progress-track">
        <div class="download-progress-bar" style="width: ${task.progress || (isDone ? 100 : 0)}%"></div>
      </div>
    `;

    if (isDone && task.song_id) {
      const playBtn = item.querySelector('.play-dl-btn');
      if (playBtn) {
        playBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          playSongById(task.song_id);
        });
      }
    }

    downloadsQueueEl.appendChild(item);
  });
}

// --- Privacy Settings Handlers ---
masterSharingToggle.addEventListener('change', async (e) => {
  await apiFetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sharing_enabled: e.target.checked })
  });
  fetchStatus();
  fetchSongs();
  fetchVideos();
  fetchFavorites();
});

saveDeviceNameBtn.addEventListener('click', async () => {
  const name = deviceNameInput.value.trim();
  if (name) {
    await apiFetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_name: name })
    });
    fetchStatus();
  }
});

addFolderBtn.addEventListener('click', async () => {
  const folderPath = prompt('Enter absolute folder path to share (e.g. D:\\Movies or C:\\Users\\...\\Music):');
  if (folderPath && folderPath.trim()) {
    const folderName = prompt('Enter a label/name for this folder:', 'My Shared Folder');
    const folderType = prompt('Enter media type (both / music / video):', 'both');
    try {
      const res = await apiFetch('/api/settings/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: folderPath.trim(), name: folderName, type: folderType || 'both' })
      });
      if (res.ok) {
        fetchSettings();
        fetchStatus();
        fetchSongs();
        fetchVideos();
        fetchFavorites();
      } else {
        const err = await res.json();
        alert(`Could not add folder: ${err.detail}`);
      }
    } catch (e) {
      alert(`Error: ${e}`);
    }
  }
});

// Render Artists, Albums, Playlists
function renderArtists(artists) {
  artistsGridEl.innerHTML = '';
  artists.forEach(artist => {
    const card = document.createElement('div');
    card.className = 'media-card artist-card';
    const coverUrl = artist.cover_hash ? `/api/cover/${artist.artist}` : '/icon.svg';
    card.innerHTML = `
      <img class="media-card-img" src="${coverUrl}" alt="" loading="lazy">
      <span class="media-card-title">${escapeHtml(artist.artist)}</span>
      <span class="media-card-subtitle">${artist.song_count} songs • ${artist.album_count} albums</span>
    `;
    card.addEventListener('click', () => openArtistDetail(artist.artist));
    artistsGridEl.appendChild(card);
  });
}

function renderAlbums(albums) {
  albumsGridEl.innerHTML = '';
  albums.forEach(album => {
    const card = document.createElement('div');
    card.className = 'media-card';
    const coverUrl = album.cover_hash ? `/api/cover/${album.album}` : '/icon.svg';
    card.innerHTML = `
      <img class="media-card-img" src="${coverUrl}" alt="" loading="lazy">
      <span class="media-card-title">${escapeHtml(album.album)}</span>
      <span class="media-card-subtitle">${escapeHtml(album.artist || 'Various Artists')} ${album.year ? '• ' + album.year : ''}</span>
    `;
    card.addEventListener('click', () => openAlbumDetail(album));
    albumsGridEl.appendChild(card);
  });
}

function renderPlaylists(playlists) {
  playlistsGridEl.innerHTML = '';
  playlists.forEach(pl => {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.innerHTML = `
      <div class="media-card-img" style="display:flex; align-items:center; justify-content:center; background: var(--bg-surface);">
        <svg viewBox="0 0 24 24" width="44" height="44" stroke="var(--accent)" stroke-width="1.5" fill="none">
          <line x1="8" y1="6" x2="21" y2="6"></line>
          <line x1="8" y1="12" x2="21" y2="12"></line>
          <line x1="8" y1="18" x2="21" y2="18"></line>
          <line x1="3" y1="6" x2="3.01" y2="6"></line>
          <line x1="3" y1="12" x2="3.01" y2="12"></line>
          <line x1="3" y1="18" x2="3.01" y2="18"></line>
        </svg>
      </div>
      <span class="media-card-title">${escapeHtml(pl.name)}</span>
      <span class="media-card-subtitle">${pl.song_count} songs</span>
    `;
    card.addEventListener('click', () => openPlaylistDetail(pl));
    playlistsGridEl.appendChild(card);
  });
}

function renderQueue() {
  queueListEl.innerHTML = '';
  state.queue.forEach((song, idx) => {
    const isCurrent = idx === state.currentIndex;
    const item = document.createElement('div');
    item.className = `song-row ${isCurrent ? 'playing' : ''}`;
    item.innerHTML = `
      <img class="song-cover-thumb" src="${getCoverUrl(song)}" alt="" style="width:36px;height:36px;">
      <div class="song-details">
        <span class="song-title">${escapeHtml(song.title)}</span>
        <span class="song-subtitle">${escapeHtml(song.artist)}</span>
      </div>
      <span class="song-duration">${formatTime(song.duration)}</span>
    `;
    item.addEventListener('click', () => loadTrack(idx, true));
    queueListEl.appendChild(item);
  });
}

// Detail Drilldown
async function openArtistDetail(artistName) {
  try {
    const res = await apiFetch(`/api/songs?artist=${encodeURIComponent(artistName)}`);
    const data = await res.json();
    const songs = data.songs;
    detailType.textContent = 'ARTIST';
    detailTitle.textContent = artistName;
    detailSubtitle.textContent = `${songs.length} songs`;
    detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';
    renderSongList(songs, detailSongList, true);
    detailPlayBtn.onclick = () => playFromList(songs, 0);
    switchView('detail');
  } catch (err) {}
}

async function openAlbumDetail(album) {
  try {
    const res = await apiFetch(`/api/songs?album=${encodeURIComponent(album.album)}&sort_by=track_number`);
    const data = await res.json();
    const songs = data.songs;
    detailType.textContent = 'ALBUM';
    detailTitle.textContent = album.album;
    detailSubtitle.textContent = `${album.artist} ${album.year ? '• ' + album.year : ''} • ${songs.length} songs`;
    detailCoverImg.src = album.cover_hash ? `/api/cover/${album.album}` : (songs[0] ? getCoverUrl(songs[0]) : '/icon.svg');
    renderSongList(songs, detailSongList, true);
    detailPlayBtn.onclick = () => playFromList(songs, 0);
    switchView('detail');
  } catch (err) {}
}

async function openPlaylistDetail(playlist) {
  try {
    const res = await apiFetch(`/api/playlists/${playlist.id}/songs`);
    const data = await res.json();
    const songs = data.songs;
    detailType.textContent = 'PLAYLIST';
    detailTitle.textContent = playlist.name;
    detailSubtitle.textContent = `${songs.length} songs`;
    detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';
    renderSongList(songs, detailSongList, true);
    detailPlayBtn.onclick = () => playFromList(songs, 0);
    switchView('detail');
  } catch (err) {}
}

// Player Logic
function playFromList(list, index) {
  state.queue = [...list];
  loadTrack(index, true);
}

function loadTrack(index, autoPlay = true) {
  if (index < 0 || index >= state.queue.length) return;
  state.currentIndex = index;
  const song = state.queue[index];
  state.currentTrack = song;

  audio.src = song.isLocal ? song.url : `/api/stream/${song.id}`;
  const coverUrl = song.isLocal ? '/icon.svg' : getCoverUrl(song);

  miniTitle.textContent = song.title || 'Unknown Title';
  miniArtist.textContent = song.artist || 'Unknown Artist';
  miniCover.src = coverUrl;

  fullTitle.textContent = song.title || 'Unknown Title';
  fullArtist.textContent = song.artist || 'Unknown Artist';
  fullAlbum.textContent = song.album || '';
  fullCover.src = coverUrl;
  totalDurationEl.textContent = formatTime(song.duration);
  seekSlider.value = 0;
  currentTimeEl.textContent = '0:00';

  updatePlayerLoveButton(song.is_favorite);

  document.querySelectorAll('.song-row').forEach(row => {
    row.classList.toggle('playing', row.dataset.songId === song.id);
  });

  updateMediaSession(song, coverUrl);
  if (autoPlay) playAudio();
  renderQueue();
}

function playAudio() {
  audio.play().then(() => {
    state.isPlaying = true;
    updatePlayIcons(true);
    if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
  }).catch(e => console.warn(e));
}

function pauseAudio() {
  audio.pause();
  state.isPlaying = false;
  updatePlayIcons(false);
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
}

function togglePlay() {
  if (state.currentIndex === -1) {
    if (state.allSongs.length > 0) playFromList(state.allSongs, 0);
    return;
  }
  if (state.isPlaying) pauseAudio();
  else playAudio();
}

function nextTrack() {
  if (state.queue.length === 0) return;
  if (state.isShuffle) {
    const nextIdx = Math.floor(Math.random() * state.queue.length);
    loadTrack(nextIdx, true);
    return;
  }
  if (state.currentIndex + 1 < state.queue.length) {
    loadTrack(state.currentIndex + 1, true);
  } else if (state.repeatMode === 'all') {
    loadTrack(0, true);
  }
}

function prevTrack() {
  if (audio.currentTime > 3) {
    audio.currentTime = 0;
    return;
  }
  if (state.currentIndex > 0) {
    loadTrack(state.currentIndex - 1, true);
  } else if (state.queue.length > 0) {
    loadTrack(state.queue.length - 1, true);
  }
}

function updatePlayIcons(playing) {
  const playSvg = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
  const pauseSvg = '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>';
  miniPlayIcon.innerHTML = playing ? pauseSvg : playSvg;
  fullPlayIcon.innerHTML = playing ? pauseSvg : playSvg;
}

function updateMediaSession(song, coverUrl) {
  if (!('mediaSession' in navigator)) return;
  const absoluteCover = new URL(coverUrl, window.location.href).href;
  navigator.mediaSession.metadata = new MediaMetadata({
    title: song.title || 'Unknown Title',
    artist: song.artist || 'Unknown Artist',
    album: song.album || 'Unknown Album',
    artwork: [{ src: absoluteCover, sizes: '512x512', type: 'image/jpeg' }]
  });
  navigator.mediaSession.setActionHandler('play', playAudio);
  navigator.mediaSession.setActionHandler('pause', pauseAudio);
  navigator.mediaSession.setActionHandler('previoustrack', prevTrack);
  navigator.mediaSession.setActionHandler('nexttrack', nextTrack);
}

audio.addEventListener('timeupdate', () => {
  if (!audio.duration) return;
  const current = audio.currentTime;
  const total = audio.duration;
  const percent = (current / total) * 100;
  seekSlider.value = percent;
  miniProgressFill.style.width = `${percent}%`;
  currentTimeEl.textContent = formatTime(current);
});

audio.addEventListener('ended', () => {
  if (state.repeatMode === 'one') {
    audio.currentTime = 0;
    playAudio();
  } else {
    nextTrack();
  }
});

// View Navigation
function switchView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item, .bottom-nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.view === viewName);
  });

  const activeViewEl = document.getElementById(`view-${viewName}`);
  if (activeViewEl) activeViewEl.classList.add('active');

  if (viewName === 'my-device') fetchMyMedia();
  if (viewName === 'songs') fetchSongs();
  if (viewName === 'videos') fetchVideos();
  if (viewName === 'favorites') fetchFavorites();
  if (viewName === 'downloader') pollDownloads();
  if (viewName === 'peers') fetchPeers();
  if (viewName === 'privacy') fetchSettings();
  if (viewName === 'artists' && state.artists.length === 0) fetchArtists();
  if (viewName === 'albums' && state.albums.length === 0) fetchAlbums();
  if (viewName === 'playlists' && state.playlists.length === 0) fetchPlaylists();
}

document.querySelectorAll('.nav-item, .bottom-nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

detailBackBtn.addEventListener('click', () => switchView('songs'));

miniPlayerClickTarget.addEventListener('click', () => fullPlayer.classList.add('open'));
fullPlayerClose.addEventListener('click', () => fullPlayer.classList.remove('open'));

if (fullLoveBtn) {
  fullLoveBtn.addEventListener('click', (e) => {
    if (state.currentTrack) toggleFavorite(state.currentTrack.id, e);
  });
}

if (miniLoveBtn) {
  miniLoveBtn.addEventListener('click', (e) => {
    if (state.currentTrack) toggleFavorite(state.currentTrack.id, e);
  });
}

document.querySelectorAll('input[name="fav-filter"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    state.favFilter = e.target.value;
    fetchFavorites();
  });
});

miniPlayBtn.addEventListener('click', togglePlay);
playBtn.addEventListener('click', togglePlay);
miniNextBtn.addEventListener('click', nextTrack);
nextBtn.addEventListener('click', nextTrack);
miniPrevBtn.addEventListener('click', prevTrack);
prevBtn.addEventListener('click', prevTrack);

seekSlider.addEventListener('input', (e) => {
  if (audio.duration) {
    audio.currentTime = (e.target.value / 100) * audio.duration;
  }
});

volumeSlider.addEventListener('input', (e) => {
  audio.volume = e.target.value;
});

shuffleBtn.addEventListener('click', () => {
  state.isShuffle = !state.isShuffle;
  shuffleBtn.classList.toggle('active', state.isShuffle);
});

repeatBtn.addEventListener('click', () => {
  if (state.repeatMode === 'off') {
    state.repeatMode = 'all';
    repeatBtn.classList.add('active');
  } else if (state.repeatMode === 'all') {
    state.repeatMode = 'one';
    repeatBtn.style.color = '#ec4899';
  } else {
    state.repeatMode = 'off';
    repeatBtn.classList.remove('active');
    repeatBtn.style.color = '';
  }
});

queueToggleBtn.addEventListener('click', () => queuePanel.classList.toggle('hidden'));
clearQueueBtn.addEventListener('click', () => {
  state.queue = [];
  state.currentIndex = -1;
  state.currentTrack = null;
  pauseAudio();
  audio.src = '';
  renderQueue();
});

// Search
let searchTimeout;
searchInput.addEventListener('input', (e) => {
  clearTimeout(searchTimeout);
  const q = e.target.value.trim();
  clearSearchBtn.classList.toggle('hidden', q.length === 0);
  searchTimeout = setTimeout(() => {
    if (state.currentView === 'videos') fetchVideos(q);
    else if (state.currentView === 'favorites') fetchFavorites();
    else fetchSongs(q, sortSelect.value);
  }, 250);
});

clearSearchBtn.addEventListener('click', () => {
  searchInput.value = '';
  clearSearchBtn.classList.add('hidden');
  if (state.currentView === 'videos') fetchVideos('');
  else if (state.currentView === 'favorites') fetchFavorites();
  else fetchSongs('', sortSelect.value);
});

sortSelect.addEventListener('change', (e) => {
  fetchSongs(searchInput.value.trim(), e.target.value);
});

document.getElementById('play-all-btn').addEventListener('click', () => {
  if (state.filteredSongs.length > 0) playFromList(state.filteredSongs, 0);
});

document.getElementById('rescan-btn').addEventListener('click', triggerScan);
document.getElementById('mobile-rescan-btn').addEventListener('click', triggerScan);

// Playlist Modals
const playlistModal = document.getElementById('playlist-modal');
const playlistModalClose = document.getElementById('playlist-modal-close');
const playlistModalBody = document.getElementById('playlist-modal-body');
playlistModalClose.addEventListener('click', () => playlistModal.classList.add('hidden'));

async function openAddToPlaylistModal(song) {
  await fetchPlaylists();
  playlistModalBody.innerHTML = '';
  if (state.playlists.length === 0) {
    playlistModalBody.innerHTML = '<p style="color:var(--text-muted);">No playlists yet. Create one first!</p>';
  } else {
    state.playlists.forEach(pl => {
      const btn = document.createElement('button');
      btn.className = 'secondary-btn';
      btn.style.marginBottom = '8px';
      btn.textContent = pl.name;
      btn.onclick = async () => {
        await apiFetch(`/api/playlists/${pl.id}/songs/${song.id}`, { method: 'POST' });
        playlistModal.classList.add('hidden');
      };
      playlistModalBody.appendChild(btn);
    });
  }
  playlistModal.classList.remove('hidden');
}

document.getElementById('new-playlist-btn').addEventListener('click', async () => {
  const name = prompt('Enter playlist name:');
  if (name && name.trim()) {
    await apiFetch('/api/playlists', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name.trim() })
    });
    fetchPlaylists();
  }
});

// File Upload from Phone / Device
const mediaUploadInput = document.getElementById('media-upload-input');
const uploadMusicBtn = document.getElementById('upload-music-btn');
const uploadVideoBtn = document.getElementById('upload-video-btn');

if (uploadMusicBtn) uploadMusicBtn.addEventListener('click', () => mediaUploadInput.click());
if (uploadVideoBtn) uploadVideoBtn.addEventListener('click', () => mediaUploadInput.click());

if (mediaUploadInput) {
  mediaUploadInput.addEventListener('change', async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('client_id', clientId);
      formData.append('device_name', getDeviceType());

      try {
        serverBadge.textContent = `Sharing ${file.name}...`;
        serverBadge.style.color = '#f59e0b';

        const res = await apiFetch('/api/upload', {
          method: 'POST',
          body: formData
        });

        if (res.ok) {
          const data = await res.json();
          alert(data.message || `Shared ${file.name} successfully!`);
        } else {
          alert(`Failed to share ${file.name}`);
        }
      } catch (err) {
        alert(`Upload error: ${err}`);
      }
    }

    mediaUploadInput.value = '';
    fetchStatus();
    fetchSongs();
    fetchVideos();
    fetchFavorites();
  });
}

// Native System Share Target Handler (1-Click Sharing from YouTube / Gallery)
function checkIncomingShares() {
  const params = new URLSearchParams(window.location.search);
  const sharedUrl = params.get('shared_url');
  const sharedFiles = params.get('shared_files');

  if (sharedUrl) {
    window.history.replaceState({}, document.title, '/');
    switchView('downloader');
    dlUrlInput.value = sharedUrl;
    // 1-Click Auto Trigger Download
    setTimeout(() => {
      startDownloadBtn.click();
    }, 400);
  } else if (sharedFiles) {
    window.history.replaceState({}, document.title, '/');
    alert(`Successfully shared ${sharedFiles} file(s) with everyone on Wi-Fi!`);
    fetchVideos();
    fetchSongs();
    fetchFavorites();
    switchView('videos');
  }
}

// QR Code Connect Modal Handlers
const qrModal = document.getElementById('qr-modal');
const qrModalBtn = document.getElementById('qr-modal-btn');
const qrModalClose = document.getElementById('qr-modal-close');
const qrCodeImg = document.getElementById('qr-code-img');
const qrConnectUrl = document.getElementById('qr-connect-url');
const qrIpSelect = document.getElementById('qr-ip-select');
const copyQrUrlBtn = document.getElementById('copy-qr-url-btn');
const shareLinkBtn = document.getElementById('share-link-btn');

async function openQrModal() {
  let availableIps = state.availableIps || [];
  let defaultUrl = state.connectUrl;

  // If page is accessed directly via a real IP (e.g. on phone), use origin
  if (!window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
    defaultUrl = window.location.origin;
  }

  if (!defaultUrl) {
    try {
      const res = await apiFetch('/api/status');
      const data = await res.json();
      defaultUrl = data.connect_url;
      availableIps = data.available_ips || [data.local_ip];
    } catch (e) {
      defaultUrl = window.location.origin;
    }
  }

  if (qrIpSelect && availableIps.length > 0) {
    qrIpSelect.innerHTML = '';
    const currentPort = window.location.port || '8000';
    
    availableIps.forEach(ip => {
      const optUrl = `http://${ip}:${currentPort}`;
      const opt = document.createElement('option');
      opt.value = optUrl;
      const isLan = ip.startsWith('192.168.') || ip.startsWith('10.');
      opt.textContent = `${ip} ${isLan ? '★ (Wi-Fi / LAN Recommended)' : '(Virtual / Hotspot)'}`;
      if (defaultUrl && defaultUrl.includes(ip)) {
        opt.selected = true;
      }
      qrIpSelect.appendChild(opt);
    });

    qrIpSelect.onchange = () => {
      const chosen = qrIpSelect.value;
      qrConnectUrl.textContent = chosen;
      qrCodeImg.src = `/api/qr?url=${encodeURIComponent(chosen)}`;
    };
  }

  const activeUrl = (qrIpSelect && qrIpSelect.value) ? qrIpSelect.value : (defaultUrl || window.location.origin);
  qrConnectUrl.textContent = activeUrl;
  qrCodeImg.src = `/api/qr?url=${encodeURIComponent(activeUrl)}`;
  qrModal.classList.remove('hidden');
}

if (qrModalBtn) qrModalBtn.addEventListener('click', openQrModal);
if (qrModalClose) qrModalClose.addEventListener('click', () => qrModal.classList.add('hidden'));

if (copyQrUrlBtn) {
  copyQrUrlBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(qrConnectUrl.textContent);
      copyQrUrlBtn.textContent = 'Copied!';
      setTimeout(() => { copyQrUrlBtn.textContent = 'Copy'; }, 2000);
    } catch (e) {
      alert(`URL: ${qrConnectUrl.textContent}`);
    }
  });
}

if (shareLinkBtn) {
  shareLinkBtn.addEventListener('click', async () => {
    const url = qrConnectUrl.textContent;
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'MediaHub',
          text: 'Connect to MediaHub to stream music & movies over local Wi-Fi with 0 MB internet data:',
          url: url
        });
      } catch (e) {}
    } else {
      await navigator.clipboard.writeText(url);
      alert('Link copied to clipboard! Paste in WhatsApp/Telegram to share.');
    }
  });
}

// Smart TV & VLC Modal Handlers
const tvModal = document.getElementById('tv-modal');
const tvModalBtn = document.getElementById('tv-modal-btn');
const tvModalClose = document.getElementById('tv-modal-close');
const tvM3uAllUrl = document.getElementById('tv-m3u-all-url');
const tvM3uMoviesUrl = document.getElementById('tv-m3u-movies-url');

function openTvModal() {
  const base = state.connectUrl || window.location.origin;
  if (tvM3uAllUrl) tvM3uAllUrl.textContent = `${base}/api/playlist.m3u`;
  if (tvM3uMoviesUrl) tvM3uMoviesUrl.textContent = `${base}/api/playlist/movies.m3u`;
  if (tvModal) tvModal.classList.remove('hidden');
}

if (tvModalBtn) tvModalBtn.addEventListener('click', openTvModal);
if (tvModalClose) tvModalClose.addEventListener('click', () => tvModal.classList.add('hidden'));

document.querySelectorAll('.copy-m3u-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const targetId = btn.dataset.target;
    const targetEl = document.getElementById(targetId);
    if (targetEl) {
      try {
        await navigator.clipboard.writeText(targetEl.textContent);
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = originalText; }, 2000);
      } catch (e) {
        alert(`URL: ${targetEl.textContent}`);
      }
    }
  });
});

// My Device & Quick Actions Event Handlers
if (quickShareBtn) quickShareBtn.addEventListener('click', () => mediaUploadInput.click());
if (emptyShareTriggerBtn) emptyShareTriggerBtn.addEventListener('click', () => mediaUploadInput.click());
if (quickLocalBtn) quickLocalBtn.addEventListener('click', () => localPlaybackInput.click());
if (addMoreLocalBtn) addMoreLocalBtn.addEventListener('click', () => localPlaybackInput.click());
if (quickMeshBtn) quickMeshBtn.addEventListener('click', () => switchView('songs'));

if (localPlaybackInput) {
  localPlaybackInput.addEventListener('change', (e) => {
    handleLocalDeviceFiles(e.target.files);
    localPlaybackInput.value = '';
  });
}

document.querySelectorAll('input[name="my-media-filter"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    state.myMediaFilter = e.target.value;
    renderMyMedia();
  });
});

// Scope Switcher Tabs (All / My Uploads / Shared Mesh)
document.querySelectorAll('.scope-tabs').forEach(tabGroup => {
  tabGroup.querySelectorAll('.scope-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      tabGroup.querySelectorAll('.scope-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.mediaScope = tab.dataset.scope;
      const target = tabGroup.dataset.target;
      if (target === 'songs') {
        fetchSongs(searchInput.value.trim(), sortSelect.value, state.mediaScope);
      } else if (target === 'videos') {
        fetchVideos(searchInput.value.trim(), state.mediaScope);
      }
    });
  });
});

// Initial Load & Mobile-First Routing
const isMobileDevice = /android|iphone|ipad|ipod/i.test(navigator.userAgent) || window.innerWidth <= 768;
const startingView = isMobileDevice ? 'my-device' : 'songs';

fetchStatus();
if (startingView === 'my-device') {
  fetchMyMedia();
  switchView('my-device');
} else {
  fetchSongs();
  switchView('songs');
}
fetchFavorites();
checkIncomingShares();
