// State
const state = {
  allSongs: [],
  filteredSongs: [],
  videos: [],
  videoCategory: 'all',
  videoDecade: '',
  videoResolution: '',
  videoSort: 'title',
  photos: [],
  photosTimeline: [],
  photosAlbums: [],
  statusGroups: [],
  activeStatusGroupIndex: -1,
  activeStatusItemIndex: -1,
  statusTimer: null,
  statusProgressInterval: null,
  selectedStatusFile: null,
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
  pendingUploads: [],
  uploadApprovalRequired: false,
  connectUrl: '',
  availableIps: [],
  settings: {},
  downloads: [],
  globalActive: false,
  globalStatus: 'stopped',
  globalUrl: null,
  globalEnabled: false,
  genres: [],
  languages: [],
  yearsData: null,
  selectedGenre: '',
  selectedLanguage: '',
  selectedYear: '',
  selectedDecade: '',
  currentPlaylist: null,
  smartPlaylists: [],
  activePlaylistTab: 'all',
  activeRibbonFilter: 'all',
  activeSubRibbon: null,
  selectedSongIds: new Set(),
  isBatchMode: false,
  playbackSpeed: 1.0,
  sleepTimerEnd: null,
  sleepTimerInterval: null,
  sleepAtTrackEnd: false,
  isEqualizerEnabled: true,
  currentPreset: 'flat',
  eqGains: [0, 0, 0, 0, 0]
};

// Client Heartbeat Identifier
let clientId = localStorage.getItem('mediahub_client_id');
if (!clientId) {
  clientId = 'client_' + Math.random().toString(36).substring(2, 10);
  localStorage.setItem('mediahub_client_id', clientId);
}

function getDeviceType() {
  const custom = localStorage.getItem('mediahub_user_name');
  if (custom && custom.trim()) return custom.trim();
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
  const adminToken = localStorage.getItem('media_admin_token');
  if (adminToken && adminToken.trim()) {
    headers['X-Admin-Token'] = adminToken.trim();
  }
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
const detailShuffleBtn = document.getElementById('detail-shuffle-btn');
const detailDownloadBtn = document.getElementById('detail-download-btn');
const detailShareBtn = document.getElementById('detail-share-btn');
const detailAddSongsBtn = document.getElementById('detail-add-songs-btn');
const detailDeleteBtn = document.getElementById('detail-delete-btn');
const detailSaveCustomBtn = document.getElementById('detail-save-custom-btn');

// Quick Filter Ribbon & Smart Combo Elements
const songQuickRibbon = document.getElementById('song-quick-ribbon');
const subRibbonLanguages = document.getElementById('sub-ribbon-languages');
const subRibbonEras = document.getElementById('sub-ribbon-eras');
const subRibbonSmartMixes = document.getElementById('sub-ribbon-smart-mixes');
const smartComboBanner = document.getElementById('smart-combo-banner');
const smartComboTitle = document.getElementById('smart-combo-title');
const smartComboSubtitle = document.getElementById('smart-combo-subtitle');
const smartComboPlayBtn = document.getElementById('smart-combo-play-btn');
const smartComboShuffleBtn = document.getElementById('smart-combo-shuffle-btn');
const smartComboSaveBtn = document.getElementById('smart-combo-save-btn');
const smartComboCloseBtn = document.getElementById('smart-combo-close-btn');

// Playlists View Elements
const importPlaylistBtn = document.getElementById('import-playlist-btn');
const playlistFileImportInput = document.getElementById('playlist-file-import-input');
const plTabAll = document.getElementById('pl-tab-all');
const plTabSmart = document.getElementById('pl-tab-smart');
const plTabCustom = document.getElementById('pl-tab-custom');

// Genres, Languages & Years Elements
const genresGridEl = document.getElementById('genres-grid');
const languagesGridEl = document.getElementById('languages-grid');
const decadesGridEl = document.getElementById('decades-grid');
const yearsPillsEl = document.getElementById('years-pills');
const filterGenreSelect = document.getElementById('filter-genre-select');
const filterLanguageSelect = document.getElementById('filter-language-select');
const filterYearSelect = document.getElementById('filter-year-select');
const clearMusicFiltersBtn = document.getElementById('clear-music-filters-btn');
const batchSelectBtn = document.getElementById('batch-select-btn');
const batchActionBar = document.getElementById('batch-action-bar');
const batchCountLabel = document.getElementById('batch-count-label');
const batchAddPlaylistBtn = document.getElementById('batch-add-playlist-btn');
const batchDownloadZipBtn = document.getElementById('batch-download-zip-btn');
const batchCancelBtn = document.getElementById('batch-cancel-btn');
const dlPlaylistSelect = document.getElementById('dl-playlist-select');

// Player Options Elements
const sleepToggleBtn = document.getElementById('sleep-toggle-btn');
const sleepBadge = document.getElementById('sleep-badge');
const eqToggleBtn = document.getElementById('eq-toggle-btn');
const speedToggleBtn = document.getElementById('speed-toggle-btn');
const fullAddPlBtn = document.getElementById('full-add-pl-btn');
const fullDownloadBtn = document.getElementById('full-download-btn');
const fullShareBtn = document.getElementById('full-share-btn');
const volumeMuteBtn = document.getElementById('volume-mute-btn');
const volumeIcon = document.getElementById('volume-icon');
const seekHoverTooltip = document.getElementById('seek-hover-tooltip');
const audioVisualizerCanvas = document.getElementById('audio-visualizer-canvas');

// Downloader Elements
const dlUrlInput = document.getElementById('dl-url-input');
const dlQualitySelect = document.getElementById('dl-quality-select');
const dlCookiesSelect = document.getElementById('dl-cookies-select');
const startDownloadBtn = document.getElementById('start-download-btn');
const clearDownloadsBtn = document.getElementById('clear-downloads-btn');

// Privacy Elements
const masterSharingToggle = document.getElementById('master-sharing-toggle');
const deviceNameInput = document.getElementById('device-name-input');
const saveDeviceNameBtn = document.getElementById('save-device-name-btn');
const addFolderBtn = document.getElementById('add-folder-btn');

// Photos Elements
const photosTimelineContainer = document.getElementById('photos-timeline-container');
const photosCountBadge = document.getElementById('photos-count-badge');
const photosAlbumFilter = document.getElementById('photos-album-filter');
const uploadPhotosBtn = document.getElementById('upload-photos-btn');
const photoUploadInput = document.getElementById('photo-upload-input');

// Lightbox Elements
const photoLightboxModal = document.getElementById('photo-lightbox-modal');
const lightboxTitle = document.getElementById('lightbox-title');
const lightboxMeta = document.getElementById('lightbox-meta');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxPrevBtn = document.getElementById('lightbox-prev-btn');
const lightboxNextBtn = document.getElementById('lightbox-next-btn');
const lightboxDownloadBtn = document.getElementById('lightbox-download-btn');
const lightboxDeleteBtn = document.getElementById('lightbox-delete-btn');
const lightboxCloseBtn = document.getElementById('lightbox-close-btn');
const lightboxVlcBtn = document.getElementById('lightbox-vlc-btn');

// 24-Hour Ephemeral Status & Field Monitoring Elements
const storiesSection = document.getElementById('stories-section');
const storiesCarousel = document.getElementById('stories-carousel');
const activeStatusBadge = document.getElementById('active-status-badge');
const postStatusBtn = document.getElementById('post-status-btn');
const postStatusModal = document.getElementById('post-status-modal');
const closePostStatusModalBtn = document.getElementById('close-post-status-modal-btn');
const cancelPostStatusBtn = document.getElementById('cancel-post-status-btn');
const statusUploadDropzone = document.getElementById('status-upload-dropzone');
const statusFileInput = document.getElementById('status-file-input');
const statusPreviewImg = document.getElementById('status-preview-img');
const statusDropzonePlaceholder = document.getElementById('status-dropzone-placeholder');
const statusCaptionInput = document.getElementById('status-caption-input');
const submitPostStatusBtn = document.getElementById('submit-post-status-btn');

// Story Viewer Modal Elements
const storyViewerModal = document.getElementById('story-viewer-modal');
const storyViewerBackdrop = document.getElementById('story-viewer-backdrop');
const storyProgressContainer = document.getElementById('story-progress-container');
const storyAvatarSmall = document.getElementById('story-avatar-small');
const storyUsername = document.getElementById('story-username');
const storyMeta = document.getElementById('story-meta');
const storySaveBtn = document.getElementById('story-save-btn');
const storyDownloadBtn = document.getElementById('story-download-btn');
const storyDeleteBtn = document.getElementById('story-delete-btn');
const storyCloseBtn = document.getElementById('story-close-btn');
const storyImg = document.getElementById('story-img');
const storyPrevBtn = document.getElementById('story-prev-btn');
const storyNextBtn = document.getElementById('story-next-btn');
const storyTouchLeft = document.getElementById('story-touch-left');
const storyTouchRight = document.getElementById('story-touch-right');
const storyCaptionBar = document.getElementById('story-caption-bar');
const storyCaptionText = document.getElementById('story-caption-text');

// Approval Queue Elements
const approvalQueueToggle = document.getElementById('approval-queue-toggle');
const approvalQueueStatusBadge = document.getElementById('approval-queue-status-badge');
const pendingUploadsCard = document.getElementById('pending-uploads-card');
const pendingUploadsList = document.getElementById('pending-uploads-list');
const pendingUploadsBadge = document.getElementById('pending-uploads-badge');
const refreshPendingBtn = document.getElementById('refresh-pending-btn');

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
      state.isAdmin = Boolean(data.is_admin);
      state.connectUrl = data.connect_url;
      state.availableIps = data.available_ips || [data.local_ip];
      state.tailscaleIp = data.tailscale_ip || null;
      state.tailscaleUrl = data.tailscale_url || null;
      state.globalActive = Boolean(data.global_active);
      state.globalStatus = data.global_status || 'stopped';
      state.globalUrl = data.global_url || null;
      state.globalEnabled = Boolean(data.global_enabled);
      state.uploadApprovalRequired = Boolean(data.upload_approval_required);
      
      const clientText = data.connected_clients > 0 ? ` (${data.connected_clients} client${data.connected_clients > 1 ? 's' : ''})` : '';
      serverBadge.textContent = data.sharing_enabled ? `Sharing Active${clientText}` : 'Stealth Mode';
      serverBadge.style.color = data.sharing_enabled ? '#10b981' : '#f59e0b';
      brandDeviceName.textContent = data.device_name || 'MediaHub';
      const stats = data.stats;
      const hours = (stats.total_duration / 3600).toFixed(1);
      const photoCountText = stats.total_photos ? ` • ${stats.total_photos} photos` : '';
      libraryStatsHeader.textContent = `${stats.total_songs} songs • ${stats.total_videos} videos${photoCountText} • ${hours} hrs`;

      updateNetworkModeUI();
      if (state.isAdmin) fetchPendingUploads();
      fetchPeersForScope();
    }
  } catch (err) {
    serverBadge.textContent = 'Offline';
    serverBadge.style.color = '#ef4444';
  }
}

function updateNetworkModeUI() {
  const pill = document.getElementById('network-mode-pill');
  const icon = document.getElementById('network-mode-icon');
  const text = document.getElementById('network-mode-text');
  const globalToggle = document.getElementById('global-access-toggle');
  const globalBadge = document.getElementById('global-status-badge');
  const globalDetails = document.getElementById('global-access-details');
  const globalUrlText = document.getElementById('global-access-url-text');

  if (state.globalActive && state.globalUrl) {
    if (pill) {
      pill.style.background = 'rgba(16, 185, 129, 0.15)';
      pill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
      pill.style.color = '#34d399';
    }
    if (icon) icon.textContent = '🌐';
    if (text) text.textContent = 'Mesh + Global';
  } else if (state.globalStatus === 'starting') {
    if (pill) {
      pill.style.background = 'rgba(245, 158, 11, 0.15)';
      pill.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      pill.style.color = '#fbbf24';
    }
    if (icon) icon.textContent = '⏳';
    if (text) text.textContent = 'Starting Global...';
  } else {
    if (pill) {
      pill.style.background = 'rgba(99, 102, 241, 0.12)';
      pill.style.borderColor = 'rgba(99, 102, 241, 0.3)';
      pill.style.color = '#a5b4fc';
    }
    if (icon) icon.textContent = '📶';
    if (text) text.textContent = 'Mesh Mode';
  }

  // Update Settings Privacy View Card
  if (globalToggle) {
    globalToggle.checked = Boolean(state.globalActive || state.globalEnabled);
    globalToggle.disabled = !state.isAdmin;
  }
  if (globalBadge) {
    if (state.globalActive) {
      globalBadge.textContent = 'Active (HTTPS)';
      globalBadge.style.background = 'rgba(16, 185, 129, 0.15)';
      globalBadge.style.color = '#34d399';
    } else if (state.globalStatus === 'starting') {
      globalBadge.textContent = 'Starting...';
      globalBadge.style.background = 'rgba(245, 158, 11, 0.15)';
      globalBadge.style.color = '#fbbf24';
    } else {
      globalBadge.textContent = 'Inactive';
      globalBadge.style.background = 'rgba(148, 163, 184, 0.15)';
      globalBadge.style.color = '#94a3b8';
    }
  }
  if (globalDetails) {
    if (state.globalActive && state.globalUrl) {
      globalDetails.style.display = 'block';
      if (globalUrlText) globalUrlText.textContent = state.globalUrl;
    } else {
      globalDetails.style.display = 'none';
    }
  }

  // Also update QR modal worldwide view if open
  updateGlobalModalPanel();
}

async function fetchSongs(query = '', sortBy = 'title', scope = null, genre = null, language = null, year = null, decade = null) {
  try {
    const activeScope = scope || state.mediaScope || 'all';
    let url = `/api/songs?query=${encodeURIComponent(query)}&sort_by=${sortBy}&scope=${activeScope}`;
    const activeGenre = genre !== null ? genre : state.selectedGenre;
    const activeLang = language !== null ? language : state.selectedLanguage;
    const activeYear = year !== null ? year : state.selectedYear;
    const activeDecade = decade !== null ? decade : state.selectedDecade;

    if (activeGenre) url += `&genre=${encodeURIComponent(activeGenre)}`;
    if (activeLang) url += `&language=${encodeURIComponent(activeLang)}`;
    if (activeYear) url += `&year=${encodeURIComponent(activeYear)}`;
    if (activeDecade) url += `&decade=${encodeURIComponent(activeDecade)}`;

    if (clearMusicFiltersBtn) {
      const hasActive = !!(state.selectedGenre || state.selectedLanguage || state.selectedYear || state.selectedDecade);
      clearMusicFiltersBtn.classList.toggle('hidden', !hasActive);
    }

    const res = await apiFetch(url);
    const data = await res.json();
    let songs = data.songs || [];

    if (activeScope !== 'server') {
      try {
        const liveRes = await apiFetch('/api/peers/shares?media_type=audio');
        const liveData = await liveRes.json();
        let liveShares = (liveData.shares || []).map(s => ({
          ...s,
          isLiveShare: true,
          artist: s.owner_name ? `From ${s.owner_name}` : 'Live Peer Share',
          album: 'Live Peer Stream',
          duration: 0
        }));

        if (activeScope === 'mine') {
          liveShares = liveShares.filter(s => s.is_owner);
        } else if (activeScope.startsWith('peer:')) {
          const targetPeer = activeScope.split(':')[1];
          liveShares = liveShares.filter(s => s.client_id === targetPeer);
        }

        if (query) {
          const q = query.toLowerCase();
          liveShares = liveShares.filter(s => (s.title || '').toLowerCase().includes(q));
        }

        songs = [...liveShares, ...songs];
      } catch (e) {
        console.warn('Failed to fetch live peer audio shares:', e);
      }
    }

    state.allSongs = songs;
    state.filteredSongs = songs;
    renderSongList(state.filteredSongs, songListEl);
    if (typeof updateSmartComboBanner === 'function') {
      updateSmartComboBanner();
    }
  } catch (err) {
    console.error('Error fetching songs:', err);
  }
}

