# Decentralized Media Hub

An open-source, peer-to-peer **Offline Media Streaming & Sharing Hub** built with **FastAPI** and a modern **Progressive Web App (PWA)** mobile player.

Stream your downloaded **Music, Movies, and Videos** across laptops, Android phones, and iPhones in **Multi-Mode**:
* **🏠 Local Wi-Fi Mesh**: 100% offline, **0 MB internet data used**, blazing fast 300–800 Mbps transfer.
* **🔒 Tailscale Private Mesh**: Direct WireGuard P2P stream from anywhere in the world with zero port-forwarding and complete privacy.
* **🌍 Worldwide Global Access**: Stream over **mobile cellular data (4G/5G)** via secure Cloudflare Tunnel (HTTPS) with zero router configuration.

---

## 🌟 Key Features

### 1. 🔄 Dual-Mode (Mesh Network + Worldwide Global Access)
* **Local Mesh Mode**: Automatic zero-config peer discovery via **mDNS / Zeroconf** across devices on the same Wi-Fi or mobile hotspot with 0 MB internet bandwidth.
* **Global Worldwide Mode**: Instant, end-to-end encrypted HTTPS remote access via background Cloudflare Tunnel. When you step outside your home Wi-Fi network, your phone stays connected over 4G/5G from anywhere on Earth.
* **Simultaneous Operation**: Both modes run concurrently! Connect over fast local Wi-Fi when at home, and switch to the secure global HTTPS link when on the move.
* **In-App Control**: Toggle worldwide access on/off directly from the Web App settings, or auto-start on boot.

### 2. 📱 Connect Phone via QR Code (Mesh & Global)
* Click **"Connect Phone"** or the network badge to switch between:
  * **Local Mesh QR**: Fast offline connection for devices on the same Wi-Fi.
  * **Worldwide QR**: Secure HTTPS link for mobile access on 4G/5G.
* Tap **"Add to Home Screen"** in Safari / Chrome to install as a full standalone app with background lock screen audio controls.

### 3. 🔒 Privacy by Design & Explicit Folder Sharing
* **Opt-in Sharing**: Only folders you explicitly choose are indexed and visible to others.
* **Stealth / Incognito Mode**: Turn off "Share My Library" at any time. You can still stream media from other devices on Wi-Fi, but your own files remain 100% private and invisible.

### 4. 📥 Universal Downloader (Server vs Local Destination)
* Paste links from **YouTube, Spotify, SoundCloud, Vimeo**, and 1,000+ platforms supported by `yt-dlp`.
* Download as **Audio (MP3/M4A)** or **Full Video (1080p/720p MP4)** with embedded artwork & metadata.
* **Destination Selector**:
  * **Server Folder**: Saves directly into the host library so all network peers can stream it.
  * **My Device (Local)**: Server processes the stream and immediately pushes the file to your mobile phone or laptop browser downloads folder.
* **Offline / Camping / Ship Flow**: If the server PC is offline and a mobile user has cellular data, they can download locally on their phone and use the 1-tap "Share to Mesh" button to push it to the server over local Wi-Fi.

### 5. 🛡️ Server Storage Governance & Host Approval Queue
* **Configurable Policy**: Host admin can choose between **"Auto-Accept All Uploads"** (trusted home network) or **"Review & Approve Queue"** (shared/public networks).
* **Pending Approvals Queue**: When review mode is active, peer uploads enter a staging queue with file previews and 1-click **Accept** or **Reject** controls.

### 6. 📷 High-Performance Photo Gallery & Mesh Sharing
* Fast indexing and thumbnail generation for `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, and `.gif`.
* **Timeline View**: Automatically organizes photos chronologically by Year & Month (similar to Apple Photos & Immich).
* **Mesh Badges**: Displays the source device sharing each photo.
* **Fullscreen Lightbox**: Includes swipe navigation, photo metadata (dimensions, camera model, date taken), direct download, and 1-click VLC links.
* **Multi-Photo Mobile Upload**: Select multiple photos from camera roll or files to share across the mesh.

### 7. 📺 External Player Integration (VLC, Smart TVs, Plex, Immich & DLNA)
* **Zero-Config UPnP / DLNA Discovery**: MediaPlayer responds to SSDP multicast on UDP port 1900. Smart TVs, VLC (*Local Network ➔ Universal Plug'n'Play*), and Kodi discover the server automatically with zero manual configuration.
* **1-Click VLC Streaming**: Every song, movie, and photo card features a 1-click `vlc://` link.
* **Dynamic M3U Playlists**: Full IPTV/VLC playlist endpoints for all media (`/api/playlist.m3u`), movies (`/api/playlist/movies.m3u`), and music (`/api/playlist/music.m3u`).