async function fetchVideos(query = '', scope = null) {
  try {
    const activeScope = scope || state.mediaScope || 'all';
    const cat = state.videoCategory || 'all';
    const decade = state.videoDecade || '';
    const resFilter = state.videoResolution || '';
    const sortBy = state.videoSort || 'title';
    let url = `/api/videos?query=${encodeURIComponent(query)}&scope=${activeScope}&sort_by=${sortBy}`;
    if (cat !== 'all') url += `&category=${cat}`;
    if (decade) url += `&decade=${decade}`;
    if (resFilter) url += `&resolution=${encodeURIComponent(resFilter)}`;
    const res = await apiFetch(url);
    const data = await res.json();
    let videos = data.videos || [];

    if (activeScope !== 'server') {
      try {
        const liveRes = await apiFetch('/api/peers/shares?media_type=video');
        const liveData = await liveRes.json();
        let liveShares = (liveData.shares || []).map(s => ({
          ...s,
          isLiveShare: true,
          duration: s.duration || 0,
          resolution: 'Peer Stream',
          mtime: s.created_at
        }));

        if (activeScope === 'mine') {
          liveShares = liveShares.filter(s => s.is_owner);
        } else if (activeScope.startsWith('peer:')) {
          const targetPeer = activeScope.split(':')[1];
          liveShares = liveShares.filter(s => s.client_id === targetPeer);
        }

        if (query) {
          const q = query.toLowerCase();
          liveShares = liveShares.filter(s => (s.title || '').toLowerCase().includes(q));
        }

        videos = [...liveShares, ...videos];
      } catch (e) {
        console.warn('Failed to fetch live peer shares:', e);
      }
    }

    state.videos = videos;
    if (videosCountBadge) videosCountBadge.textContent = `${videos.length} videos`;
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
      <div class="song-meta-right" style="display:flex; align-items:center; gap:6px;">
        <button class="live-share-track-btn secondary-btn" style="padding: 4px 8px; font-size: 0.72rem; border-radius: 6px;" title="Broadcast live to all connected peers without saving to server disk">
          <span>📡 Share Live</span>
        </button>
        <button class="copy-server-track-btn primary-btn" style="padding: 4px 8px; font-size: 0.72rem; border-radius: 6px;" title="Copy permanently to server library for CasaOS">
          <span>📥 Copy to Server</span>
        </button>
      </div>
    `;

    row.addEventListener('click', (e) => {
      if (e.target.closest('.live-share-track-btn') || e.target.closest('.copy-server-track-btn')) return;
      if (track.media_type === 'video') {
        openVideoPlayer(track);
      } else {
        const audioTracks = state.localTracks.filter(t => t.media_type === 'audio');
        playFromList(audioTracks, audioTracks.indexOf(track));
      }
    });

    const liveBtn = row.querySelector('.live-share-track-btn');
    if (liveBtn) {
      liveBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await uploadLivePeerShare(track.file, liveBtn);
      });
    }

    const copyBtn = row.querySelector('.copy-server-track-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await uploadLocalFileDirectly(track.file, copyBtn);
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
    const [resCustom, resSmart] = await Promise.all([
      apiFetch('/api/playlists'),
      apiFetch('/api/playlists/smart')
    ]);
    const dataCustom = await resCustom.json();
    const dataSmart = await resSmart.json();
    state.playlists = dataCustom.playlists || [];
    state.smartPlaylists = dataSmart.smart_playlists || [];
    if (typeof populateSmartSubRibbon === 'function') {
      populateSmartSubRibbon();
    }
    renderPlaylists();
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

    const banner = document.getElementById('admin-notice-banner');
    if (banner) {
      if (state.isAdmin) {
        banner.style.display = 'block';
        banner.style.background = 'rgba(16, 185, 129, 0.1)';
        banner.style.border = '1px solid rgba(16, 185, 129, 0.3)';
        banner.style.color = '#34d399';
        const savedToken = localStorage.getItem('media_admin_token');
        const lockBtnHtml = savedToken ? `<button id="lock-admin-btn" class="secondary-btn" style="padding: 3px 8px; font-size: 0.72rem; margin-left: 8px;">🔒 Lock</button>` : '';
        banner.innerHTML = `<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;"><span>🛡️ <strong>Host Administrator Mode:</strong> Full management access active.</span>${lockBtnHtml}</div>`;
        const lockBtn = document.getElementById('lock-admin-btn');
        if (lockBtn) {
          lockBtn.onclick = () => {
            localStorage.removeItem('media_admin_token');
            fetchStatus();
            fetchSettings();
          };
        }
      } else {
        banner.style.display = 'block';
        banner.style.background = 'rgba(99, 102, 241, 0.1)';
        banner.style.border = '1px solid rgba(99, 102, 241, 0.3)';
        banner.style.color = '#a5b4fc';
        banner.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <span>🔒 <strong>Connected as Peer Client:</strong> Browsing mode.</span>
            ${data.admin_password_set ? '<button id="unlock-admin-btn" class="secondary-btn" style="padding: 3px 10px; font-size: 0.75rem;">🔑 Unlock Admin</button>' : '<span>No admin password set. Open the server on its local network to manage settings.</span>'}
          </div>
        `;
        const unlockBtn = document.getElementById('unlock-admin-btn');
        if (unlockBtn) {
          unlockBtn.onclick = async () => {
            const pin = prompt('Enter Admin Token / PIN:');
            if (pin !== null && pin.trim()) {
              localStorage.setItem('media_admin_token', pin.trim());
              await fetchStatus();
              if (!state.isAdmin) {
                localStorage.removeItem('media_admin_token');
                alert('Incorrect admin password. Please try again.');
              }
              await fetchSettings();
            }
          };
        }
      }
    }

    let passwordPanel = document.getElementById('admin-password-panel');
    if (!passwordPanel && banner) {
      passwordPanel = document.createElement('div');
      passwordPanel.id = 'admin-password-panel';
      passwordPanel.style.cssText = 'margin: 16px 0; padding: 16px; border: 1px solid var(--border-subtle); border-radius: 12px;';
      banner.after(passwordPanel);
    }
    if (passwordPanel) {
      passwordPanel.hidden = !state.isAdmin;
      passwordPanel.innerHTML = `<h3>Admin password (optional)</h3>
        <p>${data.admin_password_set ? 'An admin password is set.' : 'No password is set. Devices on your local network can manage this server.'} Choose your own password to require it for LAN administration.</p>
        <form id="admin-password-form" style="display:flex; gap:8px; flex-wrap:wrap; margin-top:12px;">
          <input id="admin-new-password" type="password" autocomplete="new-password" placeholder="New password" required aria-label="New admin password">
          <input id="admin-confirm-password" type="password" autocomplete="new-password" placeholder="Confirm password" required aria-label="Confirm admin password">
          <button class="primary-btn" type="submit">${data.admin_password_set ? 'Change password' : 'Set password'}</button>
          ${data.admin_password_set ? '<button class="secondary-btn" type="button" id="remove-admin-password">Remove password</button>' : ''}
        </form>`;
      const savePassword = async (password) => {
        try {
          const response = await apiFetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ admin_token: password }) });
          if (!response.ok) throw new Error('Could not update the admin password.');
          if (password) localStorage.setItem('media_admin_token', password);
          else localStorage.removeItem('media_admin_token');
          await fetchStatus();
          await fetchSettings();
        } catch (error) { alert(error.message); }
      };
      document.getElementById('admin-password-form').onsubmit = async (event) => {
        event.preventDefault();
        const password = document.getElementById('admin-new-password').value.trim();
        if (!password || password !== document.getElementById('admin-confirm-password').value.trim()) {
          alert('Enter the same non-empty password in both fields.');
          return;
        }
        await savePassword(password);
      };
      const removePassword = document.getElementById('remove-admin-password');
      if (removePassword) removePassword.onclick = async () => {
        if (confirm('Remove the password and allow local network devices to manage this server?')) await savePassword('');
      };
    }

    masterSharingToggle.checked = data.sharing_enabled !== false;
    masterSharingToggle.disabled = !state.isAdmin;
    deviceNameInput.value = data.device_name || '';
    deviceNameInput.disabled = !state.isAdmin;
    if (saveDeviceNameBtn) saveDeviceNameBtn.disabled = !state.isAdmin;
    if (addFolderBtn) addFolderBtn.style.display = state.isAdmin ? 'inline-flex' : 'none';

    if (approvalQueueToggle) {
      approvalQueueToggle.checked = Boolean(data.upload_approval_required);
      approvalQueueToggle.disabled = !state.isAdmin;
      if (approvalQueueStatusBadge) {
        approvalQueueStatusBadge.textContent = data.upload_approval_required ? 'Review Queue Active' : 'Auto-Accept';
        approvalQueueStatusBadge.style.color = data.upload_approval_required ? '#fbbf24' : '#10b981';
      }
    }

    if (state.isAdmin) {
      fetchPendingUploads();
    }

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

    if (song.isLiveShare) {
      const copyBtnHtml = song.copied_to_server 
        ? `<span class="badge-pill" style="background: rgba(16, 185, 129, 0.2); color:#34d399; font-size:0.7rem;">✓ Server Saved</span>`
        : `<button class="secondary-btn copy-share-to-server-btn" data-share-id="${song.id}" style="padding: 3px 8px; font-size: 0.7rem; border-radius: 6px;">📥 Copy to Server</button>`;

      row.innerHTML = `
        <div class="song-index" style="color:#818cf8;">📡</div>
        <div class="song-cover-thumb" style="background: rgba(99,102,241,0.2); display:flex; align-items:center; justify-content:center; border-radius:8px; width:44px; height:44px; color:#a5b4fc;">
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none">
            <path d="M9 18V5l12-2v13"></path>
            <circle cx="6" cy="18" r="3"></circle>
            <circle cx="18" cy="16" r="3"></circle>
          </svg>
        </div>
        <div class="song-details">
          <span class="song-title">${escapeHtml(song.title)} <span class="badge-pill" style="background:#6366f1; color:#fff; font-size:0.68rem;">Live Peer</span></span>
          <span class="song-subtitle" style="color:#a5b4fc;">🟢 Shared by ${escapeHtml(song.owner_name || 'Peer')} • ${formatBytes(song.filesize)}</span>
        </div>
        <div class="song-meta-right" style="display:flex; align-items:center; gap:6px;">
          <a href="${song.download_url}" class="icon-btn" title="Download directly" download>
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          </a>
          ${copyBtnHtml}
        </div>
      `;
      row.addEventListener('click', (e) => {
        if (e.target.closest('a') || e.target.closest('button')) return;
        playFromList(songs, songs.indexOf(song));
      });
      const copyBtn = row.querySelector('.copy-share-to-server-btn');
      if (copyBtn) {
        copyBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          await copyLiveShareToServer(song.id, copyBtn);
        });
      }
      container.appendChild(row);
      return;
    }
    const ownerBadge = (song.owner_name && song.owner_name !== 'Host') 
      ? `<span class="owner-badge">Shared by ${escapeHtml(song.owner_name)}</span>` 
      : '';

    const genreBadge = (song.genre && song.genre !== 'Unknown')
      ? `<span class="genre-tag">${escapeHtml(song.genre)}</span>`
      : '';

    const langBadge = (song.language && song.language !== 'Unknown')
      ? `<span class="lang-tag">${escapeHtml(song.language)}</span>`
      : '';

    const isPlaylistView = isDetail && state.currentPlaylist;
    const isChecked = state.selectedSongIds.has(song.id);

    row.className = `song-row ${isCurrent ? 'playing' : ''} ${state.isBatchMode ? 'batch-mode' : ''}`;

    row.innerHTML = `
      <div class="song-checkbox" style="${state.isBatchMode ? 'display:flex;' : 'display:none;'}">
        <input type="checkbox" class="batch-song-check" data-song-id="${song.id}" ${isChecked ? 'checked' : ''}>
      </div>
      <img class="song-cover-thumb" src="${getCoverUrl(song)}" alt="" loading="lazy">
      <div class="song-details">
        <span class="song-title">${escapeHtml(song.title || 'Unknown Title')}</span>
        <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:2px;">
          <span class="song-subtitle">${escapeHtml(song.artist || 'Unknown Artist')} • ${escapeHtml(song.album || 'Unknown Album')}${song.year ? ' • ' + song.year : ''}${ownerBadge}</span>
          ${genreBadge}
          ${langBadge}
        </div>
      </div>
      <div class="song-meta-right">
        <span class="song-duration">${formatTime(song.duration)}</span>
        <button class="icon-btn edit-meta-btn" data-song-id="${song.id}" title="Edit Details">
          <svg viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2" fill="none">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
        </button>
        <button class="icon-btn love-btn ${isFav ? 'loved active' : ''}" data-song-id="${song.id}" title="${isFav ? 'Remove from Favorites' : 'Add to Favorites'}">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
        </button>
        <a href="vlc://${window.location.origin}/api/stream/${song.id}" class="vlc-play-btn" title="Open in VLC Media Player" target="_blank">📺 VLC</a>
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
        ${isPlaylistView ? `
          <button class="icon-btn remove-from-pl-btn" data-song-id="${song.id}" title="Remove from this playlist" style="color:var(--text-muted); padding:6px;">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        ` : ''}
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
      if (e.target.closest('.edit-meta-btn') || e.target.closest('.add-to-pl-btn') || e.target.closest('.download-direct-btn') || e.target.closest('.love-btn') || e.target.closest('.delete-media-btn') || e.target.closest('.remove-from-pl-btn') || e.target.closest('.batch-song-check')) return;
      if (state.isBatchMode) {
        const chk = row.querySelector('.batch-song-check');
        if (chk) {
          chk.checked = !chk.checked;
          if (chk.checked) state.selectedSongIds.add(song.id);
          else state.selectedSongIds.delete(song.id);
          updateBatchUI();
        }
        return;
      }
      playFromList(songs, idx);
    });

    const checkInput = row.querySelector('.batch-song-check');
    if (checkInput) {
      checkInput.addEventListener('change', (e) => {
        e.stopPropagation();
        if (checkInput.checked) state.selectedSongIds.add(song.id);
        else state.selectedSongIds.delete(song.id);
        updateBatchUI();
      });
    }

    const removePlBtn = row.querySelector('.remove-from-pl-btn');
    if (removePlBtn) {
      removePlBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        removeSongFromCurrentPlaylist(song.id);
      });
    }

    const editBtn = row.querySelector('.edit-meta-btn');
    if (editBtn) {
      editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openEditMetadataModal(song);
      });
    }

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

    if (video.isLiveShare) {
      const copyBtnHtml = video.copied_to_server 
        ? `<span class="badge-pill" style="background: rgba(16, 185, 129, 0.2); color:#34d399;">✓ Saved to Server</span>`
        : `<button class="primary-btn copy-share-to-server-btn" data-share-id="${video.id}" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px;">📥 Copy to Server</button>`;

      card.innerHTML = `
        <div class="video-thumb-wrapper" style="border: 1px solid rgba(99, 102, 241, 0.4); box-shadow: 0 0 12px rgba(99, 102, 241, 0.15);">
          <div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.2));">
            <svg viewBox="0 0 24 24" width="42" height="42" stroke="currentColor" stroke-width="2" fill="none" style="color: #818cf8;">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
          </div>
          <span class="badge-pill" style="background: #6366f1; color: #fff; font-weight: 600;">📡 Live Share</span>
          <div class="video-play-overlay">
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
          </div>
        </div>
        <div class="video-details">
          <div class="video-info-text">
            <h4 class="video-title">${escapeHtml(video.title)}</h4>
            <span class="video-meta" style="color:#a5b4fc;">🟢 Live from ${escapeHtml(video.owner_name || 'Connected Peer')} • ${formatBytes(video.filesize)}</span>
          </div>
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:6px;">
            <a href="${video.download_url}" class="secondary-btn" style="padding: 4px 8px; font-size: 0.72rem; text-decoration: none;" download>⬇️ Download</a>
            ${copyBtnHtml}
          </div>
        </div>
      `;
      card.addEventListener('click', (e) => {
        if (e.target.closest('a') || e.target.closest('button')) return;
        openVideoPlayer(video);
      });
      const copyBtn = card.querySelector('.copy-share-to-server-btn');
      if (copyBtn) {
        copyBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          await copyLiveShareToServer(video.id, copyBtn);
        });
      }
      targetEl.appendChild(card);
      return;
    }
    const coverUrl = getCoverUrl(video);
    const isFav = !!video.is_favorite;
    const isOwner = !!video.is_owner;
    const ownerBadge = (video.owner_name && video.owner_name !== 'Host') 
      ? ` • <span style="color: #a5b4fc;">Shared by ${escapeHtml(video.owner_name)}</span>` 
      : '';

    // Jellyfin Badges
    const resBadge = video.resolution ? `<span class="badge-pill badge-res ${video.resolution.includes('4K') ? 'res-4k' : ''}">${escapeHtml(video.resolution)}</span>` : '';
    const yearBadge = video.year ? `<span class="badge-pill badge-year">${video.year}</span>` : '';
    const tvBadge = (video.season != null && !video.resolution) ? `<span class="badge-pill badge-tv">S${String(video.season).padStart(2, '0')}</span>` : '';

    let subtitleText = '';
    if (video.season != null) {
      subtitleText = `${escapeHtml(video.artist && video.artist !== 'Video / Movie' ? video.artist : 'TV Series')} • S${video.season}${video.episode ? 'E' + video.episode : ''} • `;
    } else if (video.year) {
      subtitleText = `${video.year} • `;
    }
    if (video.resolution) {
      subtitleText += `${escapeHtml(video.resolution)} • `;
    }
    subtitleText += formatBytes(video.filesize);

    card.innerHTML = `
      <div class="video-thumb-wrapper">
        <img src="${coverUrl}" alt="" loading="lazy">
        ${resBadge || tvBadge}
        ${yearBadge}
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
          <span class="video-meta">${subtitleText}${ownerBadge}</span>
        </div>
        <div style="display:flex; align-items:center; gap:4px;">
          <button class="icon-btn edit-meta-btn" data-video-id="${video.id}" title="Edit Media Details">
            <svg viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2" fill="none">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
          <button class="icon-btn love-btn ${isFav ? 'loved active' : ''}" data-video-id="${video.id}" title="${isFav ? 'Remove from Favorites' : 'Add to Favorites'}">
            <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
            </svg>
          </button>
          <a href="vlc://${window.location.origin}/api/stream/${video.id}" class="vlc-play-btn" title="Open in VLC Media Player" target="_blank">📺 VLC</a>
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

    const editBtn = card.querySelector('.edit-meta-btn');
    if (editBtn) {
      editBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openEditMetadataModal(video);
      });
    }

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

let playbackNoticeVersion = 0;
function clearPlaybackNotice() {
  playbackNoticeVersion++;
  document.getElementById('playback-notice')?.remove();
}

async function showPlaybackError(engine) {
  if (!engine.error || engine.error.code === 1 || !engine.getAttribute('src')) return;
  const source = engine.src;
  clearPlaybackNotice();
  const version = playbackNoticeVersion;
  const panel = document.createElement('div');
  panel.id = 'playback-notice';
  panel.setAttribute('role', 'alert');
  panel.style.cssText = 'position:fixed;bottom:100px;left:5%;width:90%;max-width:620px;z-index:10000;background:var(--bg-surface,#161925);border:1px solid #f59e0b;border-radius:12px;padding:16px;box-shadow:0 8px 30px #0008;';
  const message = document.createElement('p');
  message.textContent = 'Playback failed. Checking whether the server can read this file…';
  panel.appendChild(message);
  const close = document.createElement('button');
  close.className = 'secondary-btn';
  close.textContent = 'Dismiss';
  close.onclick = clearPlaybackNotice;
  panel.appendChild(close);
  document.body.appendChild(panel);
  const url = new URL(source, window.location.href);
  const serverMedia = url.origin === window.location.origin && /^\/api\/stream\/[^/]+$/.test(url.pathname);
  if (!serverMedia) {
    message.textContent = 'This file could not play. Its format may be unsupported, or the device sharing it may be offline. Try VLC or download the file.';
    return;
  }
  try {
    const response = await apiFetch(url.href, { headers: { Range: 'bytes=0-0' }, signal: AbortSignal.timeout(15000) });
    if (version !== playbackNoticeVersion || engine.src !== source) { await response.body?.cancel(); return; }
    if (!response.ok) {
      let detail = '';
      try { detail = (await response.json()).detail || ''; } catch (_) {}
      message.textContent = detail || `The server could not stream this file (HTTP ${response.status}). Check its drive and folder permissions, then rescan.`;
      return;
    }
    await response.body?.cancel();
    if (url.searchParams.has('compatible')) {
      message.textContent = 'The compatible copy could not play. Try VLC; this file may be damaged or unsupported on this device.';
      return;
    }
    message.textContent = 'The file is reachable, but playback failed. Try a browser-compatible copy. Preparing it can take a few minutes and uses server storage.';
    const compatible = document.createElement('button');
    compatible.className = 'primary-btn';
    compatible.textContent = 'Play compatible version';
    compatible.style.margin = '8px';
    compatible.onclick = async () => {
      compatible.disabled = true;
      message.textContent = 'Preparing a compatible copy on the server…';
      url.searchParams.set('compatible', 'true');
      try {
        const jobUrl = `/api/playback/${encodeURIComponent(url.pathname.split('/').pop())}/compatible`;
        let jobResponse = await apiFetch(jobUrl, { method: 'POST', signal: AbortSignal.timeout(15000) });
        let job = await jobResponse.json();
        if (!jobResponse.ok) throw new Error(job.detail || 'Could not prepare compatible playback.');
        const deadline = Date.now() + 330000;
        while (job.status === 'preparing' && Date.now() < deadline) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          if (version !== playbackNoticeVersion || engine.src !== source) return;
          jobResponse = await apiFetch(jobUrl, { signal: AbortSignal.timeout(15000) });
          job = await jobResponse.json();
          if (!jobResponse.ok) throw new Error(job.detail || 'Could not check preparation.');
        }
        if (job.status !== 'ready') throw new Error(job.detail || 'Preparing this file took too long. Try VLC.');
        const response = await apiFetch(url.href, { headers: { Range: 'bytes=0-0' }, signal: AbortSignal.timeout(15000) });
        if (version !== playbackNoticeVersion || engine.src !== source) { await response.body?.cancel(); return; }
        if (!response.ok) {
          let detail = '';
          try { detail = (await response.json()).detail || ''; } catch (_) {}
          throw new Error(detail || `Compatible playback failed (HTTP ${response.status}). Try VLC.`);
        }
        await response.body?.cancel();
        engine.src = url.href;
        clearPlaybackNotice();
        engine.play().catch(error => { if (error.name === 'NotAllowedError') alert('The compatible version is ready. Press Play to start.'); });
      } catch (error) {
        if (version !== playbackNoticeVersion) return;
        message.textContent = error.message;
        compatible.disabled = false;
      }
    };
    panel.appendChild(compatible);
    const vlc = document.createElement('a');
    vlc.className = 'secondary-btn';
    vlc.textContent = 'Open original in VLC';
    vlc.href = `vlc://${source}`;
    panel.appendChild(vlc);
  } catch (_) {
    if (version === playbackNoticeVersion) message.textContent = 'The media server could not be reached. Check the connection and try again.';
  }
}
audio.addEventListener('error', () => {
  state.isPlaying = false;
  updatePlayIcons(false);
  showPlaybackError(audio);
});
videoEngine.addEventListener('error', () => showPlaybackError(videoEngine));
audio.addEventListener('playing', () => { state.isPlaying = true; updatePlayIcons(true); clearPlaybackNotice(); });
videoEngine.addEventListener('playing', clearPlaybackNotice);

function openVideoPlayer(video) {
  clearPlaybackNotice();
  pauseAudio();
  videoModalTitle.textContent = video.title || 'Playing Video';
  videoEngine.src = video.isLocal ? video.url : (video.stream_url || `/api/stream/${video.id}`);
  videoModal.classList.remove('hidden');
  videoEngine.play().catch(e => console.warn('Video autoplay prevented:', e));
}