### 5. 🎬 Offline Movie & Video Streaming
* Stream `.mp4`, `.mkv`, `.webm`, `.mov` files with **HTTP 206 Byte-Range Seeking**.
* Instant scrubbing without buffering.
* Integrated responsive video player modal with fullscreen & picture-in-picture.

### 8. 🎬 Smart Offline Media Organization & Metadata (Jellyfin-Style)
* **Automatic Scene & Torrent Parsing**: Instantly cleans complex video filenames (e.g. `Inception.2010.1080p.BluRay.x264.mp4` ➔ Title: **Inception**, Year: **2010**, Resolution: **1080p**).
* **TV Show Season & Episode Detection**: Automatically groups episodes into series and seasons (`Breaking.Bad.S01E03.720p.mkv` ➔ Series: *Breaking Bad*, Season 1, Episode 3).
* **Automatic Video Poster Snapshots**: Captures high-res video preview thumbnails using embedded FFmpeg and caches them permanently with zero network calls.
* **Virtual Library Organization**: Filter and sort movies by **Category (Movies vs TV Series)**, **Release Era / Decades (2020s, 2010s, 2000s, 90s, Classic)**, and **Resolution (4K UHD, 1080p FHD, 720p HD)**.
* **1-Click Metadata Editor**: Edit title, artist, album, year, and genre directly from any device.

### 9. 💾 One-Tap "Save to Device" (High-Speed Wi-Fi Transfer)
* Any phone or laptop connected over Wi-Fi can tap the Download icon to save a song or movie directly to their local device storage at full Wi-Fi speeds (300–800 Mbps).

---

## 🚀 Getting Started

### 1. 1-Click Launch (Windows)
* **Local Mesh Player**: Double-click [`start_player.bat`](file:///c:/Users/Sahaveer/PycharmProjects/MediaPlayer/start_player.bat)
* **Worldwide Global + Mesh Player**: Double-click [`start_global_player.bat`](file:///c:/Users/Sahaveer/PycharmProjects/MediaPlayer/start_global_player.bat)

### 2. Manual CLI Start
* **Local Mesh Mode**:
  ```bash
  python run_server.py
  ```
* **Dual Mode (Mesh + Worldwide 4G/5G Access via Cloudflare)**:
  ```bash
  python run_server.py --global
  ```

---

## 🐧 Running as a 24/7 Linux Server (Tailscale Global Access)

Because your Linux server already has **Tailscale** installed, MediaPlayer can run 24/7 in the background:

### Option A: Running with PM2
```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Option B: Running with Systemd
```bash
# Copy unit file to systemd directory
sudo cp mediaplayer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mediaplayer
```

### 🌍 Accessing Anywhere in the World:
1. **Direct Tailnet P2P**:
   Open `http://<your-linux-tailscale-ip>:8000` or `http://<linux-hostname>:8000` from any phone or laptop on your Tailscale account.
2. **Public HTTPS via Tailscale Funnel (No Tailscale app required on phone)**:
   ```bash
   tailscale funnel 8000
   ```
   This gives you an official HTTPS URL (`https://<node>.<tailnet>.ts.net`) with free Let's Encrypt SSL!
3. **Built-in Cloudflare Tunnel**:
   ```bash
   python3 run_server.py --global
   ```

---

## 📱 Navigation Guide

* 🎵 **Music**: Browse all indexed songs, artists, albums, and playlists with lock screen controls.
* 🎬 **Movies & Videos**: Grid view of all shared video files with duration and video player.
* 📥 **Downloader**: Paste a YouTube link, pick Audio/Video & Quality, and track download progress.
* 🌐 **Wi-Fi Peers**: View active devices sharing media on your local network.
* 🔒 **Privacy & Folders**: Add/remove shared folders, edit device name, and toggle Stealth mode / Worldwide Remote Access.

---

## 🧪 Running Tests
```bash
python test_hub.py
```