videoModalClose.addEventListener('click', () => {
  clearPlaybackNotice();
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
    sharedFoldersListEl.innerHTML = '<p class="placeholder-text">No folders shared yet.</p>';
    return;
  }

  folders.forEach(folder => {
    const item = document.createElement('div');
    item.className = 'folder-item';

    if (state.isAdmin) {
      item.innerHTML = `
        <div>
          <strong>${escapeHtml(folder.name || 'Folder')}</strong>
          <div class="folder-path">${escapeHtml(folder.path)} (${folder.type})</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <label class="switch" style="transform: scale(0.8);" title="Toggle folder sharing">
            <input type="checkbox" class="folder-toggle" ${folder.enabled ? 'checked' : ''}>
            <span class="slider round"></span>
          </label>
          <button class="icon-btn delete-folder-btn" title="Remove Folder from Sharing">
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
    } else {
      item.innerHTML = `
        <div>
          <strong>${escapeHtml(folder.name || 'Folder')}</strong>
          <div class="folder-path">${escapeHtml(folder.path)} (${folder.type})</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size: 0.75rem; color: #10b981; background: rgba(16, 185, 129, 0.12); padding: 4px 10px; border-radius: 6px;">
            ${folder.enabled ? 'Active on Host' : 'Disabled'}
          </span>
        </div>
      `;
    }

    sharedFoldersListEl.appendChild(item);
  });
}

// --- Downloader Operations ---
if (dlUrlInput) {
  dlUrlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      startDownloadBtn.click();
    }
  });
}

startDownloadBtn.addEventListener('click', async () => {
  const url = dlUrlInput.value.trim();
  if (!url) {
    alert('Please paste a YouTube, Instagram, Spotify, or media link, or enter a song name to search');
    return;
  }

  const format = document.querySelector('input[name="dl-format"]:checked').value;
  const quality = dlQualitySelect.value;
  const destination = document.querySelector('input[name="dl-destination"]:checked')?.value || 'server';
  const cookies_browser = dlCookiesSelect ? (dlCookiesSelect.value || null) : null;

  try {
    startDownloadBtn.disabled = true;
    startDownloadBtn.textContent = 'Starting...';

    const res = await apiFetch('/api/download', {
      method: 'POST',
      signal: AbortSignal.timeout(15000),
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        format,
        quality,
        destination,
        cookies_browser,
        target_playlist_id: dlPlaylistSelect ? (dlPlaylistSelect.value || null) : null,
        client_id: clientId,
        device_name: getDeviceType()
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'The server could not start this download.');
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

if (clearDownloadsBtn) {
  clearDownloadsBtn.addEventListener('click', async () => {
    try {
      await apiFetch('/api/downloads/clear', { method: 'POST' });
      pollDownloads();
    } catch (e) {
      console.error('Error clearing download history:', e);
    }
  });
}

let dlPollInterval = null;
let lastKnownCompleted = new Set();

async function pollDownloads() {
  try {
    const res = await apiFetch('/api/downloads/status', { signal: AbortSignal.timeout(10000) });
    if (!res.ok) throw new Error('Could not read download status.');
    const data = await res.json();
    state.downloads = data.tasks;
    renderDownloads(data.tasks);

    let hasNewCompletion = false;
    data.tasks.forEach(t => {
      if (t.status === 'completed' && !lastKnownCompleted.has(t.id)) {
        lastKnownCompleted.add(t.id);
        hasNewCompletion = true;
        // Auto-download to client device if destination was client
        if (t.destination === 'client' && t.owner_id === clientId && t.download_url) {
          const dlA = document.createElement('a');
          dlA.href = t.download_url;
          dlA.download = '';
          document.body.appendChild(dlA);
          dlA.click();
          document.body.removeChild(dlA);
        }
      }
    });

    if (hasNewCompletion) {
      fetchStatus();
      fetchSongs();
      fetchVideos();
      fetchPhotos();
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
      fetchPhotos();
      fetchFavorites();
    }
  } catch (e) {}
}

async function playSongById(songId) {
  try {
    const res = await apiFetch(`/api/song/${songId}`);
    if (res.ok) {
      const song = await res.json();
      if (song.media_type === 'video') {
        openVideoPlayer(song);
        return;
      }
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
    const isClient = task.destination === 'client';
    const isFailed = task.status === 'failed';
    const isDownloading = task.status === 'downloading';

    let speedText = '';
    if (isDownloading && task.speed) {
      speedText = ` • ${formatBytes(task.speed)}/s`;
      if (task.eta) speedText += ` (ETA ${task.eta}s)`;
    }

    item.innerHTML = `
      <div class="download-task-header">
        <div style="display:flex; flex-direction:column; gap:3px; max-width:68%; overflow:hidden;">
          <span class="task-title" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(task.title || task.url)}">
            ${escapeHtml(task.title || task.url)}
          </span>
          ${isFailed && task.error ? `
            <span class="task-error-hint" style="font-size:0.75rem; color:#f87171; line-height:1.2; word-break:break-word;">
              ⚠️ ${escapeHtml(task.error)}
            </span>
          ` : `
            <span style="font-size:0.75rem; color:var(--text-muted);">
              ${task.format === 'audio' ? '🎵 Audio' : '🎬 Video'} • ${task.destination === 'client' ? (isDone ? 'Ready to save to your device' : 'Preparing for your device') : (isDone ? 'Saved to Server' : 'Saving to Server')}${speedText}
            </span>
          `}
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          ${isFailed ? `
            <button class="secondary-btn retry-dl-btn" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px;">
              🔄 Retry
            </button>
          ` : ''}
          ${isDone && isClient && task.download_url ? `
            <a href="${task.download_url}" class="primary-btn" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px; text-decoration: none;" download>
              💾 Save File
            </a>
            <a href="vlc://${window.location.origin}${task.download_url}" class="vlc-play-btn" style="padding: 4px 10px; font-size: 0.75rem;" target="_blank">📺 VLC</a>
          ` : ''}
          ${isDone && !isClient && task.song_id ? `
            <button class="primary-btn play-dl-btn" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px;">
              ▶️ Play
            </button>
            <a href="vlc://${window.location.origin}/api/stream/${task.song_id}" class="vlc-play-btn" style="padding: 4px 10px; font-size: 0.75rem;" target="_blank">📺 VLC</a>
          ` : ''}
          <span class="task-status-badge ${task.status}">${task.status}</span>
        </div>
      </div>
      <div class="download-progress-track">
        <div class="download-progress-bar" style="width: ${isFailed ? 100 : (task.progress || (isDone ? 100 : 0))}%; background: ${isFailed ? '#ef4444' : ''}"></div>
      </div>
    `;

    if (isDone && !isClient && task.song_id) {
      const playBtn = item.querySelector('.play-dl-btn');
      if (playBtn) {
        playBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          playSongById(task.song_id);
        });
      }
    }

    if (isFailed) {
      const retryBtn = item.querySelector('.retry-dl-btn');
      if (retryBtn) {
        retryBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          retryBtn.disabled = true;
          retryBtn.textContent = 'Retrying...';
          try {
            const retryResponse = await apiFetch('/api/download', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                url: task.url,
                format: task.format,
                quality: task.quality || 'best',
                destination: task.destination || 'server',
                client_id: clientId,
                device_name: getDeviceType()
              })
            });
            if (!retryResponse.ok) {
              const error = await retryResponse.json();
              throw new Error(error.detail || 'Could not restart download.');
            }
            pollDownloads();
          } catch (err) {
            alert(`Retry failed: ${err}`);
            retryBtn.disabled = false;
            retryBtn.textContent = '🔄 Retry';
          }
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

if (approvalQueueToggle) {
  approvalQueueToggle.addEventListener('change', async (e) => {
    try {
      await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_approval_required: e.target.checked })
      });
      fetchSettings();
    } catch (err) {
      alert(`Error updating approval policy: ${err}`);
    }
  });
}

if (refreshPendingBtn) {
  refreshPendingBtn.addEventListener('click', () => fetchPendingUploads());
}

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

// Add Folder Modal Elements & Handlers
const addFolderModal = document.getElementById('add-folder-modal');
const addFolderModalClose = document.getElementById('add-folder-modal-close');
const addFolderCancelBtn = document.getElementById('add-folder-cancel-btn');
const addFolderSubmitBtn = document.getElementById('add-folder-submit-btn');
const newFolderPathInput = document.getElementById('new-folder-path-input');
const newFolderNameInput = document.getElementById('new-folder-name-input');
const newFolderTypeSelect = document.getElementById('new-folder-type-select');
const serverFolderBrowser = document.getElementById('server-folder-browser');
const serverFolderEntries = document.getElementById('server-folder-entries');
const serverFolderFilter = document.getElementById('server-folder-filter');
const serverFolderLocation = document.getElementById('server-folder-location');
const serverFolderUp = document.getElementById('server-folder-up');
const serverFolderUse = document.getElementById('server-folder-use');
let serverFolderData = null;
let serverFolderRequest = 0;

function renderServerFolderEntries() {
  serverFolderEntries.replaceChildren();
  const query = serverFolderFilter.value.toLowerCase();
  const folders = (serverFolderData?.folders || []).filter(folder => folder.name.toLowerCase().includes(query));
  folders.forEach(folder => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'secondary-btn';
    button.style.textAlign = 'left';
    button.textContent = `📁 ${folder.name}`;
    button.title = folder.path;
    button.onclick = () => browseServerFolders(folder.path);
    serverFolderEntries.appendChild(button);
  });
  if (!folders.length) serverFolderEntries.textContent = query ? 'No matching folders.' : 'No subfolders. You can use the current folder.';
}

async function browseServerFolders(path = null) {
  const requestId = ++serverFolderRequest;
  serverFolderBrowser.hidden = false;
  serverFolderData = null;
  serverFolderEntries.textContent = '';
  serverFolderLocation.textContent = 'Loading server folders…';
  serverFolderUse.disabled = true;
  serverFolderUp.disabled = true;
  try {
    const response = await apiFetch('/api/settings/browse' + (path ? `?path=${encodeURIComponent(path)}` : ''));
    const data = await response.json();
    if (requestId !== serverFolderRequest) return;
    if (!response.ok) throw new Error(data.detail || 'Could not browse server folders.');
    serverFolderData = data;
    serverFolderLocation.textContent = data.path || 'Available media locations on this server';
    serverFolderUse.disabled = !data.path;
    serverFolderUp.disabled = !data.parent;
    serverFolderFilter.value = '';
    renderServerFolderEntries();
    if (!data.path && !data.folders.length) serverFolderEntries.textContent = 'No media locations found. Enter a mounted server folder path below.';
  } catch (error) {
    if (requestId === serverFolderRequest) serverFolderLocation.textContent = error.message;
  }
}

document.getElementById('browse-server-folders')?.addEventListener('click', () => browseServerFolders());
document.getElementById('server-folder-roots')?.addEventListener('click', () => browseServerFolders());
serverFolderUp?.addEventListener('click', () => { if (serverFolderData?.parent) browseServerFolders(serverFolderData.parent); });
serverFolderFilter?.addEventListener('input', renderServerFolderEntries);
serverFolderUse?.addEventListener('click', () => {
  if (!serverFolderData?.path) return;
  newFolderPathInput.value = serverFolderData.path;
  const name = serverFolderData.path.split(/[\\/]/).filter(Boolean).pop();
  newFolderNameInput.value = name || 'Media';
  newFolderTypeSelect.value = /^(music|audio|songs)$/i.test(name) ? 'music' : /^(videos?|movies|tv shows)$/i.test(name) ? 'video' : 'both';
  serverFolderBrowser.hidden = true;
  newFolderTypeSelect.focus();
});

if (addFolderBtn) {
  addFolderBtn.addEventListener('click', () => {
    if (newFolderPathInput) newFolderPathInput.value = '';
    if (newFolderNameInput) newFolderNameInput.value = '';
    if (newFolderTypeSelect) newFolderTypeSelect.value = 'both';
    if (addFolderModal) addFolderModal.classList.remove('hidden');
    if (serverFolderBrowser) browseServerFolders();
  });
}

if (addFolderModalClose) addFolderModalClose.addEventListener('click', () => addFolderModal.classList.add('hidden'));
if (addFolderCancelBtn) addFolderCancelBtn.addEventListener('click', () => addFolderModal.classList.add('hidden'));

// Preset chips (e.g. /DATA/Media, /DATA/Media/Movies, etc.)
document.querySelectorAll('.preset-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const path = chip.dataset.path;
    const name = chip.dataset.name;
    const type = chip.dataset.type;
    if (newFolderPathInput) newFolderPathInput.value = path;
    if (newFolderNameInput) newFolderNameInput.value = name;
    if (newFolderTypeSelect) newFolderTypeSelect.value = type;
  });
});

if (addFolderSubmitBtn) {
  addFolderSubmitBtn.addEventListener('click', async () => {
    const folderPath = newFolderPathInput.value.trim();
    const folderName = newFolderNameInput.value.trim() || 'Shared Folder';
    const folderType = newFolderTypeSelect.value || 'both';

    if (!folderPath) {
      alert('Please enter a server folder path.');
      return;
    }

    addFolderSubmitBtn.disabled = true;
    addFolderSubmitBtn.innerHTML = '<span>Adding & Scanning...</span>';

    try {
      const res = await apiFetch('/api/settings/folders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: folderPath, name: folderName, type: folderType })
      });
      if (res.ok) {
        if (addFolderModal) addFolderModal.classList.add('hidden');
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
    } finally {
      addFolderSubmitBtn.disabled = false;
      addFolderSubmitBtn.innerHTML = '<span>Add & Index Folder</span>';
    }
  });
}

// User / Device Display Name Customization
const editUserNameTrigger = document.getElementById('edit-user-name-trigger');
if (editUserNameTrigger) {
  editUserNameTrigger.addEventListener('click', () => {
    const current = localStorage.getItem('mediahub_user_name') || '';
    const newName = prompt('Enter your display name (files you share will display this name):', current || getDeviceType());
    if (newName !== null) {
      if (newName.trim()) {
        localStorage.setItem('mediahub_user_name', newName.trim());
      } else {
        localStorage.removeItem('mediahub_user_name');
      }
      if (myDeviceTypeLabel) myDeviceTypeLabel.textContent = getDeviceType();
      sendClientHeartbeat();
    }
  });
}

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

function renderPlaylists(playlists = null) {
  if (!playlistsGridEl) return;
  playlistsGridEl.innerHTML = '';

  let list = playlists;
  if (!list) {
    if (state.activePlaylistTab === 'smart') {
      list = state.smartPlaylists || [];
    } else if (state.activePlaylistTab === 'custom') {
      list = state.playlists || [];
    } else {
      list = [...(state.smartPlaylists || []), ...(state.playlists || [])];
    }
  }

  if (!list || list.length === 0) {
    let emptyMsg = 'No playlists created yet.';
    let emptySub = 'Click "+ Custom Playlist" or generate a Smart Auto-Mix to get started.';
    if (state.activePlaylistTab === 'smart') {
      emptyMsg = 'No smart auto-mixes found.';
      emptySub = 'Tag your songs with Eras, Languages, or Genres to automatically unlock dynamic mixes!';
    } else if (state.activePlaylistTab === 'custom') {
      emptyMsg = 'No custom playlists created yet.';
      emptySub = 'Click "+ Custom Playlist" or "Import M3U" to curate your own playlists.';
    }
    playlistsGridEl.innerHTML = `
      <div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--text-muted);">
        <p>${emptyMsg}</p>
        <p style="font-size: 0.85rem; margin-top: 8px;">${emptySub}</p>
      </div>
    `;
    return;
  }

  list.forEach(pl => {
    const isSmart = !!(pl.is_smart || (pl.id && pl.id.toString().startsWith('smart:')));
    const card = document.createElement('div');
    card.className = `media-card ${isSmart ? 'smart-mix-card' : ''}`;

    let coverHtml = '';
    if (pl.sample_covers && pl.sample_covers.length >= 4) {
      coverHtml = `
        <div class="media-card-img playlist-mosaic">
          ${pl.sample_covers.slice(0, 4).map(c => `<img src="/api/cover/${c}" alt="" loading="lazy">`).join('')}
        </div>
      `;
    } else if (pl.sample_covers && pl.sample_covers.length > 0) {
      coverHtml = `
        <div class="media-card-img">
          <img src="/api/cover/${pl.sample_covers[0]}" alt="" style="width:100%; height:100%; object-fit:cover;" loading="lazy">
        </div>
      `;
    } else if (isSmart) {
      coverHtml = `
        <div class="media-card-img" style="display:flex; align-items:center; justify-content:center; background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(168,85,247,0.25)); border:1px solid rgba(99,102,241,0.3);">
          <span style="font-size: 2.4rem;">⚡</span>
        </div>
      `;
    } else {
      coverHtml = `
        <div class="media-card-img" style="display:flex; align-items:center; justify-content:center; background: var(--bg-surface);">
          <svg viewBox="0 0 24 24" width="44" height="44" stroke="var(--accent)" stroke-width="1.5" fill="none">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <circle cx="4" cy="6" r="1.5" fill="currentColor"></circle>
            <circle cx="4" cy="12" r="1.5" fill="currentColor"></circle>
            <circle cx="4" cy="18" r="1.5" fill="currentColor"></circle>
          </svg>
        </div>
      `;
    }

    const durationText = pl.total_duration ? ` • ${formatTime(pl.total_duration)}` : '';
    const badgeHtml = isSmart ? `<span class="smart-mix-badge">⚡ AUTO MIX</span>` : '';
    card.innerHTML = `
      ${coverHtml}
      ${badgeHtml}
      <span class="media-card-title">${escapeHtml(pl.name)}</span>
      <span class="media-card-subtitle">${pl.song_count || 0} tracks${durationText}</span>
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

function playShuffledList(songs) {
  if (!songs || songs.length === 0) return;
  const shuffled = [...songs].sort(() => Math.random() - 0.5);
  state.isShuffle = true;
  if (shuffleBtn) shuffleBtn.classList.add('active');
  playFromList(shuffled, 0);
}

// Detail Drilldown Functions
async function openArtistDetail(artistName) {
  try {
    state.currentPlaylist = null;
    if (detailAddSongsBtn) detailAddSongsBtn.classList.add('hidden');
    if (detailDeleteBtn) detailDeleteBtn.classList.add('hidden');

    const res = await apiFetch(`/api/songs?artist=${encodeURIComponent(artistName)}`);
    const data = await res.json();
    const songs = data.songs || [];
    detailType.textContent = 'ARTIST';
    detailTitle.textContent = artistName;
    detailSubtitle.textContent = `${songs.length} songs`;
    detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';

    detailPlayBtn.onclick = () => playFromList(songs, 0);
    detailShuffleBtn.onclick = () => playShuffledList(songs);
    detailDownloadBtn.onclick = () => downloadSongsBatchZip(songs.map(s => s.id), `${artistName}_songs.zip`);
    detailShareBtn.onclick = () => {
      const shareUrl = `${window.location.origin}/#artist-${encodeURIComponent(artistName)}`;
      navigator.clipboard.writeText(shareUrl);
      alert(`Copied link for artist "${artistName}"!`);
    };

    renderSongList(songs, detailSongList, true);
    switchView('detail');
  } catch (err) {
    console.error('Error opening artist detail:', err);
  }
}

async function openAlbumDetail(album) {
  try {
    state.currentPlaylist = null;
    if (detailAddSongsBtn) detailAddSongsBtn.classList.add('hidden');
    if (detailDeleteBtn) detailDeleteBtn.classList.add('hidden');

    const res = await apiFetch(`/api/songs?album=${encodeURIComponent(album.album)}&sort_by=track_number`);
    const data = await res.json();
    const songs = data.songs || [];
    detailType.textContent = 'ALBUM';
    detailTitle.textContent = album.album;
    detailSubtitle.textContent = `${album.artist} ${album.year ? '• ' + album.year : ''} • ${songs.length} songs`;
    detailCoverImg.src = album.cover_hash ? `/api/cover/${album.album}` : (songs[0] ? getCoverUrl(songs[0]) : '/icon.svg');

    detailPlayBtn.onclick = () => playFromList(songs, 0);
    detailShuffleBtn.onclick = () => playShuffledList(songs);
    detailDownloadBtn.onclick = () => downloadSongsBatchZip(songs.map(s => s.id), `${album.album}_album.zip`);
    detailShareBtn.onclick = () => {
      const shareUrl = `${window.location.origin}/#album-${encodeURIComponent(album.album)}`;
      navigator.clipboard.writeText(shareUrl);
      alert(`Copied link for album "${album.album}"!`);
    };

    renderSongList(songs, detailSongList, true);
    switchView('detail');
  } catch (err) {
    console.error('Error opening album detail:', err);
  }
}

async function openPlaylistDetail(playlist) {
  try {
    state.currentPlaylist = playlist;
    const res = await apiFetch(`/api/playlists/${playlist.id}/songs`);
    const data = await res.json();
    const songs = data.songs || [];
    const isSmart = !!(playlist.is_smart || (playlist.id && playlist.id.toString().startsWith('smart:')));

    detailType.textContent = isSmart ? '⚡ SMART AUTO MIX' : 'PLAYLIST';
    detailTitle.textContent = playlist.name;
    const durText = playlist.total_duration ? ` • ${formatTime(playlist.total_duration)}` : '';
    detailSubtitle.textContent = `${playlist.description ? playlist.description + ' • ' : ''}${songs.length} tracks${durText}`;
    
    if (playlist.sample_covers && playlist.sample_covers.length > 0) {
      detailCoverImg.src = `/api/cover/${playlist.sample_covers[0]}`;
    } else {
      detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';
    }

    if (isSmart) {
      if (detailSaveCustomBtn) {
        detailSaveCustomBtn.classList.remove('hidden');
        detailSaveCustomBtn.onclick = async () => {
          try {
            const saveName = prompt('Save this auto-mix as a permanent custom playlist:', playlist.name);
            if (!saveName) return;
            const sRes = await apiFetch('/api/playlists', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                name: saveName,
                description: playlist.description || `Generated from ${playlist.name}`,
                song_ids: songs.map(s => s.id)
              })
            });
            if (sRes.ok) {
              const resData = await sRes.json();
              alert(`Saved "${saveName}" as a custom playlist!`);
              await fetchPlaylists();
              if (resData.playlist) openPlaylistDetail(resData.playlist);
            } else {
              const err = await sRes.json();
              alert(err.detail || 'Failed to save playlist');
            }
          } catch (e) {
            alert('Error saving custom playlist: ' + e);
          }
        };
      }
      if (detailAddSongsBtn) detailAddSongsBtn.classList.add('hidden');
      if (detailDeleteBtn) detailDeleteBtn.classList.add('hidden');
    } else {
      if (detailSaveCustomBtn) detailSaveCustomBtn.classList.add('hidden');
      if (detailAddSongsBtn) {
        detailAddSongsBtn.classList.remove('hidden');
        detailAddSongsBtn.onclick = () => openAddSongsToPlaylistModal(playlist);
      }
      if (detailDeleteBtn) {
        detailDeleteBtn.classList.remove('hidden');
        detailDeleteBtn.onclick = async () => {
          if (confirm(`Delete playlist "${playlist.name}"? (Tracks in your library will be preserved)`)) {
            try {
              const dres = await apiFetch(`/api/playlists/${playlist.id}`, { method: 'DELETE' });
              if (dres.ok) {
                state.currentPlaylist = null;
                await fetchPlaylists();
                switchView('playlists');
              }
            } catch (e) {
              alert('Failed to delete playlist: ' + e);
            }
          }
        };
      }
    }

    detailPlayBtn.onclick = () => playFromList(songs, 0);
    detailShuffleBtn.onclick = () => playShuffledList(songs);
    detailDownloadBtn.onclick = () => {
      const a = document.createElement('a');
      a.href = `/api/playlists/${playlist.id}/download`;
      a.download = `${playlist.name}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    };
    detailShareBtn.onclick = () => openSharePlaylistModal(playlist);

    renderSongList(songs, detailSongList, true);
    switchView('detail');
  } catch (err) {
    console.error('Error opening playlist detail:', err);
  }
}

async function openGenreDetail(genreName) {
  try {
    state.currentPlaylist = null;
    if (detailAddSongsBtn) detailAddSongsBtn.classList.add('hidden');
    if (detailDeleteBtn) detailDeleteBtn.classList.add('hidden');

    const res = await apiFetch(`/api/songs?genre=${encodeURIComponent(genreName)}`);
    const data = await res.json();
    const songs = data.songs || [];

    detailType.textContent = 'GENRE';
    detailTitle.textContent = genreName;
    detailSubtitle.textContent = `${songs.length} tracks`;
    detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';

    detailPlayBtn.onclick = () => playFromList(songs, 0);
    detailShuffleBtn.onclick = () => playShuffledList(songs);
    detailDownloadBtn.onclick = () => downloadSongsBatchZip(songs.map(s => s.id), `${genreName}_genre.zip`);
    detailShareBtn.onclick = () => {
      const shareUrl = `${window.location.origin}/#genre-${encodeURIComponent(genreName)}`;
      navigator.clipboard.writeText(shareUrl);
      alert(`Copied link for genre "${genreName}"!`);
    };

    renderSongList(songs, detailSongList, true);
    switchView('detail');
  } catch (e) {
    console.error('Error opening genre detail:', e);
  }
}

async function openLanguageDetail(languageName) {
  try {
    state.currentPlaylist = null;
    if (detailAddSongsBtn) detailAddSongsBtn.classList.add('hidden');
    if (detailDeleteBtn) detailDeleteBtn.classList.add('hidden');

    const res = await apiFetch(`/api/songs?language=${encodeURIComponent(languageName)}`);
    const data = await res.json();
    const songs = data.songs || [];

    detailType.textContent = 'LANGUAGE';
    detailTitle.textContent = languageName;
    detailSubtitle.textContent = `${songs.length} tracks`;
    detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';

    detailPlayBtn.onclick = () => playFromList(songs, 0);
    detailShuffleBtn.onclick = () => playShuffledList(songs);
    detailDownloadBtn.onclick = () => downloadSongsBatchZip(songs.map(s => s.id), `${languageName}_language.zip`);
    detailShareBtn.onclick = () => {
      const shareUrl = `${window.location.origin}/#lang-${encodeURIComponent(languageName)}`;
      navigator.clipboard.writeText(shareUrl);
      alert(`Copied link for language "${languageName}"!`);
    };

    renderSongList(songs, detailSongList, true);
    switchView('detail');
  } catch (e) {
    console.error('Error opening language detail:', e);
  }
}

async function openDecadeDetail(decade) {
  try {
    state.currentPlaylist = null;
    if (detailAddSongsBtn) detailAddSongsBtn.classList.add('hidden');
    if (detailDeleteBtn) detailDeleteBtn.classList.add('hidden');

    const res = await apiFetch(`/api/songs?decade=${encodeURIComponent(decade)}`);
    const data = await res.json();
    const songs = data.songs || [];

    detailType.textContent = 'DECADE / ERA';
    detailTitle.textContent = decade;
    detailSubtitle.textContent = `${songs.length} tracks`;
    detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';

    detailPlayBtn.onclick = () => playFromList(songs, 0);
    detailShuffleBtn.onclick = () => playShuffledList(songs);
    detailDownloadBtn.onclick = () => downloadSongsBatchZip(songs.map(s => s.id), `${decade}.zip`);
    detailShareBtn.onclick = () => {
      const shareUrl = `${window.location.origin}/#era-${encodeURIComponent(decade)}`;
      navigator.clipboard.writeText(shareUrl);
      alert(`Copied link for era "${decade}"!`);
    };

    renderSongList(songs, detailSongList, true);
    switchView('detail');
  } catch (e) {
    console.error('Error opening decade detail:', e);
  }
}

async function openYearDetail(year) {
  try {
    state.currentPlaylist = null;
    if (detailAddSongsBtn) detailAddSongsBtn.classList.add('hidden');
    if (detailDeleteBtn) detailDeleteBtn.classList.add('hidden');

    const res = await apiFetch(`/api/songs?year=${encodeURIComponent(year)}`);
    const data = await res.json();
    const songs = data.songs || [];

    detailType.textContent = 'RELEASE YEAR';
    detailTitle.textContent = String(year);
    detailSubtitle.textContent = `${songs.length} tracks`;
    detailCoverImg.src = songs[0] ? getCoverUrl(songs[0]) : '/icon.svg';

    detailPlayBtn.onclick = () => playFromList(songs, 0);
    detailShuffleBtn.onclick = () => playShuffledList(songs);
    detailDownloadBtn.onclick = () => downloadSongsBatchZip(songs.map(s => s.id), `Year_${year}.zip`);
    detailShareBtn.onclick = () => {
      const shareUrl = `${window.location.origin}/#year-${year}`;
      navigator.clipboard.writeText(shareUrl);
      alert(`Copied link for year ${year}!`);
    };

    renderSongList(songs, detailSongList, true);
    switchView('detail');
  } catch (e) {
    console.error('Error opening year detail:', e);
  }
}

// Genres, Languages & Years APIs and Renderers
async function fetchGenres() {
  try {
    const res = await apiFetch('/api/genres?media_type=audio');
    const data = await res.json();
    state.genres = data.genres || [];
    renderGenres(state.genres);
    populateMusicFilterDropdowns();
  } catch (e) {
    console.error('Error fetching genres:', e);
  }
}

function renderGenres(genres) {
  if (!genresGridEl) return;
  genresGridEl.innerHTML = '';
  if (!genres || genres.length === 0) {
    genresGridEl.innerHTML = `
      <div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--text-muted);">
        <p>No genres detected in your audio files yet.</p>
        <p style="font-size: 0.85rem; margin-top: 8px;">Scan your library or use the metadata editor to tag genres.</p>
      </div>
    `;
    return;
  }

  const GRADIENTS = [
    'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
    'linear-gradient(135deg, #059669 0%, #10b981 100%)',
    'linear-gradient(135deg, #d97706 0%, #f59e0b 100%)',
    'linear-gradient(135deg, #dc2626 0%, #ef4444 100%)',
    'linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)',
    'linear-gradient(135deg, #7c2d12 0%, #ea580c 100%)',
    'linear-gradient(135deg, #4c1d95 0%, #8b5cf6 100%)',
    'linear-gradient(135deg, #047857 0%, #34d399 100%)',
    'linear-gradient(135deg, #be185d 0%, #ec4899 100%)',
    'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
  ];

  genres.forEach((g, idx) => {
    const card = document.createElement('div');
    card.className = 'category-card';
    card.style.background = GRADIENTS[idx % GRADIENTS.length];
    card.innerHTML = `
      <div class="category-icon">🎵</div>
      <div class="category-info">
        <h3 class="category-title">${escapeHtml(g.genre)}</h3>
        <span class="category-subtitle">${g.count} tracks</span>
      </div>
    `;
    card.addEventListener('click', () => openGenreDetail(g.genre));
    genresGridEl.appendChild(card);
  });
}

async function fetchLanguages() {
  try {
    const res = await apiFetch('/api/languages?media_type=audio');
    const data = await res.json();
    state.languages = data.languages || [];
    renderLanguages(state.languages);
    populateMusicFilterDropdowns();
  } catch (e) {
    console.error('Error fetching languages:', e);
  }
}

function renderLanguages(languages) {
  if (!languagesGridEl) return;
  languagesGridEl.innerHTML = '';
  if (!languages || languages.length === 0) {
    languagesGridEl.innerHTML = `
      <div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--text-muted);">
        <p>No languages detected in your library yet.</p>
        <p style="font-size: 0.85rem; margin-top: 8px;">Tag languages using the metadata editor.</p>
      </div>
    `;
    return;
  }

  const LANG_ICONS = {
    'English': '🇬🇧',
    'Hindi': '🇮🇳',
    'Spanish': '🇪🇸',
    'French': '🇫🇷',
    'German': '🇩🇪',
    'Japanese': '🇯🇵',
    'Korean': '🇰🇷',
    'Chinese': '🇨🇳',
    'Punjabi': '🇮🇳',
    'Tamil': '🇮🇳',
    'Telugu': '🇮🇳',
    'Arabic': '🇸🇦',
    'Italian': '🇮🇹',
    'Russian': '🇷🇺',
    'Portuguese': '🇧🇷'
  };

  const GRADIENTS = [
    'linear-gradient(135deg, #0e7490 0%, #06b6d4 100%)',
    'linear-gradient(135deg, #4338ca 0%, #6366f1 100%)',
    'linear-gradient(135deg, #b45309 0%, #f59e0b 100%)',
    'linear-gradient(135deg, #be123c 0%, #f43f5e 100%)',
    'linear-gradient(135deg, #047857 0%, #10b981 100%)',
  ];

  languages.forEach((l, idx) => {
    const card = document.createElement('div');
    card.className = 'category-card';
    card.style.background = GRADIENTS[idx % GRADIENTS.length];
    const icon = LANG_ICONS[l.language] || '🌐';

    card.innerHTML = `
      <div class="category-icon">${icon}</div>
      <div class="category-info">
        <h3 class="category-title">${escapeHtml(l.language)}</h3>
        <span class="category-subtitle">${l.count} tracks</span>
      </div>
    `;
    card.addEventListener('click', () => openLanguageDetail(l.language));
    languagesGridEl.appendChild(card);
  });
}

async function fetchYears() {
  try {
    const res = await apiFetch('/api/years?media_type=audio');
    const data = await res.json();
    state.yearsData = data;
    renderYears(data.decades || [], data.years || []);
    populateMusicFilterDropdowns();
  } catch (e) {
    console.error('Error fetching years:', e);
  }
}

function renderYears(decades, years) {
  if (decadesGridEl) {
    decadesGridEl.innerHTML = '';
    const GRADIENTS = [
      'linear-gradient(135deg, #9333ea 0%, #c084fc 100%)',
      'linear-gradient(135deg, #2563eb 0%, #60a5fa 100%)',
      'linear-gradient(135deg, #059669 0%, #34d399 100%)',
      'linear-gradient(135deg, #d97706 0%, #fbbf24 100%)',
      'linear-gradient(135deg, #dc2626 0%, #f87171 100%)',
    ];

    if (!decades || decades.length === 0) {
      decadesGridEl.innerHTML = '<p style="color:var(--text-muted); grid-column:1/-1;">No release years found in tracks.</p>';
    } else {
      decades.forEach((d, idx) => {
        const card = document.createElement('div');
        card.className = 'category-card';
        card.style.background = GRADIENTS[idx % GRADIENTS.length];
        card.innerHTML = `
          <div class="category-icon">⏳</div>
          <div class="category-info">
            <h3 class="category-title">${escapeHtml(d.decade)}</h3>
            <span class="category-subtitle">${d.count} tracks</span>
          </div>
        `;
        card.addEventListener('click', () => openDecadeDetail(d.decade));
        decadesGridEl.appendChild(card);
      });
    }
  }

  if (yearsPillsEl) {
    yearsPillsEl.innerHTML = '';
    years.forEach(y => {
      const pill = document.createElement('button');
      pill.className = 'year-pill';
      pill.textContent = `${y.year} (${y.count})`;
      pill.addEventListener('click', () => openYearDetail(y.year));
      yearsPillsEl.appendChild(pill);
    });
  }
}

async function populateMusicFilterDropdowns() {
  if (filterGenreSelect && filterGenreSelect.options.length <= 1) {
    try {
      if (state.genres.length === 0) {
        const res = await apiFetch('/api/genres?media_type=audio');
        const data = await res.json();
        state.genres = data.genres || [];
      }
      filterGenreSelect.innerHTML = '<option value="">All Genres</option>';
      state.genres.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.genre;
        opt.textContent = `${g.genre} (${g.count})`;
        filterGenreSelect.appendChild(opt);
      });
      if (state.selectedGenre) filterGenreSelect.value = state.selectedGenre;
    } catch (e) {}
  }

  if (filterLanguageSelect && filterLanguageSelect.options.length <= 1) {
    try {
      if (state.languages.length === 0) {
        const res = await apiFetch('/api/languages?media_type=audio');
        const data = await res.json();
        state.languages = data.languages || [];
      }
      filterLanguageSelect.innerHTML = '<option value="">All Languages</option>';
      state.languages.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.language;
        opt.textContent = `${l.language} (${l.count})`;
        filterLanguageSelect.appendChild(opt);
      });
      if (state.selectedLanguage) filterLanguageSelect.value = state.selectedLanguage;
    } catch (e) {}
  }

  if (filterYearSelect && filterYearSelect.options.length <= 1) {
    try {
      if (!state.yearsData) {
        const res = await apiFetch('/api/years?media_type=audio');
        state.yearsData = await res.json();
      }
      filterYearSelect.innerHTML = '<option value="">All Years</option>';
      (state.yearsData?.years || []).forEach(y => {
        const opt = document.createElement('option');
        opt.value = y.year;
        opt.textContent = `${y.year} (${y.count})`;
        filterYearSelect.appendChild(opt);
      });
      if (state.selectedYear) filterYearSelect.value = state.selectedYear;
    } catch (e) {}
  }
}

// Web Audio API 5-Band Equalizer & Visualizer Engine
let audioCtx = null;
let audioSourceNode = null;
let eqFilters = [];
let analyserNode = null;
let visualizerAnimationId = null;

const EQ_PRESETS = {
  flat: [0, 0, 0, 0, 0],
  bass: [6, 4, 0, -1, -2],
  treble: [-2, -1, 1, 4, 6],
  vocal: [-2, 1, 4, 3, -1],
  rock: [5, 3, -1, 3, 5],
  pop: [-1, 2, 5, 2, -2],
  electronic: [6, 3, 0, 2, 5],
  jazz: [4, 2, -2, 2, 4],
  classical: [5, 3, -1, 2, 4]
};

function initAudioEngine() {
  if (audioCtx) {
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    return;
  }
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    audioCtx = new AudioContextClass();
    audioSourceNode = audioCtx.createMediaElementSource(audio);

    const freqs = [60, 250, 1000, 4000, 14000];
    const types = ['lowshelf', 'peaking', 'peaking', 'peaking', 'highshelf'];
    eqFilters = freqs.map((freq, i) => {
      const filter = audioCtx.createBiquadFilter();
      filter.type = types[i];
      filter.frequency.value = freq;
      filter.gain.value = state.isEqualizerEnabled ? (state.eqGains[i] || 0) : 0;
      return filter;
    });

    analyserNode = audioCtx.createAnalyser();
    analyserNode.fftSize = 64;

    let lastNode = audioSourceNode;
    eqFilters.forEach(filter => {
      lastNode.connect(filter);
      lastNode = filter;
    });
    lastNode.connect(analyserNode);
    analyserNode.connect(audioCtx.destination);
  } catch (e) {
    console.warn('AudioEngine init notice:', e);
  }
}

function applyEqGains(gains) {
  state.eqGains = gains;
  const bands = [60, 250, 1000, 4000, 14000];
  bands.forEach((b, i) => {
    const gain = state.isEqualizerEnabled ? gains[i] : 0;
    if (eqFilters[i]) eqFilters[i].gain.value = gain;
    const slider = document.getElementById(`eq-band-${b}`);
    const label = document.getElementById(`eq-gain-${b}`);
    if (slider) slider.value = gains[i];
    if (label) label.textContent = `${gains[i] > 0 ? '+' : ''}${gains[i]}dB`;
  });
}

function startVisualizer() {
  if (!audioVisualizerCanvas || !analyserNode) return;
  if (visualizerAnimationId) cancelAnimationFrame(visualizerAnimationId);

  const canvas = audioVisualizerCanvas;
  const ctx = canvas.getContext('2d');
  const bufferLength = analyserNode.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    visualizerAnimationId = requestAnimationFrame(draw);
    if (!state.isPlaying) return;

    analyserNode.getByteFrequencyData(dataArray);

    const width = canvas.width = canvas.parentElement ? canvas.parentElement.clientWidth : 300;
    const height = canvas.height = canvas.parentElement ? canvas.parentElement.clientHeight : 44;

    ctx.clearRect(0, 0, width, height);

    const barCount = 28;
    const barWidth = (width / barCount) - 3;
    let x = 0;

    for (let i = 0; i < barCount; i++) {
      const dataIndex = Math.floor(i * (bufferLength / barCount));
      const value = dataArray[dataIndex] || 0;
      const percent = value / 255;
      const barHeight = Math.max(3, percent * height);

      const grad = ctx.createLinearGradient(0, height, 0, height - barHeight);
      grad.addColorStop(0, '#6366f1');
      grad.addColorStop(0.6, '#818cf8');
      grad.addColorStop(1, '#a855f7');

      ctx.fillStyle = grad;
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(x, height - barHeight, Math.max(2, barWidth), barHeight, [3, 3, 0, 0]);
        ctx.fill();
      } else {
        ctx.fillRect(x, height - barHeight, Math.max(2, barWidth), barHeight);
      }

      x += barWidth + 3;
    }
  }

  draw();
}

function stopVisualizer() {
  if (visualizerAnimationId) {
    cancelAnimationFrame(visualizerAnimationId);
    visualizerAnimationId = null;
  }
  if (audioVisualizerCanvas) {
    const ctx = audioVisualizerCanvas.getContext('2d');
    ctx.clearRect(0, 0, audioVisualizerCanvas.width, audioVisualizerCanvas.height);
  }
}

// Player Logic
function playFromList(list, index) {
  state.queue = [...list];
  loadTrack(index, true);
}

function loadTrack(index, autoPlay = true) {
  if (index < 0 || index >= state.queue.length) return;
  clearPlaybackNotice();
  state.currentIndex = index;
  const song = state.queue[index];
  state.currentTrack = song;

  audio.src = song.isLocal ? song.url : (song.stream_url || `/api/stream/${song.id}`);
  audio.playbackRate = state.playbackSpeed;
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

  const fullGenreBadge = document.getElementById('full-genre-badge');
  if (fullGenreBadge) {
    if (song.genre && song.genre !== 'Unknown') {
      fullGenreBadge.textContent = song.genre;
      fullGenreBadge.classList.remove('hidden');
    } else {
      fullGenreBadge.classList.add('hidden');
    }
  }

  const fullLangBadge = document.getElementById('full-lang-badge');
  if (fullLangBadge) {
    if (song.language && song.language !== 'Unknown') {
      fullLangBadge.textContent = song.language;
      fullLangBadge.classList.remove('hidden');
    } else {
      fullLangBadge.classList.add('hidden');
    }
  }

  if (fullAddPlBtn) fullAddPlBtn.onclick = () => openAddToPlaylistModal(song);
  if (fullDownloadBtn) {
    fullDownloadBtn.onclick = () => {
      const a = document.createElement('a');
      a.href = `/api/stream/${song.id}?download=true`;
      a.download = `${song.title || 'track'}.mp3`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    };
  }
  if (fullShareBtn) {
    fullShareBtn.onclick = () => {
      const shareUrl = `${window.location.origin}/#track-${song.id}`;
      if (navigator.share) {
        navigator.share({
          title: song.title || 'Track',
          text: `Listen to "${song.title}" by ${song.artist || 'Unknown'} on MediaHub:`,
          url: shareUrl
        }).catch(() => {});
      } else {
        navigator.clipboard.writeText(shareUrl);
        alert('Track link copied to clipboard!');
      }
    };
  }

  updatePlayerLoveButton(song.is_favorite);

  document.querySelectorAll('.song-row').forEach(row => {
    row.classList.toggle('playing', row.dataset.songId === song.id);
  });

  updateMediaSession(song, coverUrl);
  if (autoPlay) playAudio();
  renderQueue();
}

function playAudio() {
  initAudioEngine();
  startVisualizer();
  audio.play().then(() => {
    state.isPlaying = true;
    updatePlayIcons(true);
    if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
  }).catch(e => console.warn(e));
}

function pauseAudio() {
  audio.pause();
  stopVisualizer();
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
  if (state.sleepAtTrackEnd) {
    clearSleepTimer();
    pauseAudio();
    return;
  }
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
  if (viewName === 'songs') { fetchSongs(); populateMusicFilterDropdowns(); }
  if (viewName === 'videos') fetchVideos();
  if (viewName === 'photos') fetchPhotos();
  if (viewName === 'favorites') fetchFavorites();
  if (viewName === 'downloader') { pollDownloads(); populateDownloaderPlaylists(); }
  if (viewName === 'peers') fetchPeers();
  if (viewName === 'privacy') fetchSettings();
  if (viewName === 'artists') fetchArtists();
  if (viewName === 'albums') fetchAlbums();
  if (viewName === 'playlists') fetchPlaylists();
  if (viewName === 'genres') fetchGenres();
  if (viewName === 'languages') fetchLanguages();
  if (viewName === 'years') fetchYears();
}

// --- Photos Logic ---
async function fetchPhotos(album = '', scope = state.mediaScope || 'all') {
  try {
    let url = `/api/photos?scope=${scope}&client_id=${clientId}`;
    if (album) url += `&album=${encodeURIComponent(album)}`;
    const res = await apiFetch(url);
    const data = await res.json();
    state.photos = data.photos || [];
    renderPhotos(state.photos);
    fetchPhotoTimeline();
    fetchPhotoAlbums();
    fetchActiveStatuses();
  } catch (err) {
    console.error('Error fetching photos:', err);
  }
}

async function fetchPhotoTimeline() {
  try {
    const res = await apiFetch('/api/photos/timeline');
    const data = await res.json();
    state.photosTimeline = data.timeline || [];
  } catch (err) {}
}

async function fetchPhotoAlbums() {
  try {
    const res = await apiFetch('/api/photos/albums');
    const data = await res.json();
    state.photosAlbums = data.albums || [];
    renderPhotoAlbumsDropdown(data.albums || []);
  } catch (err) {}
}

function renderPhotoAlbumsDropdown(albums) {
  if (!photosAlbumFilter) return;
  const currentVal = photosAlbumFilter.value;
  photosAlbumFilter.innerHTML = '<option value="">All Albums</option>';
  albums.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.album;
    opt.textContent = `${a.album} (${a.count})`;
    if (a.album === currentVal) opt.selected = true;
    photosAlbumFilter.appendChild(opt);
  });
}

function renderPhotos(photos) {
  if (!photosTimelineContainer) return;
  photosTimelineContainer.innerHTML = '';
  if (photosCountBadge) photosCountBadge.textContent = `${photos.length} photos`;

  if (!photos || photos.length === 0) {
    photosTimelineContainer.innerHTML = `
      <div style="padding: 60px 20px; text-align: center; color: var(--text-muted);">
        <div style="font-size: 3rem; margin-bottom: 12px;">📷</div>
        <h3 style="color: var(--text-primary); margin-bottom: 6px;">No photos shared yet</h3>
        <p style="font-size: 0.88rem; max-width: 400px; margin: 0 auto 16px;">
          Share photos from your phone camera roll, or add your Pictures folder in Settings to browse across Wi-Fi.
        </p>
        <button id="empty-upload-photos-btn" class="primary-btn" style="margin: 0 auto;">
          <span>Upload Photos</span>
        </button>
      </div>
    `;
    const btn = document.getElementById('empty-upload-photos-btn');
    if (btn) btn.addEventListener('click', () => photoUploadInput && photoUploadInput.click());
    return;
  }

  const monthNames = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const groups = {};
  photos.forEach(p => {
    let groupKey = 'Recent Photos';
    if (p.year && p.month) {
      groupKey = `${monthNames[p.month] || ''} ${p.year}`;
    } else if (p.date_taken) {
      groupKey = p.date_taken.substring(0, 7);
    }
    if (!groups[groupKey]) groups[groupKey] = [];
    groups[groupKey].push(p);
  });

  Object.entries(groups).forEach(([groupName, groupPhotos]) => {
    const groupEl = document.createElement('div');
    groupEl.className = 'photo-timeline-group';

    groupEl.innerHTML = `
      <div class="photo-timeline-header">
        <h3>${escapeHtml(groupName)}</h3>
        <span class="photo-timeline-count">${groupPhotos.length} photo${groupPhotos.length === 1 ? '' : 's'}</span>
      </div>
      <div class="photo-grid"></div>
    `;

    const grid = groupEl.querySelector('.photo-grid');
    groupPhotos.forEach(photo => {
      const globalIdx = photos.indexOf(photo);
      const card = document.createElement('div');
      card.className = 'photo-card';
      const thumbUrl = `/api/photo/${photo.id}/thumb`;
      const ownerLabel = (photo.source_device && photo.source_device !== 'My Device') ? photo.source_device : (photo.owner_name !== 'Host' ? photo.owner_name : '');

      card.innerHTML = `
        <img src="${thumbUrl}" alt="${escapeHtml(photo.title)}" loading="lazy">
        <div class="photo-card-overlay">
          ${ownerLabel ? `<span class="photo-source-badge">📱 ${escapeHtml(ownerLabel)}</span>` : '<span></span>'}
          <span class="photo-card-title">${escapeHtml(photo.title)}</span>
        </div>
      `;

      card.addEventListener('click', () => openPhotoLightbox(globalIdx));
      grid.appendChild(card);
    });

    photosTimelineContainer.appendChild(groupEl);
  });
}

// Lightbox
let activePhotoIndex = -1;

function openPhotoLightbox(index) {
  if (!state.photos || index < 0 || index >= state.photos.length) return;
  activePhotoIndex = index;
  const photo = state.photos[index];

  if (photoLightboxModal) photoLightboxModal.classList.remove('hidden');
  if (lightboxImg) lightboxImg.src = `/api/photo/${photo.id}/raw`;
  if (lightboxTitle) lightboxTitle.textContent = photo.title || 'Photo';
  
  const metaParts = [];
  if (photo.date_taken) metaParts.push(photo.date_taken);
  if (photo.camera_model) metaParts.push(`📷 ${photo.camera_model}`);
  if (photo.width && photo.height) metaParts.push(`${photo.width}×${photo.height}`);
  if (photo.owner_name && photo.owner_name !== 'Host') metaParts.push(`Uploaded by ${photo.owner_name}`);
  if (lightboxMeta) lightboxMeta.textContent = metaParts.join(' • ') || '-';

  if (lightboxDownloadBtn) {
    lightboxDownloadBtn.href = `/api/photo/${photo.id}/raw?download=true`;
  }
  if (lightboxVlcBtn) {
    lightboxVlcBtn.href = `vlc://${window.location.origin}/api/photo/${photo.id}/raw`;
  }

  if (lightboxPrevBtn) lightboxPrevBtn.style.visibility = index > 0 ? 'visible' : 'hidden';
  if (lightboxNextBtn) lightboxNextBtn.style.visibility = index < state.photos.length - 1 ? 'visible' : 'hidden';
}

function closePhotoLightbox() {
  if (photoLightboxModal) photoLightboxModal.classList.add('hidden');
  if (lightboxImg) lightboxImg.src = '';
  activePhotoIndex = -1;
}

function prevPhoto() {
  if (activePhotoIndex > 0) openPhotoLightbox(activePhotoIndex - 1);
}

function nextPhoto() {
  if (activePhotoIndex < state.photos.length - 1) openPhotoLightbox(activePhotoIndex + 1);
}

// ==========================================================================
// 24-Hour Ephemeral Status & Field Monitoring Logic
// ==========================================================================

function formatTimeAgo(epochSeconds) {
  if (!epochSeconds) return 'recently';
  const diff = Math.max(0, Math.floor(Date.now() / 1000 - epochSeconds));
  if (diff < 60) return 'Just now';
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return 'Yesterday';
}

function formatTimeRemaining(remainingSeconds) {
  if (isNaN(remainingSeconds) || remainingSeconds <= 0) return '0m';
  const mins = Math.floor(remainingSeconds / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hours}h ${remMins}m`;
}

async function fetchActiveStatuses() {
  try {
    const res = await apiFetch(`/api/status/active?client_id=${clientId}`);
    if (!res.ok) return;
    const data = await res.json();
    state.statusGroups = data.groups || [];
    if (activeStatusBadge) {
      activeStatusBadge.textContent = `${data.total_active || 0} active`;
    }
    renderStoriesCarousel(state.statusGroups);
  } catch (err) {
    console.error('Error fetching active statuses:', err);
  }
}

function renderStoriesCarousel(groups) {
  if (!storiesCarousel) return;
  storiesCarousel.innerHTML = '';

  // 1. "Add Status" / Check-in circle
  const addCard = document.createElement('div');
  addCard.className = 'story-circle-item';
  addCard.title = 'Post a 24-hour disappearing photo status update';
  addCard.innerHTML = `
    <div class="story-avatar-ring add-ring">
      <div class="story-avatar-inner" style="background: rgba(236, 72, 153, 0.1); color: #ec4899; font-size: 1.5rem; font-weight: 300;">
        +
      </div>
    </div>
    <span class="story-username-label" style="font-weight: 600; color: #ec4899;">Your Status</span>
  `;
  addCard.addEventListener('click', openPostStatusModal);
  storiesCarousel.appendChild(addCard);

  if (!groups || groups.length === 0) {
    return;
  }

  // 2. Each worker's / peer's active status group
  groups.forEach((group, gIdx) => {
    const itemCard = document.createElement('div');
    itemCard.className = 'story-circle-item';
    const latestItem = group.items[group.items.length - 1];
    const thumbUrl = latestItem ? latestItem.image_url : '';
    const initial = (group.owner_name || 'P').charAt(0).toUpperCase();

    itemCard.innerHTML = `
      <div class="story-avatar-ring">
        <div class="story-avatar-inner">
          ${thumbUrl ? `<img src="${thumbUrl}" alt="${escapeHtml(group.owner_name)}">` : initial}
        </div>
        <span class="story-badge-count">${group.items.length}</span>
      </div>
      <span class="story-username-label" title="${escapeHtml(group.owner_name)}">
        ${group.is_owner ? 'You' : escapeHtml(group.owner_name)}
      </span>
    `;

    itemCard.addEventListener('click', () => openStoryViewer(gIdx, 0));
    storiesCarousel.appendChild(itemCard);
  });
}

function openStoryViewer(groupIndex, itemIndex = 0) {
  if (!state.statusGroups || groupIndex < 0 || groupIndex >= state.statusGroups.length) return;
  state.activeStatusGroupIndex = groupIndex;
  state.activeStatusItemIndex = itemIndex;

  if (storyViewerModal) storyViewerModal.classList.remove('hidden');
  renderCurrentStoryItem();
}

function closeStoryViewer() {
  clearTimeout(state.statusTimer);
  clearInterval(state.statusProgressInterval);
  if (storyViewerModal) storyViewerModal.classList.add('hidden');
  if (storyImg) storyImg.src = '';
  state.activeStatusGroupIndex = -1;
  state.activeStatusItemIndex = -1;
}

function renderCurrentStoryItem() {
  clearTimeout(state.statusTimer);
  clearInterval(state.statusProgressInterval);

  const group = state.statusGroups[state.activeStatusGroupIndex];
  if (!group || !group.items || group.items.length === 0) {
    closeStoryViewer();
    return;
  }
  const item = group.items[state.activeStatusItemIndex];
  if (!item) {
    closeStoryViewer();
    return;
  }

  // 1. Progress Bars
  if (storyProgressContainer) {
    storyProgressContainer.innerHTML = '';
    group.items.forEach((it, idx) => {
      const bar = document.createElement('div');
      bar.className = 'story-progress-bar';
      const fill = document.createElement('div');
      fill.className = 'story-progress-fill';
      if (idx < state.activeStatusItemIndex) {
        fill.style.width = '100%';
      } else if (idx === state.activeStatusItemIndex) {
        fill.style.width = '0%';
        fill.id = 'active-story-progress-fill';
      } else {
        fill.style.width = '0%';
      }
      bar.appendChild(fill);
      storyProgressContainer.appendChild(bar);
    });
  }

  // 2. Header info
  if (storyAvatarSmall) storyAvatarSmall.textContent = group.is_owner ? '👤' : '📱';
  if (storyUsername) storyUsername.textContent = `${group.owner_name}${group.is_owner ? ' (You)' : ''}`;
  if (storyMeta) {
    const timeAgo = formatTimeAgo(item.created_at);
    const timeLeft = formatTimeRemaining(item.expires_in_seconds);
    storyMeta.textContent = `${timeAgo} • ⏳ ${timeLeft} left`;
  }

  // 3. Image
  if (storyImg) storyImg.src = item.image_url;

  // 4. Caption
  if (storyCaptionBar && storyCaptionText) {
    if (item.caption && item.caption.trim()) {
      storyCaptionBar.style.display = 'block';
      storyCaptionText.textContent = item.caption;
    } else {
      storyCaptionBar.style.display = 'none';
      storyCaptionText.textContent = '';
    }
  }

  // 5. Actions
  if (storySaveBtn) {
    if (item.is_saved) {
      storySaveBtn.innerHTML = '<span>✓ Preserved</span>';
      storySaveBtn.style.background = 'rgba(16, 185, 129, 0.35)';
      storySaveBtn.disabled = true;
    } else {
      storySaveBtn.innerHTML = '<span>📥 Save to Server</span>';
      storySaveBtn.style.background = '';
      storySaveBtn.disabled = false;
      storySaveBtn.onclick = () => saveStatusToServer(item.id, storySaveBtn);
    }
  }

  if (storyDownloadBtn) {
    storyDownloadBtn.href = item.download_url;
  }

  if (storyDeleteBtn) {
    if (item.is_owner || state.isAdmin) {
      storyDeleteBtn.style.display = 'flex';
      storyDeleteBtn.onclick = () => deleteStatusItem(item.id);
    } else {
      storyDeleteBtn.style.display = 'none';
    }
  }

  // 6. Navigation arrows visibility
  if (storyPrevBtn) {
    storyPrevBtn.style.visibility = (state.activeStatusGroupIndex > 0 || state.activeStatusItemIndex > 0) ? 'visible' : 'hidden';
  }
  if (storyNextBtn) {
    storyNextBtn.style.visibility = 'visible';
  }

  // 7. Auto-advance animation (5.5s timer)
  const durationMs = 5500;
  const startTime = Date.now();
  const fillEl = document.getElementById('active-story-progress-fill');

  state.statusProgressInterval = setInterval(() => {
    const elapsed = Date.now() - startTime;
    const pct = Math.min(100, (elapsed / durationMs) * 100);
    if (fillEl) fillEl.style.width = `${pct}%`;
  }, 50);

  state.statusTimer = setTimeout(() => {
    nextStoryItem();
  }, durationMs);
}

function nextStoryItem() {
  clearTimeout(state.statusTimer);
  clearInterval(state.statusProgressInterval);
  const group = state.statusGroups[state.activeStatusGroupIndex];
  if (!group) {
    closeStoryViewer();
    return;
  }

  if (state.activeStatusItemIndex < group.items.length - 1) {
    state.activeStatusItemIndex++;
    renderCurrentStoryItem();
  } else if (state.activeStatusGroupIndex < state.statusGroups.length - 1) {
    state.activeStatusGroupIndex++;
    state.activeStatusItemIndex = 0;
    renderCurrentStoryItem();
  } else {
    closeStoryViewer();
  }
}

function prevStoryItem() {
  clearTimeout(state.statusTimer);
  clearInterval(state.statusProgressInterval);
  if (state.activeStatusItemIndex > 0) {
    state.activeStatusItemIndex--;
    renderCurrentStoryItem();
  } else if (state.activeStatusGroupIndex > 0) {
    state.activeStatusGroupIndex--;
    const prevGroup = state.statusGroups[state.activeStatusGroupIndex];
    state.activeStatusItemIndex = Math.max(0, prevGroup.items.length - 1);
    renderCurrentStoryItem();
  }
}

async function saveStatusToServer(statusId, btnEl = null) {
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Saving...';
  }
  try {
    const res = await apiFetch(`/api/status/${statusId}/save`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      alert(data.message || 'Saved permanently to server Photos library!');
      if (btnEl) {
        btnEl.innerHTML = '<span>✓ Preserved</span>';
        btnEl.style.background = 'rgba(16, 185, 129, 0.35)';
      }
      // Update local item
      const group = state.statusGroups[state.activeStatusGroupIndex];
      if (group && group.items) {
        const item = group.items.find(i => i.id === statusId);
        if (item) item.is_saved = true;
      }
      fetchPhotos();
    } else {
      alert(`Save failed: ${data.detail || data.message}`);
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.innerHTML = '<span>📥 Save to Server</span>';
      }
    }
  } catch (err) {
    alert(`Save error: ${err}`);
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerHTML = '<span>📥 Save to Server</span>';
    }
  }
}

async function deleteStatusItem(statusId) {
  if (!confirm('Are you sure you want to delete this status update?')) return;
  try {
    const res = await apiFetch(`/api/status/${statusId}?client_id=${clientId}`, { method: 'DELETE' });
    if (res.ok) {
      // Remove locally from state
      const group = state.statusGroups[state.activeStatusGroupIndex];
      if (group && group.items) {
        group.items = group.items.filter(i => i.id !== statusId);
        if (group.items.length === 0) {
          state.statusGroups.splice(state.activeStatusGroupIndex, 1);
          closeStoryViewer();
        } else {
          if (state.activeStatusItemIndex >= group.items.length) {
            state.activeStatusItemIndex = group.items.length - 1;
          }
          renderCurrentStoryItem();
        }
      }
      fetchActiveStatuses();
    } else {
      const data = await res.json();
      alert(`Delete failed: ${data.detail || 'Error'}`);
    }
  } catch (err) {
    alert(`Delete error: ${err}`);
  }
}

// --- Post Status Modal Handlers ---
function openPostStatusModal() {
  if (postStatusModal) postStatusModal.classList.remove('hidden');
  resetPostStatusForm();
}

function closePostStatusModal() {
  if (postStatusModal) postStatusModal.classList.add('hidden');
  resetPostStatusForm();
}

function resetPostStatusForm() {
  state.selectedStatusFile = null;
  if (statusFileInput) statusFileInput.value = '';
  if (statusCaptionInput) statusCaptionInput.value = '';
  if (statusPreviewImg) {
    statusPreviewImg.src = '';
    statusPreviewImg.classList.add('hidden');
  }
  if (statusDropzonePlaceholder) statusDropzonePlaceholder.classList.remove('hidden');
  if (submitPostStatusBtn) {
    submitPostStatusBtn.disabled = true;
    submitPostStatusBtn.innerHTML = '<span>🚀 Publish (24h)</span>';
  }
}

function handleStatusFileSelect(file) {
  if (!file) return;
  state.selectedStatusFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    if (statusPreviewImg) {
      statusPreviewImg.src = e.target.result;
      statusPreviewImg.classList.remove('hidden');
    }
    if (statusDropzonePlaceholder) statusDropzonePlaceholder.classList.add('hidden');
    if (submitPostStatusBtn) submitPostStatusBtn.disabled = false;
  };
  reader.readAsDataURL(file);
}

async function submitStatusPost() {
  if (!state.selectedStatusFile) return;
  if (submitPostStatusBtn) {
    submitPostStatusBtn.disabled = true;
    submitPostStatusBtn.innerHTML = '<span>Uploading...</span>';
  }

  const formData = new FormData();
  formData.append('file', state.selectedStatusFile);
  formData.append('caption', statusCaptionInput ? statusCaptionInput.value : '');
  formData.append('client_id', clientId);
  formData.append('device_name', getDeviceType());

  try {
    const res = await apiFetch('/api/status/post', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      closePostStatusModal();
      fetchActiveStatuses();
      alert(data.message || 'Status published! Visible for 24 hours to all peers and host server.');
    } else {
      alert(`Failed to publish status: ${data.detail || data.message}`);
      if (submitPostStatusBtn) {
        submitPostStatusBtn.disabled = false;
        submitPostStatusBtn.innerHTML = '<span>🚀 Publish (24h)</span>';
      }
    }
  } catch (err) {
    alert(`Upload error: ${err}`);
    if (submitPostStatusBtn) {
      submitPostStatusBtn.disabled = false;
      submitPostStatusBtn.innerHTML = '<span>🚀 Publish (24h)</span>';
    }
  }
}

// Pending Uploads (Approval Queue)
async function fetchPendingUploads() {
  if (!state.isAdmin) {
    if (pendingUploadsCard) pendingUploadsCard.style.display = 'none';
    return;
  }
  try {
    const res = await apiFetch('/api/admin/pending-uploads');
    const data = await res.json();
    state.pendingUploads = data.pending || [];
    renderPendingUploads(state.pendingUploads);
  } catch (err) {
    console.error('Error fetching pending uploads:', err);
  }
}

function renderPendingUploads(items) {
  if (!pendingUploadsCard || !pendingUploadsList) return;
  if (!items || items.length === 0) {
    pendingUploadsCard.style.display = 'none';
    if (pendingUploadsBadge) pendingUploadsBadge.textContent = '0';
    return;
  }

  pendingUploadsCard.style.display = 'block';
  if (pendingUploadsBadge) pendingUploadsBadge.textContent = String(items.length);
  pendingUploadsList.innerHTML = '';

  items.forEach(item => {
    const el = document.createElement('div');
    el.className = 'pending-item';
    el.innerHTML = `
      <div class="pending-item-info">
        <span class="pending-item-name">${escapeHtml(item.filename)}</span>
        <span class="pending-item-meta">${formatBytes(item.filesize)} • from ${escapeHtml(item.owner_name || 'Peer')} (${item.media_type})</span>
      </div>
      <div class="pending-item-actions">
        <button class="approve-btn" data-id="${item.id}">Approve</button>
        <button class="reject-btn" data-id="${item.id}">Reject</button>
      </div>
    `;

    el.querySelector('.approve-btn').addEventListener('click', async () => {
      try {
        await apiFetch(`/api/admin/pending-uploads/${item.id}/approve`, { method: 'POST' });
        fetchPendingUploads();
        fetchStatus();
        fetchSongs();
        fetchVideos();
        fetchPhotos();
      } catch (e) {
        alert(`Error approving: ${e}`);
      }
    });

    el.querySelector('.reject-btn').addEventListener('click', async () => {
      try {
        await apiFetch(`/api/admin/pending-uploads/${item.id}/reject`, { method: 'POST' });
        fetchPendingUploads();
        fetchStatus();
      } catch (e) {
        alert(`Error rejecting: ${e}`);
      }
    });

    pendingUploadsList.appendChild(el);
  });
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
    else if (state.currentView === 'photos') fetchPhotos(photosAlbumFilter ? photosAlbumFilter.value : '', state.mediaScope);
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
if (playlistModalClose) playlistModalClose.addEventListener('click', () => playlistModal.classList.add('hidden'));

async function openAddToPlaylistModal(song) {
  await fetchPlaylists();
  playlistModalBody.innerHTML = '';
  if (state.playlists.length === 0) {
    playlistModalBody.innerHTML = '<p style="color:var(--text-muted); padding:10px 0;">No playlists yet. Create one first!</p>';
  } else {
    state.playlists.forEach(pl => {
      const btn = document.createElement('button');
      btn.className = 'secondary-btn';
      btn.style.marginBottom = '8px';
      btn.style.width = '100%';
      btn.style.textAlign = 'left';
      btn.textContent = `${pl.name} (${pl.song_count || 0} tracks)`;
      btn.onclick = async () => {
        try {
          const res = await apiFetch(`/api/playlists/${pl.id}/songs/${song.id}`, { method: 'POST' });
          if (res.ok) {
            playlistModal.classList.add('hidden');
            alert(`Added "${song.title || 'track'}" to "${pl.name}"`);
            fetchPlaylists();
          }
        } catch (e) {
          alert('Failed to add to playlist: ' + e);
        }
      };
      playlistModalBody.appendChild(btn);
    });
  }
  playlistModal.classList.remove('hidden');
}

// Create Playlist Modal (Manual, Smart Auto-Mix & M3U Import)
const createPlaylistModal = document.getElementById('create-playlist-modal');
const createPlaylistModalClose = document.getElementById('create-playlist-modal-close');
const cancelCreatePlaylistBtn = document.getElementById('cancel-create-playlist-btn');
const submitCreatePlaylistBtn = document.getElementById('submit-create-playlist-btn');
const newPlaylistNameInput = document.getElementById('new-playlist-name-input');
const newPlaylistDescInput = document.getElementById('new-playlist-desc-input');

// Smart Auto-Mix Panel Elements
const smartEraSelect = document.getElementById('smart-era-select');
const smartLangSelect = document.getElementById('smart-lang-select');
const smartGenreSelect = document.getElementById('smart-genre-select');
const smartNameInput = document.getElementById('smart-name-input');
const smartMatchCount = document.getElementById('smart-match-count');
const cancelSmartPlaylistBtn = document.getElementById('cancel-smart-playlist-btn');
const submitSmartPlaylistBtn = document.getElementById('submit-smart-playlist-btn');

// Import M3U Panel Elements
const m3uDropzone = document.getElementById('m3u-dropzone');
const modalM3uFileInput = document.getElementById('modal-m3u-file-input');
const m3uSelectedFileLabel = document.getElementById('m3u-selected-file-label');
const cancelImportPlaylistBtn = document.getElementById('cancel-import-playlist-btn');
const submitImportPlaylistBtn = document.getElementById('submit-import-playlist-btn');

let selectedM3UFile = null;

function switchCreatePlaylistTab(tab) {
  document.querySelectorAll('.modal-tabs .modal-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  document.querySelectorAll('.modal-tab-panel').forEach(panel => {
    panel.classList.add('hidden');
  });
  const targetPanel = document.getElementById(`tab-panel-${tab}`);
  if (targetPanel) targetPanel.classList.remove('hidden');

  if (tab === 'smart') {
    populateSmartBuilderDropdowns();
    updateSmartMatchPreview();
  }
}

document.querySelectorAll('.modal-tabs .modal-tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    switchCreatePlaylistTab(btn.dataset.tab);
  });
});

function openCreatePlaylistModal(initialTab = 'manual') {
  if (newPlaylistNameInput) newPlaylistNameInput.value = '';
  if (newPlaylistDescInput) newPlaylistDescInput.value = '';
  selectedM3UFile = null;
  if (m3uSelectedFileLabel) {
    m3uSelectedFileLabel.textContent = '';
    m3uSelectedFileLabel.classList.add('hidden');
  }
  if (submitImportPlaylistBtn) submitImportPlaylistBtn.disabled = true;

  switchCreatePlaylistTab(initialTab);
  createPlaylistModal?.classList.remove('hidden');
  if (initialTab === 'manual') newPlaylistNameInput?.focus();
}

function populateSmartBuilderDropdowns() {
  if (smartLangSelect && smartLangSelect.options.length <= 1) {
    smartLangSelect.innerHTML = '<option value="">Any Language</option>';
    (state.languages || []).forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.language;
      opt.textContent = `${l.language} (${l.count})`;
      smartLangSelect.appendChild(opt);
    });
  }

  if (smartGenreSelect && smartGenreSelect.options.length <= 1) {
    genreOptPopulate: {
      smartGenreSelect.innerHTML = '<option value="">Any Genre</option>';
      (state.genres || []).forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.genre;
        opt.textContent = `${g.genre} (${g.count})`;
        smartGenreSelect.appendChild(opt);
      });
    }
  }
}

function updateSmartMatchPreview() {
  const era = smartEraSelect?.value || '';
  const lang = smartLangSelect?.value || '';
  const genre = smartGenreSelect?.value || '';

  const eraStr = (era && era.endsWith('s')) ? era : (era ? era.toUpperCase() : '');
  let title = '';
  if (era && lang) {
    title = `${eraStr} ${lang.toUpperCase()}`;
  } else if (genre && lang) {
    title = `${genre.toUpperCase()} ${lang.toUpperCase()}`;
  } else if (genre && era) {
    title = `${eraStr} ${genre.toUpperCase()}`;
  } else if (era) {
    title = `${eraStr} HITS`;
  } else if (lang) {
    title = `${lang.toUpperCase()} HITS`;
  } else if (genre) {
    title = `${genre.toUpperCase()} HITS`;
  } else {
    title = 'SMART AUTO-MIX';
  }

  if (smartNameInput) smartNameInput.value = title;

  if (smartMatchCount && state.allSongs) {
    const matches = state.allSongs.filter(s => {
      if (genre && (s.genre || '').toLowerCase() !== genre.toLowerCase()) return false;
      if (lang && (s.language || '').toLowerCase() !== lang.toLowerCase()) return false;
      if (era) {
        const y = parseInt(s.year, 10);
        if (!y) return false;
        if (era === '2020s' && (y < 2020 || y > 2029)) return false;
        if (era === '2010s' && (y < 2010 || y > 2019)) return false;
        if (era === '2000s' && (y < 2000 || y > 2009)) return false;
        if (era === '1990s' && (y < 1990 || y > 1999)) return false;
        if (era === '1980s' && (y < 1980 || y > 1989)) return false;
        if (era === 'Classic' && y >= 1980) return false;
      }
      return true;
    });
    smartMatchCount.textContent = matches.length;
  }
}

if (smartEraSelect) smartEraSelect.addEventListener('change', updateSmartMatchPreview);
if (smartLangSelect) smartLangSelect.addEventListener('change', updateSmartMatchPreview);
if (smartGenreSelect) smartGenreSelect.addEventListener('change', updateSmartMatchPreview);

if (createPlaylistModalClose) createPlaylistModalClose.addEventListener('click', () => createPlaylistModal?.classList.add('hidden'));
if (cancelCreatePlaylistBtn) cancelCreatePlaylistBtn.addEventListener('click', () => createPlaylistModal?.classList.add('hidden'));
if (cancelSmartPlaylistBtn) cancelSmartPlaylistBtn.addEventListener('click', () => createPlaylistModal?.classList.add('hidden'));
if (cancelImportPlaylistBtn) cancelImportPlaylistBtn.addEventListener('click', () => createPlaylistModal?.classList.add('hidden'));

// Panel 1: Submit Manual Playlist
if (submitCreatePlaylistBtn) {
  submitCreatePlaylistBtn.addEventListener('click', async () => {
    const name = newPlaylistNameInput?.value.trim();
    const description = newPlaylistDescInput?.value.trim();
    if (!name) {
      alert('Please enter a playlist name.');
      return;
    }
    try {
      const res = await apiFetch('/api/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
      });
      if (res.ok) {
        createPlaylistModal?.classList.add('hidden');
        await fetchPlaylists();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to create playlist');
      }
    } catch (e) {
      alert('Error creating playlist: ' + e);
    }
  });
}

// Panel 2: Submit Smart Auto-Mix
if (submitSmartPlaylistBtn) {
  submitSmartPlaylistBtn.addEventListener('click', async () => {
    const era = smartEraSelect?.value || '';
    const lang = smartLangSelect?.value || '';
    const genre = smartGenreSelect?.value || '';
    const name = smartNameInput?.value.trim();
    if (!name) {
      alert('Please enter a playlist name.');
      return;
    }
    try {
      const res = await apiFetch('/api/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description: `Smart Auto-Mix [${[era, lang, genre].filter(Boolean).join(', ')}]`,
          is_smart: true,
          criteria: {
            decade: era || undefined,
            language: lang || undefined,
            genre: genre || undefined
          }
        })
      });
      if (res.ok) {
        const data = await res.json();
        createPlaylistModal?.classList.add('hidden');
        await fetchPlaylists();
        if (data.playlist) openPlaylistDetail(data.playlist);
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to create smart playlist');
      }
    } catch (e) {
      alert('Error creating smart playlist: ' + e);
    }
  });
}

// Panel 3: Import M3U
async function uploadAndImportM3U(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await apiFetch('/api/playlists/import', {
      method: 'POST',
      body: formData
    });
    if (res.ok) {
      const data = await res.json();
      alert(`Successfully imported playlist "${data.name}"! Matched ${data.matched_tracks} of ${data.total_tracks} tracks.`);
      createPlaylistModal?.classList.add('hidden');
      await fetchPlaylists();
      if (data.playlist_id) {
        const pl = state.playlists.find(p => p.id === data.playlist_id) || { id: data.playlist_id, name: data.name };
        openPlaylistDetail(pl);
      }
    } else {
      const err = await res.json();
      alert(err.detail || 'Failed to import playlist');
    }
  } catch (e) {
    alert('Error importing playlist: ' + e);
  }
}

if (m3uDropzone) {
  m3uDropzone.addEventListener('click', () => modalM3uFileInput?.click());
  m3uDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    m3uDropzone.style.borderColor = 'var(--accent)';
    m3uDropzone.style.background = 'rgba(99, 102, 241, 0.08)';
  });
  m3uDropzone.addEventListener('dragleave', () => {
    m3uDropzone.style.borderColor = 'var(--border-subtle)';
    m3uDropzone.style.background = 'rgba(255, 255, 255, 0.02)';
  });
  m3uDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    m3uDropzone.style.borderColor = 'var(--border-subtle)';
    m3uDropzone.style.background = 'rgba(255, 255, 255, 0.02)';
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      selectedM3UFile = e.dataTransfer.files[0];
      if (m3uSelectedFileLabel) {
        m3uSelectedFileLabel.textContent = `Selected: ${selectedM3UFile.name}`;
        m3uSelectedFileLabel.classList.remove('hidden');
      }
      if (submitImportPlaylistBtn) submitImportPlaylistBtn.disabled = false;
    }
  });
}

if (modalM3uFileInput) {
  modalM3uFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      selectedM3UFile = e.target.files[0];
      if (m3uSelectedFileLabel) {
        m3uSelectedFileLabel.textContent = `Selected: ${selectedM3UFile.name}`;
        m3uSelectedFileLabel.classList.remove('hidden');
      }
      if (submitImportPlaylistBtn) submitImportPlaylistBtn.disabled = false;
    }
  });
}

if (submitImportPlaylistBtn) {
  submitImportPlaylistBtn.addEventListener('click', () => {
    if (selectedM3UFile) uploadAndImportM3U(selectedM3UFile);
  });
}

// View-Playlists Header Controls
if (importPlaylistBtn) {
  importPlaylistBtn.addEventListener('click', () => {
    openCreatePlaylistModal('import');
  });
}

if (playlistFileImportInput) {
  playlistFileImportInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadAndImportM3U(e.target.files[0]);
    }
  });
}

if (plTabAll) {
  plTabAll.addEventListener('click', () => {
    state.activePlaylistTab = 'all';
    document.querySelectorAll('.playlist-tabs-bar .filter-pill').forEach(p => p.classList.remove('active'));
    plTabAll.classList.add('active');
    renderPlaylists();
  });
}
if (plTabSmart) {
  plTabSmart.addEventListener('click', () => {
    state.activePlaylistTab = 'smart';
    document.querySelectorAll('.playlist-tabs-bar .filter-pill').forEach(p => p.classList.remove('active'));
    plTabSmart.classList.add('active');
    renderPlaylists();
  });
}
if (plTabCustom) {
  plTabCustom.addEventListener('click', () => {
    state.activePlaylistTab = 'custom';
    document.querySelectorAll('.playlist-tabs-bar .filter-pill').forEach(p => p.classList.remove('active'));
    plTabCustom.classList.add('active');
    renderPlaylists();
  });
}

const newPlaylistBtn = document.getElementById('new-playlist-btn');
if (newPlaylistBtn) {
  newPlaylistBtn.addEventListener('click', (e) => {
    e.preventDefault();
    openCreatePlaylistModal('manual');
  });
}

// Share Playlist Modal
const sharePlaylistModal = document.getElementById('share-playlist-modal');
const sharePlaylistModalClose = document.getElementById('share-playlist-modal-close');
const sharePlaylistTitle = document.getElementById('share-playlist-title');
const sharePlaylistQr = document.getElementById('share-playlist-qr');
const sharePlaylistUrlInput = document.getElementById('share-playlist-url-input');
const copySharePlaylistUrlBtn = document.getElementById('copy-share-playlist-url-btn');
const sharePlaylistNativeBtn = document.getElementById('share-playlist-native-btn');
const sharePlaylistM3uBtn = document.getElementById('share-playlist-m3u-btn');
const sharePlaylistZipBtn = document.getElementById('share-playlist-zip-btn');

function openSharePlaylistModal(playlist) {
  if (!playlist) return;
  const shareUrl = `${window.location.origin}/#playlist-${playlist.id}`;
  if (sharePlaylistTitle) sharePlaylistTitle.textContent = `Share "${playlist.name}"`;
  if (sharePlaylistUrlInput) sharePlaylistUrlInput.value = shareUrl;
  if (sharePlaylistQr) sharePlaylistQr.src = `/api/qr?data=${encodeURIComponent(shareUrl)}`;

  if (copySharePlaylistUrlBtn) {
    copySharePlaylistUrlBtn.onclick = () => {
      navigator.clipboard.writeText(shareUrl).then(() => {
        copySharePlaylistUrlBtn.textContent = '✓ Copied!';
        setTimeout(() => { copySharePlaylistUrlBtn.textContent = 'Copy Link'; }, 2000);
      });
    };
  }

  if (sharePlaylistNativeBtn) {
    sharePlaylistNativeBtn.onclick = async () => {
      if (navigator.share) {
        try {
          await navigator.share({
            title: playlist.name,
            text: `Listen to "${playlist.name}" on MediaHub:`,
            url: shareUrl
          });
        } catch (e) {}
      } else {
        navigator.clipboard.writeText(shareUrl);
        alert('Share link copied to clipboard!');
      }
    };
  }

  if (sharePlaylistM3uBtn) {
    sharePlaylistM3uBtn.onclick = () => {
      window.open(`/api/playlists/${playlist.id}/export.m3u`, '_blank');
    };
  }

  if (sharePlaylistZipBtn) {
    sharePlaylistZipBtn.onclick = () => {
      const a = document.createElement('a');
      a.href = `/api/playlists/${playlist.id}/download`;
      a.download = `${playlist.name}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    };
  }

  sharePlaylistModal?.classList.remove('hidden');
}

if (sharePlaylistModalClose) {
  sharePlaylistModalClose.addEventListener('click', () => sharePlaylistModal?.classList.add('hidden'));
}

// Add Songs to Playlist Modal
const playlistAddSongsModal = document.getElementById('playlist-add-songs-modal');
const playlistAddSongsModalClose = document.getElementById('playlist-add-songs-modal-close');
const playlistSongSearchInput = document.getElementById('playlist-song-search-input');
const playlistAddSongsList = document.getElementById('playlist-add-songs-list');
const playlistAddSelectedCount = document.getElementById('playlist-add-selected-count');
const playlistAddCancelBtn = document.getElementById('playlist-add-cancel-btn');
const playlistAddSubmitBtn = document.getElementById('playlist-add-submit-btn');

let pendingPlaylistSongIds = new Set();
let modalAllSongsCache = [];

async function openAddSongsToPlaylistModal(playlist) {
  if (!playlist) return;
  pendingPlaylistSongIds.clear();
  if (playlistSongSearchInput) playlistSongSearchInput.value = '';
  if (playlistAddSelectedCount) playlistAddSelectedCount.textContent = '0 tracks selected';

  playlistAddSongsModal?.classList.remove('hidden');

  try {
    if (modalAllSongsCache.length === 0) {
      const res = await apiFetch('/api/songs?scope=all');
      const data = await res.json();
      modalAllSongsCache = data.songs || [];
    }
    renderAddSongsModalList(modalAllSongsCache);
  } catch (e) {
    console.error('Error fetching songs for playlist modal:', e);
  }

  if (playlistAddSubmitBtn) {
    playlistAddSubmitBtn.onclick = async () => {
      if (pendingPlaylistSongIds.size === 0) {
        alert('Please select at least one track to add.');
        return;
      }
      try {
        const res = await apiFetch(`/api/playlists/${playlist.id}/songs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ song_ids: Array.from(pendingPlaylistSongIds) })
        });
        if (res.ok) {
          playlistAddSongsModal?.classList.add('hidden');
          await openPlaylistDetail(playlist);
          await fetchPlaylists();
        } else {
          alert('Failed to add songs');
        }
      } catch (err) {
        alert('Error adding songs: ' + err);
      }
    };
  }
}

function renderAddSongsModalList(songs) {
  if (!playlistAddSongsList) return;
  playlistAddSongsList.innerHTML = '';

  const q = (playlistSongSearchInput?.value || '').toLowerCase().trim();
  const filtered = q ? songs.filter(s =>
    (s.title || '').toLowerCase().includes(q) ||
    (s.artist || '').toLowerCase().includes(q) ||
    (s.album || '').toLowerCase().includes(q)
  ) : songs;

  filtered.slice(0, 100).forEach(song => {
    const item = document.createElement('label');
    item.className = 'song-row';
    item.style.cursor = 'pointer';
    item.style.padding = '8px 12px';
    item.style.display = 'flex';
    item.style.alignItems = 'center';
    item.style.gap = '12px';

    const isChecked = pendingPlaylistSongIds.has(song.id);

    item.innerHTML = `
      <input type="checkbox" class="modal-song-check" data-song-id="${song.id}" ${isChecked ? 'checked' : ''} style="width:18px; height:18px;">
      <img src="${getCoverUrl(song)}" style="width:36px; height:36px; border-radius:6px; object-fit:cover;">
      <div style="flex:1; min-width:0;">
        <div style="font-weight:500; font-size:0.9rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(song.title)}</div>
        <div style="font-size:0.78rem; color:var(--text-secondary);">${escapeHtml(song.artist)} • ${escapeHtml(song.album)}</div>
      </div>
      <span style="font-size:0.8rem; color:var(--text-muted);">${formatTime(song.duration)}</span>
    `;

    const chk = item.querySelector('.modal-song-check');
    chk.addEventListener('change', () => {
      if (chk.checked) pendingPlaylistSongIds.add(song.id);
      else pendingPlaylistSongIds.delete(song.id);
      if (playlistAddSelectedCount) {
        playlistAddSelectedCount.textContent = `${pendingPlaylistSongIds.size} tracks selected`;
      }
    });

    playlistAddSongsList.appendChild(item);
  });
}

if (playlistSongSearchInput) {
  playlistSongSearchInput.addEventListener('input', () => {
    renderAddSongsModalList(modalAllSongsCache);
  });
}
if (playlistAddSongsModalClose) {
  playlistAddSongsModalClose.addEventListener('click', () => playlistAddSongsModal?.classList.add('hidden'));
}
if (playlistAddCancelBtn) {
  playlistAddCancelBtn.addEventListener('click', () => playlistAddSongsModal?.classList.add('hidden'));
}

async function removeSongFromCurrentPlaylist(songId) {
  if (!state.currentPlaylist) return;
  try {
    const res = await apiFetch(`/api/playlists/${state.currentPlaylist.id}/songs/${songId}`, {
      method: 'DELETE'
    });
    if (res.ok) {
      await openPlaylistDetail(state.currentPlaylist);
      await fetchPlaylists();
    }
  } catch (e) {
    console.error('Error removing song from playlist:', e);
  }
}

async function populateDownloaderPlaylists() {
  if (!dlPlaylistSelect) return;
  try {
    if (state.playlists.length === 0) {
      const res = await apiFetch('/api/playlists');
      const data = await res.json();
      state.playlists = data.playlists || [];
    }
    const currentVal = dlPlaylistSelect.value;
    dlPlaylistSelect.innerHTML = '<option value="">None (Library Only)</option>';
    state.playlists.forEach(pl => {
      const opt = document.createElement('option');
      opt.value = pl.id;
      opt.textContent = pl.name;
      if (pl.id === currentVal) opt.selected = true;
      dlPlaylistSelect.appendChild(opt);
    });
  } catch (e) {}
}

// Batch Selection & Batch ZIP Download
if (batchSelectBtn) {
  batchSelectBtn.addEventListener('click', () => {
    state.isBatchMode = !state.isBatchMode;
    if (!state.isBatchMode) {
      state.selectedSongIds.clear();
    }
    updateBatchUI();
    renderSongList(state.filteredSongs, songListEl);
  });
}

function updateBatchUI() {
  if (batchActionBar) {
    batchActionBar.classList.toggle('hidden', !state.isBatchMode);
  }
  if (batchSelectBtn) {
    batchSelectBtn.classList.toggle('active', state.isBatchMode);
    batchSelectBtn.textContent = state.isBatchMode ? '✕ Cancel' : '☑ Select';
  }
  if (batchCountLabel) {
    batchCountLabel.textContent = `${state.selectedSongIds.size} tracks selected`;
  }
}

if (batchCancelBtn) {
  batchCancelBtn.addEventListener('click', () => {
    state.isBatchMode = false;
    state.selectedSongIds.clear();
    updateBatchUI();
    renderSongList(state.filteredSongs, songListEl);
  });
}

if (batchDownloadZipBtn) {
  batchDownloadZipBtn.addEventListener('click', async () => {
    if (state.selectedSongIds.size === 0) {
      alert('Please select at least one song to download.');
      return;
    }
    await downloadSongsBatchZip(Array.from(state.selectedSongIds), 'selected_tracks.zip');
  });
}

if (batchAddPlaylistBtn) {
  batchAddPlaylistBtn.addEventListener('click', async () => {
    if (state.selectedSongIds.size === 0) {
      alert('Please select at least one song first.');
      return;
    }
    await openBatchAddToPlaylistPicker(Array.from(state.selectedSongIds));
  });
}

async function downloadSongsBatchZip(songIds, filename = 'tracks.zip') {
  if (!songIds || songIds.length === 0) return;
  try {
    serverBadge.textContent = 'Generating ZIP...';
    serverBadge.style.color = '#818cf8';

    const res = await apiFetch('/api/songs/download-zip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ song_ids: songIds, zip_name: filename })
    });
    if (!res.ok) {
      alert('Failed to generate ZIP archive.');
      fetchStatus();
      return;
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    fetchStatus();
  } catch (e) {
    console.error('Batch download error:', e);
    alert('Failed to download ZIP: ' + e);
    fetchStatus();
  }
}

async function openBatchAddToPlaylistPicker(songIds) {
  await fetchPlaylists();
  playlistModalBody.innerHTML = '';
  if (state.playlists.length === 0) {
    playlistModalBody.innerHTML = '<p style="color:var(--text-muted); padding:10px 0;">No playlists yet. Create one first!</p>';
  } else {
    state.playlists.forEach(pl => {
      const btn = document.createElement('button');
      btn.className = 'secondary-btn';
      btn.style.marginBottom = '8px';
      btn.style.width = '100%';
      btn.style.textAlign = 'left';
      btn.textContent = `${pl.name} (${pl.song_count || 0} tracks)`;
      btn.onclick = async () => {
        try {
          const res = await apiFetch(`/api/playlists/${pl.id}/songs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ song_ids: songIds })
          });
          if (res.ok) {
            playlistModal.classList.add('hidden');
            state.isBatchMode = false;
            state.selectedSongIds.clear();
            updateBatchUI();
            renderSongList(state.filteredSongs, songListEl);
            alert(`Added ${songIds.length} tracks to "${pl.name}"!`);
            fetchPlaylists();
          }
        } catch (e) {
          alert('Failed to add tracks: ' + e);
        }
      };
      playlistModalBody.appendChild(btn);
    });
  }
  playlistModal.classList.remove('hidden');
}

// Equalizer Modal Controls
const equalizerModal = document.getElementById('equalizer-modal');
const equalizerModalClose = document.getElementById('equalizer-modal-close');
const eqPowerToggle = document.getElementById('eq-power-toggle');

if (eqToggleBtn) {
  eqToggleBtn.addEventListener('click', () => {
    initAudioEngine();
    equalizerModal?.classList.remove('hidden');
  });
}
if (equalizerModalClose) {
  equalizerModalClose.addEventListener('click', () => equalizerModal?.classList.add('hidden'));
}
if (eqPowerToggle) {
  eqPowerToggle.addEventListener('change', () => {
    initAudioEngine();
    state.isEqualizerEnabled = eqPowerToggle.checked;
    applyEqGains(state.eqGains);
  });
}

[60, 250, 1000, 4000, 14000].forEach((freq, idx) => {
  const slider = document.getElementById(`eq-band-${freq}`);
  const label = document.getElementById(`eq-gain-${freq}`);
  if (slider) {
    slider.addEventListener('input', () => {
      initAudioEngine();
      const val = parseFloat(slider.value);
      state.eqGains[idx] = val;
      if (eqFilters[idx] && state.isEqualizerEnabled) eqFilters[idx].gain.value = val;
      if (label) label.textContent = `${val > 0 ? '+' : ''}${val}dB`;
      document.querySelectorAll('.eq-chip').forEach(c => c.classList.remove('active'));
    });
  }
});

document.querySelectorAll('.eq-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    initAudioEngine();
    const preset = chip.dataset.preset;
    if (EQ_PRESETS[preset]) {
      state.currentPreset = preset;
      document.querySelectorAll('.eq-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      applyEqGains(EQ_PRESETS[preset]);
    }
  });
});

// Sleep Timer Modal & Engine
const sleepTimerModal = document.getElementById('sleep-timer-modal');
const sleepTimerModalClose = document.getElementById('sleep-timer-modal-close');

if (sleepToggleBtn) {
  sleepToggleBtn.addEventListener('click', () => {
    sleepTimerModal?.classList.remove('hidden');
  });
}
if (sleepTimerModalClose) {
  sleepTimerModalClose.addEventListener('click', () => sleepTimerModal?.classList.add('hidden'));
}

function clearSleepTimer() {
  if (state.sleepTimerInterval) {
    clearInterval(state.sleepTimerInterval);
    state.sleepTimerInterval = null;
  }
  state.sleepTimerEnd = null;
  state.sleepAtTrackEnd = false;
  if (sleepBadge) {
    sleepBadge.textContent = '';
    sleepBadge.classList.add('hidden');
  }
}

function startSleepTimer(minutes) {
  clearSleepTimer();
  state.sleepTimerEnd = Date.now() + minutes * 60 * 1000;
  if (sleepBadge) {
    sleepBadge.textContent = `${minutes}m`;
    sleepBadge.classList.remove('hidden');
  }

  state.sleepTimerInterval = setInterval(() => {
    if (!state.sleepTimerEnd) return;
    const remainingMs = state.sleepTimerEnd - Date.now();
    if (remainingMs <= 0) {
      clearSleepTimer();
      fadeOutAndPause();
      return;
    }
    const remMins = Math.ceil(remainingMs / 60000);
    if (sleepBadge) sleepBadge.textContent = `${remMins}m`;
  }, 10000);
}

function fadeOutAndPause() {
  let vol = audio.volume;
  const originalVol = vol;
  const fade = setInterval(() => {
    if (vol > 0.05) {
      vol -= 0.05;
      audio.volume = vol;
    } else {
      clearInterval(fade);
      pauseAudio();
      audio.volume = originalVol;
    }
  }, 100);
}

document.querySelectorAll('.sleep-opt-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const val = btn.dataset.time;
    if (val === '0') {
      clearSleepTimer();
    } else if (val === 'end') {
      clearSleepTimer();
      state.sleepAtTrackEnd = true;
      if (sleepBadge) {
        sleepBadge.textContent = 'Track';
        sleepBadge.classList.remove('hidden');
      }
    } else {
      const mins = parseInt(val, 10);
      if (!isNaN(mins)) startSleepTimer(mins);
    }
    sleepTimerModal?.classList.add('hidden');
  });
});

// Playback Speed Toggle
const SPEED_STEPS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];
if (speedToggleBtn) {
  speedToggleBtn.addEventListener('click', () => {
    const currIdx = SPEED_STEPS.indexOf(state.playbackSpeed);
    const nextIdx = (currIdx + 1) % SPEED_STEPS.length;
    state.playbackSpeed = SPEED_STEPS[nextIdx];
    audio.playbackRate = state.playbackSpeed;
    speedToggleBtn.textContent = `${state.playbackSpeed}x`;
  });
}

// Volume & Mute Controls
let preMuteVolume = 1;

if (volumeMuteBtn) {
  volumeMuteBtn.addEventListener('click', () => {
    if (audio.muted || audio.volume === 0) {
      audio.muted = false;
      audio.volume = preMuteVolume > 0 ? preMuteVolume : 0.5;
      if (volumeSlider) volumeSlider.value = audio.volume;
      updateVolumeIcon(audio.volume);
    } else {
      preMuteVolume = audio.volume;
      audio.muted = true;
      audio.volume = 0;
      if (volumeSlider) volumeSlider.value = 0;
      updateVolumeIcon(0);
    }
  });
}

function updateVolumeIcon(vol) {
  if (!volumeIcon) return;
  if (vol === 0 || audio.muted) {
    volumeIcon.innerHTML = `
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
      <line x1="23" y1="9" x2="17" y2="15"></line>
      <line x1="17" y1="9" x2="23" y2="15"></line>
    `;
  } else if (vol < 0.5) {
    volumeIcon.innerHTML = `
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
    `;
  } else {
    volumeIcon.innerHTML = `
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
    `;
  }
}

if (volumeSlider) {
  volumeSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    audio.volume = val;
    audio.muted = (val === 0);
    if (val > 0) preMuteVolume = val;
    updateVolumeIcon(val);
  });
}

// Seek Slider Hover Tooltip
if (seekSlider && seekHoverTooltip) {
  seekSlider.addEventListener('mousemove', (e) => {
    if (!audio.duration) return;
    const rect = seekSlider.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const percent = x / rect.width;
    const previewTime = percent * audio.duration;
    seekHoverTooltip.textContent = formatTime(previewTime);
    seekHoverTooltip.style.left = `${x}px`;
    seekHoverTooltip.classList.remove('hidden');
  });

  seekSlider.addEventListener('mouseleave', () => {
    seekHoverTooltip.classList.add('hidden');
  });
}

// Music View Filter Dropdowns
if (filterGenreSelect) {
  filterGenreSelect.addEventListener('change', () => {
    state.selectedGenre = filterGenreSelect.value;
    fetchSongs(searchInput.value.trim(), sortSelect.value);
  });
}
if (filterLanguageSelect) {
  filterLanguageSelect.addEventListener('change', () => {
    state.selectedLanguage = filterLanguageSelect.value;
    fetchSongs(searchInput.value.trim(), sortSelect.value);
  });
}
if (filterYearSelect) {
  filterYearSelect.addEventListener('change', () => {
    state.selectedYear = filterYearSelect.value;
    fetchSongs(searchInput.value.trim(), sortSelect.value);
  });
}
if (clearMusicFiltersBtn) {
  clearMusicFiltersBtn.addEventListener('click', () => {
    state.selectedGenre = '';
    state.selectedLanguage = '';
    state.selectedYear = '';
    state.selectedDecade = '';
    if (filterGenreSelect) filterGenreSelect.value = '';
    if (filterLanguageSelect) filterLanguageSelect.value = '';
    if (filterYearSelect) filterYearSelect.value = '';
    clearMusicFiltersBtn.classList.add('hidden');
    smartComboBanner?.classList.add('hidden');
    document.querySelectorAll('#song-quick-ribbon .ribbon-chip').forEach(c => {
      c.classList.toggle('active', c.dataset.ribbon === 'all');
    });
    document.querySelectorAll('.sub-ribbon').forEach(sr => sr.classList.add('hidden'));
    fetchSongs(searchInput.value.trim(), sortSelect.value);
  });
}

// --- Quick Category Ribbon & Active Smart Combo Banner ---
function initQuickCategoryRibbon() {
  const chips = document.querySelectorAll('#song-quick-ribbon .ribbon-chip');
  if (!chips || chips.length === 0) return;

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const type = chip.dataset.ribbon;

      if (type === 'all') {
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.selectedGenre = '';
        state.selectedLanguage = '';
        state.selectedDecade = '';
        state.selectedYear = '';
        if (filterGenreSelect) filterGenreSelect.value = '';
        if (filterLanguageSelect) filterLanguageSelect.value = '';
        if (filterYearSelect) filterYearSelect.value = '';
        document.querySelectorAll('.sub-ribbon').forEach(sr => sr.classList.add('hidden'));
        fetchSongs(searchInput ? searchInput.value.trim() : '', sortSelect ? sortSelect.value : 'title');
      } else if (type === 'albums') {
        switchView('albums');
      } else if (type === 'artists') {
        switchView('artists');
      } else if (type === 'devotional') {
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.selectedGenre = 'Devotional';
        if (filterGenreSelect) filterGenreSelect.value = 'Devotional';
        document.querySelectorAll('.sub-ribbon').forEach(sr => sr.classList.add('hidden'));
        fetchSongs(searchInput ? searchInput.value.trim() : '', sortSelect ? sortSelect.value : 'title');
      } else if (type === 'languages-menu') {
        const isCurrentlyHidden = subRibbonLanguages?.classList.contains('hidden');
        document.querySelectorAll('.sub-ribbon').forEach(sr => sr.classList.add('hidden'));
        if (isCurrentlyHidden) {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          populateLanguagesSubRibbon();
          subRibbonLanguages?.classList.remove('hidden');
        } else {
          chip.classList.remove('active');
          const allChip = document.querySelector('#song-quick-ribbon [data-ribbon="all"]');
          if (allChip && !state.selectedGenre && !state.selectedLanguage && !state.selectedDecade) {
            allChip.classList.add('active');
          }
        }
      } else if (type === 'eras-menu') {
        const isCurrentlyHidden = subRibbonEras?.classList.contains('hidden');
        document.querySelectorAll('.sub-ribbon').forEach(sr => sr.classList.add('hidden'));
        if (isCurrentlyHidden) {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          populateErasSubRibbon();
          subRibbonEras?.classList.remove('hidden');
        } else {
          chip.classList.remove('active');
          const allChip = document.querySelector('#song-quick-ribbon [data-ribbon="all"]');
          if (allChip && !state.selectedGenre && !state.selectedLanguage && !state.selectedDecade) {
            allChip.classList.add('active');
          }
        }
      } else if (type === 'smart-mixes-menu') {
        const isCurrentlyHidden = subRibbonSmartMixes?.classList.contains('hidden');
        document.querySelectorAll('.sub-ribbon').forEach(sr => sr.classList.add('hidden'));
        if (isCurrentlyHidden) {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
          populateSmartSubRibbon();
          subRibbonSmartMixes?.classList.remove('hidden');
        } else {
          chip.classList.remove('active');
          const allChip = document.querySelector('#song-quick-ribbon [data-ribbon="all"]');
          if (allChip && !state.selectedGenre && !state.selectedLanguage && !state.selectedDecade) {
            allChip.classList.add('active');
          }
        }
      }
    });
  });
}

function populateLanguagesSubRibbon() {
  if (!subRibbonLanguages) return;
  subRibbonLanguages.innerHTML = '';
  if (!state.languages || state.languages.length === 0) {
    subRibbonLanguages.innerHTML = `<span style="font-size:0.78rem; color:var(--text-muted); padding:4px 8px;">No language tags found in songs yet.</span>`;
    return;
  }
  state.languages.forEach(l => {
    const btn = document.createElement('button');
    btn.className = `sub-chip ${state.selectedLanguage === l.language ? 'active' : ''}`;
    btn.textContent = `${l.language} (${l.count})`;
    btn.onclick = () => {
      if (state.selectedLanguage === l.language) {
        state.selectedLanguage = '';
        btn.classList.remove('active');
        if (filterLanguageSelect) filterLanguageSelect.value = '';
      } else {
        state.selectedLanguage = l.language;
        subRibbonLanguages.querySelectorAll('.sub-chip').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        if (filterLanguageSelect) filterLanguageSelect.value = l.language;
      }
      fetchSongs(searchInput ? searchInput.value.trim() : '', sortSelect ? sortSelect.value : 'title');
    };
    subRibbonLanguages.appendChild(btn);
  });
}

function populateErasSubRibbon() {
  if (!subRibbonEras) return;
  subRibbonEras.innerHTML = '';
  const ERAS = [
    { label: '2020s', value: '2020s' },
    { label: '2010s', value: '2010s' },
    { label: '2000s', value: '2000s' },
    { label: '1990s', value: '1990s' },
    { label: '1980s', value: '1980s' },
    { label: 'Classic (< 1980)', value: 'Classic' }
  ];
  ERAS.forEach(era => {
    const btn = document.createElement('button');
    btn.className = `sub-chip ${state.selectedDecade === era.value ? 'active' : ''}`;
    btn.textContent = era.label;
    btn.onclick = () => {
      if (state.selectedDecade === era.value) {
        state.selectedDecade = '';
        btn.classList.remove('active');
      } else {
        state.selectedDecade = era.value;
        subRibbonEras.querySelectorAll('.sub-chip').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
      }
      fetchSongs(searchInput ? searchInput.value.trim() : '', sortSelect ? sortSelect.value : 'title');
    };
    subRibbonEras.appendChild(btn);
  });
}

function populateSmartSubRibbon() {
  if (!subRibbonSmartMixes) return;
  subRibbonSmartMixes.innerHTML = '';
  if (!state.smartPlaylists || state.smartPlaylists.length === 0) {
    subRibbonSmartMixes.innerHTML = `<span style="font-size:0.78rem; color:var(--text-muted); padding:4px 8px;">No smart auto-mixes yet. Tag your library with Eras & Languages!</span>`;
    return;
  }
  state.smartPlaylists.slice(0, 10).forEach(sm => {
    const btn = document.createElement('button');
    btn.className = 'sub-chip';
    btn.innerHTML = `⚡ ${escapeHtml(sm.name)} <span style="opacity:0.7; font-size:0.75rem;">(${sm.song_count})</span>`;
    btn.onclick = () => openPlaylistDetail(sm);
    subRibbonSmartMixes.appendChild(btn);
  });
}

function updateSmartComboBanner() {
  if (!smartComboBanner) return;

  const genre = state.selectedGenre;
  const lang = state.selectedLanguage;
  const decade = state.selectedDecade;
  const year = state.selectedYear;

  const isComboActive = !!(decade || lang || genre || year);

  if (!isComboActive || !state.filteredSongs || state.filteredSongs.length === 0) {
    smartComboBanner.classList.add('hidden');
    return;
  }

  const eraStr = (decade && decade.endsWith('s')) ? decade : (decade ? decade.toUpperCase() : '');
  let title = '';
  if (decade && lang) {
    title = `${eraStr} ${lang.toUpperCase()}`;
  } else if (genre && lang) {
    title = `${genre.toUpperCase()} ${lang.toUpperCase()}`;
  } else if (genre && decade) {
    title = `${eraStr} ${genre.toUpperCase()}`;
  } else if (year && lang) {
    title = `${year} ${lang.toUpperCase()}`;
  } else if (genre) {
    title = `${genre.toUpperCase()} HITS`;
  } else if (lang) {
    title = `${lang.toUpperCase()} HITS`;
  } else if (decade) {
    title = `${eraStr} HITS`;
  } else if (year) {
    title = `${year} HITS`;
  } else {
    title = 'SMART AUTO-MIX';
  }

  const count = state.filteredSongs.length;
  const totalSec = state.filteredSongs.reduce((acc, s) => acc + (s.duration || 0), 0);
  const durStr = formatTime(totalSec);

  if (smartComboTitle) smartComboTitle.textContent = title;
  if (smartComboSubtitle) smartComboSubtitle.textContent = `${count} tracks • ${durStr}`;

  if (smartComboPlayBtn) {
    smartComboPlayBtn.onclick = () => playFromList(state.filteredSongs, 0);
  }
  if (smartComboShuffleBtn) {
    smartComboShuffleBtn.onclick = () => playShuffledList(state.filteredSongs);
  }
  if (smartComboSaveBtn) {
    smartComboSaveBtn.onclick = async () => {
      try {
        const name = prompt('Save this auto-mix as a permanent custom playlist:', title);
        if (!name) return;
        const res = await apiFetch('/api/playlists', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            description: `Smart mix for ${title}`,
            is_smart: true,
            criteria: {
              decade: decade || undefined,
              language: lang || undefined,
              genre: genre || undefined,
              year: year ? parseInt(year, 10) : undefined
            },
            song_ids: state.filteredSongs.map(s => s.id)
          })
        });
        if (res.ok) {
          alert(`Saved custom playlist "${name}"!`);
          await fetchPlaylists();
        } else {
          const err = await res.json();
          alert(err.detail || 'Failed to save playlist');
        }
      } catch (e) {
        alert('Error saving playlist: ' + e);
      }
    };
  }
  if (smartComboCloseBtn) {
    smartComboCloseBtn.onclick = () => {
      state.selectedGenre = '';
      state.selectedLanguage = '';
      state.selectedDecade = '';
      state.selectedYear = '';
      if (filterGenreSelect) filterGenreSelect.value = '';
      if (filterLanguageSelect) filterLanguageSelect.value = '';
      if (filterYearSelect) filterYearSelect.value = '';
      smartComboBanner.classList.add('hidden');
      document.querySelectorAll('#song-quick-ribbon .ribbon-chip').forEach(c => {
        c.classList.toggle('active', c.dataset.ribbon === 'all');
      });
      document.querySelectorAll('.sub-ribbon').forEach(sr => sr.classList.add('hidden'));
      fetchSongs(searchInput ? searchInput.value.trim() : '', sortSelect ? sortSelect.value : 'title');
    };
  }

  smartComboBanner.classList.remove('hidden');
}

// Edit Metadata Modal Logic (Jellyfin-Style Fast Organizer with Language)
const editMetadataModal = document.getElementById('edit-metadata-modal');
const editMetadataClose = document.getElementById('edit-metadata-modal-close');
const editMetaCancelBtn = document.getElementById('edit-meta-cancel-btn');
const editMetaSaveBtn = document.getElementById('edit-meta-save-btn');

if (editMetadataClose) {
  editMetadataClose.addEventListener('click', () => editMetadataModal.classList.add('hidden'));
}
if (editMetaCancelBtn) {
  editMetaCancelBtn.addEventListener('click', () => editMetadataModal.classList.add('hidden'));
}
if (editMetaSaveBtn) {
  editMetaSaveBtn.addEventListener('click', saveMetadataEdits);
}

function openEditMetadataModal(item) {
  if (!item || !editMetadataModal) return;
  document.getElementById('edit-meta-id').value = item.id;
  document.getElementById('edit-meta-title').value = item.title || '';
  document.getElementById('edit-meta-artist').value = item.artist || '';
  document.getElementById('edit-meta-album').value = item.album || '';
  document.getElementById('edit-meta-year').value = item.year || '';
  document.getElementById('edit-meta-genre').value = item.genre || '';

  const langInput = document.getElementById('edit-meta-language');
  if (langInput) langInput.value = item.language || '';

  const isTv = item.media_type === 'video' && (item.genre === 'TV Show' || item.season != null);
  const tvGroup = document.getElementById('edit-meta-tv-group');
  if (tvGroup) {
    tvGroup.style.display = isTv ? 'flex' : 'none';
    document.getElementById('edit-meta-season').value = item.season || '';
    document.getElementById('edit-meta-episode').value = item.episode || '';
  }

  const artistLabel = document.getElementById('edit-meta-artist-label');
  if (artistLabel) artistLabel.textContent = item.media_type === 'video' ? 'Series / Creator' : 'Artist Name';

  const albumLabel = document.getElementById('edit-meta-album-label');
  if (albumLabel) albumLabel.textContent = item.media_type === 'video' ? 'Collection / Show' : 'Album Name';

  const heading = document.getElementById('edit-meta-heading');
  if (heading) heading.textContent = item.media_type === 'video' ? 'Edit Video Details' : 'Edit Track Details';

  editMetadataModal.classList.remove('hidden');
}

async function saveMetadataEdits() {
  const id = document.getElementById('edit-meta-id').value;
  if (!id) return;

  const title = document.getElementById('edit-meta-title').value.trim();
  const artist = document.getElementById('edit-meta-artist').value.trim();
  const album = document.getElementById('edit-meta-album').value.trim();
  const yearVal = document.getElementById('edit-meta-year').value.trim();
  const genre = document.getElementById('edit-meta-genre').value.trim();
  const language = document.getElementById('edit-meta-language')?.value.trim();
  const seasonVal = document.getElementById('edit-meta-season')?.value.trim();
  const episodeVal = document.getElementById('edit-meta-episode')?.value.trim();

  const payload = {
    title: title || undefined,
    artist: artist || undefined,
    album: album || undefined,
    genre: genre || undefined,
    language: language || undefined,
    year: yearVal ? parseInt(yearVal, 10) : null,
    season: seasonVal ? parseInt(seasonVal, 10) : null,
    episode: episodeVal ? parseInt(episodeVal, 10) : null,
  };

  try {
    const res = await apiFetch(`/api/media/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || 'Failed to update metadata');
      return;
    }
    editMetadataModal.classList.add('hidden');
    if (state.currentView === 'videos') {
      fetchVideos(searchInput.value.trim());
    } else {
      fetchSongs(searchInput.value.trim(), sortSelect.value);
    }
    fetchMyMedia();
  } catch (err) {
    console.error('Error saving metadata:', err);
    alert('Failed to save metadata');
  }
}

// Video Category Pills & Filters
const videoCatPills = document.querySelectorAll('#video-cat-pills .filter-pill');
videoCatPills.forEach(pill => {
  pill.addEventListener('click', () => {
    videoCatPills.forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    state.videoCategory = pill.dataset.cat || 'all';
    fetchVideos(searchInput.value.trim());
  });
});

const videoDecadeFilter = document.getElementById('video-decade-filter');
if (videoDecadeFilter) {
  videoDecadeFilter.addEventListener('change', (e) => {
    state.videoDecade = e.target.value;
    fetchVideos(searchInput.value.trim());
  });
}

const videoResFilter = document.getElementById('video-res-filter');
if (videoResFilter) {
  videoResFilter.addEventListener('change', (e) => {
    state.videoResolution = e.target.value;
    fetchVideos(searchInput.value.trim());
  });
}

const videoSortSelect = document.getElementById('video-sort-select');
if (videoSortSelect) {
  videoSortSelect.addEventListener('change', (e) => {
    state.videoSort = e.target.value;
    fetchVideos(searchInput.value.trim());
  });
}

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
    // Leave format and destination selection to the person sharing the link.
    dlUrlInput.focus();
  } else if (sharedFiles) {
    window.history.replaceState({}, document.title, '/');
    alert(`Successfully shared ${sharedFiles} file(s) with everyone on Wi-Fi!`);
    fetchVideos();
    fetchSongs();
    fetchFavorites();
    switchView('videos');
  }
}

// QR Code Connect Modal Handlers (Dual-Mode: Local Mesh + Worldwide Global)
const qrModal = document.getElementById('qr-modal');
const qrModalBtn = document.getElementById('qr-modal-btn');
const qrModalClose = document.getElementById('qr-modal-close');
const qrCodeImg = document.getElementById('qr-code-img');
const qrConnectUrl = document.getElementById('qr-connect-url');
const qrIpSelect = document.getElementById('qr-ip-select');
const copyQrUrlBtn = document.getElementById('copy-qr-url-btn');
const shareLinkBtn = document.getElementById('share-link-btn');

// Dual-Mode Connect Tab Elements
const connectTabMesh = document.getElementById('connect-tab-mesh');
const connectTabTailscale = document.getElementById('connect-tab-tailscale');
const connectTabGlobal = document.getElementById('connect-tab-global');
const meshConnectContent = document.getElementById('mesh-connect-content');
const tailscaleConnectContent = document.getElementById('tailscale-connect-content');
const globalConnectContent = document.getElementById('global-connect-content');
const tailscaleQrCodeImg = document.getElementById('tailscale-qr-code-img');
const tailscaleConnectUrlDisplay = document.getElementById('tailscale-connect-url-display');
const copyTailscaleQrUrlBtn = document.getElementById('copy-tailscale-qr-url-btn');
const shareTailscaleLinkBtn = document.getElementById('share-tailscale-link-btn');
const globalActivePanel = document.getElementById('global-active-panel');
const globalStartingPanel = document.getElementById('global-starting-panel');
const globalInactivePanel = document.getElementById('global-inactive-panel');
const globalQrCodeImg = document.getElementById('global-qr-code-img');
const globalConnectUrlDisplay = document.getElementById('global-connect-url-display');
const copyGlobalQrUrlBtn = document.getElementById('copy-global-qr-url-btn');
const shareGlobalLinkBtn = document.getElementById('share-global-link-btn');
const startGlobalNowBtn = document.getElementById('start-global-now-btn');

function switchConnectTab(tabName) {
  // Reset all tabs
  [connectTabMesh, connectTabTailscale, connectTabGlobal].forEach(tab => {
    if (tab) {
      tab.style.color = 'var(--text-secondary)';
      tab.style.borderBottomColor = 'transparent';
      tab.style.fontWeight = '500';
    }
  });
  if (meshConnectContent) meshConnectContent.style.display = 'none';
  if (tailscaleConnectContent) tailscaleConnectContent.style.display = 'none';
  if (globalConnectContent) globalConnectContent.style.display = 'none';

  if (tabName === 'global') {
    if (connectTabGlobal) {
      connectTabGlobal.style.color = '#34d399';
      connectTabGlobal.style.borderBottomColor = '#34d399';
      connectTabGlobal.style.fontWeight = '600';
    }
    if (globalConnectContent) globalConnectContent.style.display = 'block';
    updateGlobalModalPanel();
  } else if (tabName === 'tailscale') {
    if (connectTabTailscale) {
      connectTabTailscale.style.color = '#818cf8';
      connectTabTailscale.style.borderBottomColor = '#818cf8';
      connectTabTailscale.style.fontWeight = '600';
    }
    if (tailscaleConnectContent) tailscaleConnectContent.style.display = 'block';
    if (state.tailscaleUrl) {
      if (tailscaleConnectUrlDisplay) tailscaleConnectUrlDisplay.textContent = state.tailscaleUrl;
      if (tailscaleQrCodeImg) tailscaleQrCodeImg.src = `/api/qr?url=${encodeURIComponent(state.tailscaleUrl)}`;
    }
  } else {
    if (connectTabMesh) {
      connectTabMesh.style.color = 'var(--text-primary)';
      connectTabMesh.style.borderBottomColor = 'var(--accent)';
      connectTabMesh.style.fontWeight = '600';
    }
    if (meshConnectContent) meshConnectContent.style.display = 'block';
  }
}

function updateGlobalModalPanel() {
  if (!globalActivePanel || !globalStartingPanel || !globalInactivePanel) return;

  if (state.globalActive && state.globalUrl) {
    globalActivePanel.style.display = 'block';
    globalStartingPanel.style.display = 'none';
    globalInactivePanel.style.display = 'none';
    if (globalConnectUrlDisplay) globalConnectUrlDisplay.textContent = state.globalUrl;
    if (globalQrCodeImg) globalQrCodeImg.src = `/api/qr?url=${encodeURIComponent(state.globalUrl)}`;
  } else if (state.globalStatus === 'starting') {
    globalActivePanel.style.display = 'none';
    globalStartingPanel.style.display = 'block';
    globalInactivePanel.style.display = 'none';
  } else {
    globalActivePanel.style.display = 'none';
    globalStartingPanel.style.display = 'none';
    globalInactivePanel.style.display = 'block';
  }
}

if (connectTabMesh) connectTabMesh.addEventListener('click', () => switchConnectTab('mesh'));
if (connectTabTailscale) connectTabTailscale.addEventListener('click', () => switchConnectTab('tailscale'));
if (connectTabGlobal) connectTabGlobal.addEventListener('click', () => switchConnectTab('global'));

if (copyTailscaleQrUrlBtn) {
  copyTailscaleQrUrlBtn.addEventListener('click', async () => {
    if (state.tailscaleUrl) {
      try {
        await navigator.clipboard.writeText(state.tailscaleUrl);
        copyTailscaleQrUrlBtn.textContent = 'Copied!';
        setTimeout(() => { copyTailscaleQrUrlBtn.textContent = 'Copy'; }, 2000);
      } catch (e) {
        alert(`Tailscale URL: ${state.tailscaleUrl}`);
      }
    }
  });
}

if (shareTailscaleLinkBtn) {
  shareTailscaleLinkBtn.addEventListener('click', async () => {
    const url = state.tailscaleUrl;
    if (!url) return;
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Decentralized Media Hub (Tailscale Access)',
          text: 'Connect to MediaHub anywhere in the world over Tailscale VPN:',
          url: url
        });
      } catch (e) {}
    } else {
      await navigator.clipboard.writeText(url);
      alert('Tailscale link copied! Paste on any device with Tailscale.');
    }
  });
}

if (startGlobalNowBtn) {
  startGlobalNowBtn.addEventListener('click', async () => {
    startGlobalNowBtn.disabled = true;
    startGlobalNowBtn.innerHTML = '<span>Starting Global Tunnel...</span>';
    state.globalStatus = 'starting';
    updateGlobalModalPanel();
    updateNetworkModeUI();

    try {
      await apiFetch('/api/tunnel/start', { method: 'POST' });
      // Poll until tunnel URL is captured
      let tries = 0;
      const pollTimer = setInterval(async () => {
        tries++;
        await fetchStatus();
        if (state.globalActive && state.globalUrl) {
          clearInterval(pollTimer);
          startGlobalNowBtn.disabled = false;
          startGlobalNowBtn.innerHTML = '<span>🚀 Start Worldwide Access (Global Mode)</span>';
          updateGlobalModalPanel();
        } else if (tries > 20) {
          clearInterval(pollTimer);
          startGlobalNowBtn.disabled = false;
          startGlobalNowBtn.innerHTML = '<span>🚀 Start Worldwide Access (Global Mode)</span>';
        }
      }, 1000);
    } catch (e) {
      alert(`Could not start tunnel: ${e}`);
      startGlobalNowBtn.disabled = false;
      startGlobalNowBtn.innerHTML = '<span>🚀 Start Worldwide Access (Global Mode)</span>';
    }
  });
}

if (copyGlobalQrUrlBtn) {
  copyGlobalQrUrlBtn.addEventListener('click', async () => {
    if (state.globalUrl) {
      try {
        await navigator.clipboard.writeText(state.globalUrl);
        copyGlobalQrUrlBtn.textContent = 'Copied!';
        setTimeout(() => { copyGlobalQrUrlBtn.textContent = 'Copy'; }, 2000);
      } catch (e) {
        alert(`Worldwide URL: ${state.globalUrl}`);
      }
    }
  });
}

if (shareGlobalLinkBtn) {
  shareGlobalLinkBtn.addEventListener('click', async () => {
    const url = state.globalUrl;
    if (!url) return;
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Decentralized Media Hub (Worldwide Access)',
          text: 'Connect to MediaHub from mobile cellular data (4G/5G) anywhere in the world:',
          url: url
        });
      } catch (e) {}
    } else {
      await navigator.clipboard.writeText(url);
      alert('Worldwide link copied! Paste in WhatsApp/iMessage to open on phone.');
    }
  });
}

async function openQrModal(defaultTab = 'mesh') {
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
      state.globalActive = Boolean(data.global_active);
      state.globalStatus = data.global_status || 'stopped';
      state.globalUrl = data.global_url || null;
      state.globalEnabled = Boolean(data.global_enabled);
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

  if (connectTabTailscale) {
    connectTabTailscale.style.display = state.tailscaleUrl ? 'block' : 'none';
  }

  switchConnectTab(defaultTab);
  qrModal.classList.remove('hidden');
}

if (qrModalBtn) qrModalBtn.addEventListener('click', () => openQrModal('mesh'));
if (qrModalClose) qrModalClose.addEventListener('click', () => qrModal.classList.add('hidden'));

const networkModePill = document.getElementById('network-mode-pill');
if (networkModePill) networkModePill.addEventListener('click', () => openQrModal(state.globalActive ? 'global' : 'mesh'));

const openGlobalQrSettingsBtn = document.getElementById('open-global-qr-settings-btn');
if (openGlobalQrSettingsBtn) openGlobalQrSettingsBtn.addEventListener('click', () => openQrModal('global'));

const copyGlobalSettingsUrlBtn = document.getElementById('copy-global-settings-url-btn');
if (copyGlobalSettingsUrlBtn) {
  copyGlobalSettingsUrlBtn.addEventListener('click', async () => {
    if (state.globalUrl) {
      try {
        await navigator.clipboard.writeText(state.globalUrl);
        copyGlobalSettingsUrlBtn.textContent = 'Copied!';
        setTimeout(() => { copyGlobalSettingsUrlBtn.textContent = 'Copy'; }, 2000);
      } catch (e) {
        alert(state.globalUrl);
      }
    }
  });
}

const globalAccessToggle = document.getElementById('global-access-toggle');
if (globalAccessToggle) {
  globalAccessToggle.addEventListener('change', async (e) => {
    const isChecked = e.target.checked;
    state.globalStatus = isChecked ? 'starting' : 'stopped';
    updateNetworkModeUI();
    try {
      const endpoint = isChecked ? '/api/tunnel/start' : '/api/tunnel/stop';
      await apiFetch(endpoint, { method: 'POST' });
      // Poll for tunnel state updates
      let tries = 0;
      const pollTimer = setInterval(async () => {
        tries++;
        await fetchStatus();
        if (state.globalActive && state.globalUrl) {
          clearInterval(pollTimer);
        } else if (!isChecked || tries > 20) {
          clearInterval(pollTimer);
        }
      }, 1000);
    } catch (err) {
      console.error('Error toggling worldwide access:', err);
    }
  });
}

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

// Scope Switcher Tabs & Peer Device Dropdown
async function fetchPeersForScope() {
  try {
    const res = await apiFetch('/api/peers/connected');
    const data = await res.json();
    const peers = data.peers || [];
    document.querySelectorAll('.peer-scope-dropdown').forEach(select => {
      const currentVal = select.value;
      select.innerHTML = `
        <option value="">👥 Peers (Select Device)</option>
        <option value="peers">👥 All Connected Peers</option>
      `;
      peers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = `peer:${p.id}`;
        opt.textContent = `${p.active ? '🟢' : '⚪'} ${escapeHtml(p.name)}`;
        select.appendChild(opt);
      });
      if (currentVal) select.value = currentVal;
    });
  } catch (e) {
    console.error('Error fetching peers for scope:', e);
  }
}

document.querySelectorAll('.scope-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const bar = tab.closest('.scope-bar');
    if (bar) {
      bar.querySelectorAll('.scope-tab').forEach(t => t.classList.remove('active'));
      const peerSelect = bar.querySelector('.peer-scope-dropdown');
      if (peerSelect) {
        peerSelect.value = '';
        peerSelect.classList.remove('active');
      }
    }
    tab.classList.add('active');
    state.mediaScope = tab.dataset.scope;
    const target = bar ? bar.dataset.target : 'songs';
    if (target === 'songs') {
      fetchSongs(searchInput.value.trim(), sortSelect.value, state.mediaScope);
    } else if (target === 'videos') {
      fetchVideos(searchInput.value.trim(), state.mediaScope);
    } else if (target === 'photos') {
      fetchPhotos(photosAlbumFilter ? photosAlbumFilter.value : '', state.mediaScope);
    }
  });
});

document.querySelectorAll('.peer-scope-dropdown').forEach(select => {
  select.addEventListener('change', () => {
    const bar = select.closest('.scope-bar');
    const val = select.value;
    const target = bar ? bar.dataset.target : (select.dataset.target || 'songs');

    if (bar) {
      bar.querySelectorAll('.scope-tab').forEach(t => t.classList.remove('active'));
    }

    if (!val) {
      if (bar) {
        const allBtn = bar.querySelector('.scope-tab[data-scope="all"]');
        if (allBtn) allBtn.classList.add('active');
      }
      select.classList.remove('active');
      state.mediaScope = 'all';
    } else {
      select.classList.add('active');
      state.mediaScope = val;
    }

    if (target === 'songs') {
      fetchSongs(searchInput.value.trim(), sortSelect.value, state.mediaScope);
    } else if (target === 'videos') {
      fetchVideos(searchInput.value.trim(), state.mediaScope);
    } else if (target === 'photos') {
      fetchPhotos(photosAlbumFilter ? photosAlbumFilter.value : '', state.mediaScope);
    }
  });
});

// Photos & Lightbox Event Listeners
if (photosAlbumFilter) {
  photosAlbumFilter.addEventListener('change', () => {
    fetchPhotos(photosAlbumFilter.value, state.mediaScope);
  });
}

if (uploadPhotosBtn) {
  uploadPhotosBtn.addEventListener('click', () => {
    if (photoUploadInput) photoUploadInput.click();
  });
}

if (photoUploadInput) {
  photoUploadInput.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    serverBadge.textContent = `Uploading ${files.length} photos...`;
    serverBadge.style.color = '#f59e0b';

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    formData.append('client_id', clientId);
    formData.append('device_name', getDeviceType());

    try {
      const res = await apiFetch('/api/upload/photos', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      alert(data.message || 'Photos uploaded!');
      fetchPhotos();
      fetchStatus();
    } catch (err) {
      alert(`Error uploading photos: ${err}`);
    } finally {
      photoUploadInput.value = '';
    }
  });
}

if (lightboxCloseBtn) lightboxCloseBtn.addEventListener('click', closePhotoLightbox);
if (lightboxPrevBtn) lightboxPrevBtn.addEventListener('click', prevPhoto);
if (lightboxNextBtn) lightboxNextBtn.addEventListener('click', nextPhoto);

if (lightboxDeleteBtn) {
  lightboxDeleteBtn.addEventListener('click', async () => {
    if (activePhotoIndex < 0 || !state.photos[activePhotoIndex]) return;
    const photo = state.photos[activePhotoIndex];
    if (confirm(`Delete photo "${photo.title}"?`)) {
      try {
        const res = await apiFetch(`/api/photo/${photo.id}`, { method: 'DELETE' });
        if (res.ok) {
          closePhotoLightbox();
          fetchPhotos();
          fetchStatus();
        } else {
          const err = await res.json();
          alert(err.detail || 'Could not delete photo');
        }
      } catch (e) {
        alert(`Error: ${e}`);
      }
    }
  });
}

// 24-Hour Status & Story Viewer Event Listeners
if (postStatusBtn) postStatusBtn.addEventListener('click', openPostStatusModal);
if (closePostStatusModalBtn) closePostStatusModalBtn.addEventListener('click', closePostStatusModal);
if (cancelPostStatusBtn) cancelPostStatusBtn.addEventListener('click', closePostStatusModal);

if (statusUploadDropzone) {
  statusUploadDropzone.addEventListener('click', () => {
    if (statusFileInput) statusFileInput.click();
  });
}

if (statusFileInput) {
  statusFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleStatusFileSelect(e.target.files[0]);
    }
  });
}

if (submitPostStatusBtn) submitPostStatusBtn.addEventListener('click', submitStatusPost);

if (storyCloseBtn) storyCloseBtn.addEventListener('click', closeStoryViewer);
if (storyViewerBackdrop) storyViewerBackdrop.addEventListener('click', closeStoryViewer);
if (storyPrevBtn) storyPrevBtn.addEventListener('click', prevStoryItem);
if (storyNextBtn) storyNextBtn.addEventListener('click', nextStoryItem);
if (storyTouchLeft) storyTouchLeft.addEventListener('click', prevStoryItem);
if (storyTouchRight) storyTouchRight.addEventListener('click', nextStoryItem);

document.addEventListener('keydown', (e) => {
  if (photoLightboxModal && !photoLightboxModal.classList.contains('hidden')) {
    if (e.key === 'Escape') closePhotoLightbox();
    if (e.key === 'ArrowLeft') prevPhoto();
    if (e.key === 'ArrowRight') nextPhoto();
    return;
  }
  if (storyViewerModal && !storyViewerModal.classList.contains('hidden')) {
    if (e.key === 'Escape') closeStoryViewer();
    if (e.key === 'ArrowLeft') prevStoryItem();
    if (e.key === 'ArrowRight') nextStoryItem();
    return;
  }

  // If typing in an input or textarea, don't trigger media shortcuts
  const activeTag = document.activeElement ? document.activeElement.tagName : '';
  if (activeTag === 'INPUT' || activeTag === 'TEXTAREA' || activeTag === 'SELECT') {
    return;
  }

  if (e.key === ' ') {
    e.preventDefault();
    togglePlay();
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault();
    if (audio.duration) audio.currentTime = Math.max(0, audio.currentTime - 5);
  } else if (e.key === 'ArrowRight') {
    e.preventDefault();
    if (audio.duration) audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    const newVol = Math.min(1, (audio.volume || 0) + 0.05);
    audio.volume = newVol;
    if (volumeSlider) volumeSlider.value = newVol;
    updateVolumeIcon(newVol);
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    const newVol = Math.max(0, (audio.volume || 0) - 0.05);
    audio.volume = newVol;
    if (volumeSlider) volumeSlider.value = newVol;
    updateVolumeIcon(newVol);
  } else if ((e.key === 'N' || e.key === 'n') && e.shiftKey) {
    e.preventDefault();
    nextTrack();
  } else if ((e.key === 'P' || e.key === 'p') && e.shiftKey) {
    e.preventDefault();
    prevTrack();
  } else if (e.key === 'm' || e.key === 'M') {
    if (volumeMuteBtn) volumeMuteBtn.click();
  } else if (e.key === 'l' || e.key === 'L') {
    if (fullLoveBtn && !fullLoveBtn.closest('.hidden')) fullLoveBtn.click();
    else if (miniLoveBtn) miniLoveBtn.click();
  } else if (e.key === 'Escape') {
    if (fullPlayer && fullPlayer.classList.contains('active')) {
      fullPlayer.classList.remove('active');
    }
  }
});

// Initial Load & Mobile-First Routing
const isMobileDevice = /android|iphone|ipad|ipod/i.test(navigator.userAgent) || window.innerWidth <= 768;
const startingView = isMobileDevice ? 'my-device' : 'songs';

initQuickCategoryRibbon();
fetchLanguages();
fetchGenres();
fetchPlaylists();

fetchStatus();
if (startingView === 'my-device') {
  fetchMyMedia();
  switchView('my-device');
} else {
  fetchSongs();
  switchView('songs');
}
fetchFavorites();
fetchActiveStatuses();
checkIncomingShares();

// --- Live Peer Sharing (Ephemeral P2P Broadcast with Zero Server Clutter) ---
const peerShareInput = document.getElementById('peer-share-input');
const peerShareMusicBtn = document.getElementById('peer-share-music-btn');
const peerShareVideoBtn = document.getElementById('peer-share-video-btn');
const peerSharePhotoBtn = document.getElementById('peer-share-photo-btn');

if (peerShareMusicBtn) peerShareMusicBtn.addEventListener('click', () => peerShareInput && peerShareInput.click());
if (peerShareVideoBtn) peerShareVideoBtn.addEventListener('click', () => peerShareInput && peerShareInput.click());
if (peerSharePhotoBtn) peerSharePhotoBtn.addEventListener('click', () => peerShareInput && peerShareInput.click());

if (peerShareInput) {
  peerShareInput.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    for (const file of files) {
      await uploadLivePeerShare(file);
    }
    peerShareInput.value = '';
    fetchStatus();
    fetchSongs();
    fetchVideos();
    fetchPhotos();
    fetchPeersForScope();
  });
}

async function uploadLivePeerShare(file, btnEl = null) {
  if (!file) return;
  const originalText = btnEl ? btnEl.innerHTML : '';
  if (btnEl) {
    btnEl.innerHTML = '<span>Broadcasting...</span>';
    btnEl.style.opacity = '0.7';
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('client_id', clientId);
  formData.append('device_name', getDeviceType());

  try {
    serverBadge.textContent = `Broadcasting ${file.name}...`;
    serverBadge.style.color = '#6366f1';

    const res = await apiFetch('/api/peers/share', {
      method: 'POST',
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      if (btnEl) {
        btnEl.innerHTML = '<span>✓ Live Shared</span>';
        btnEl.style.background = 'rgba(99, 102, 241, 0.2)';
        btnEl.style.color = '#818cf8';
      } else {
        alert(data.message || `Broadcasting '${file.name}' live to all connected peers!`);
      }
      fetchStatus();
      fetchSongs();
      fetchVideos();
      fetchPhotos();
      fetchPeersForScope();
    } else {
      alert(`Failed to broadcast ${file.name}`);
      if (btnEl) btnEl.innerHTML = originalText;
    }
  } catch (err) {
    alert(`Live share error: ${err}`);
    if (btnEl) btnEl.innerHTML = originalText;
  }
}

async function copyLiveShareToServer(shareId, btnEl = null) {
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Saving to Server...';
  }
  try {
    const res = await apiFetch(`/api/peers/shares/${shareId}/copy-to-server`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      alert(data.message || 'Saved permanently to server hard drive for CasaOS!');
      fetchVideos();
      fetchSongs();
      fetchPhotos();
      fetchStatus();
    } else {
      alert(`Error saving to server: ${data.detail || data.message}`);
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.textContent = '📥 Copy to Server';
      }
    }
  } catch (err) {
    alert(`Request error: ${err}`);
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = '📥 Copy to Server';
    }
  }
}
