# Decentralized Media Hub

An open-source, peer-to-peer **Offline Media Streaming & Sharing Hub** built with **Python (FastAPI)** and a modern **Progressive Web App (PWA)** mobile player.

Stream your downloaded **Music, Movies, and Videos** across laptops, Android phones, and iPhones over **local Wi-Fi or mobile hotspots with 0 MB internet data used**.

---

## 🌟 Key Features

### 1. 🔒 Privacy by Design & Explicit Folder Sharing
* **Opt-in Sharing**: Only folders you explicitly choose are indexed and visible to others.
* **Stealth / Incognito Mode**: Turn off "Share My Library" at any time. You can still stream media from other devices on Wi-Fi, but your own files remain 100% private and invisible.

### 2. 📥 YouTube & Spotify Downloader (Audio & Video)
* Paste any YouTube or Spotify link inside the app.
* Download as **Audio (MP3/M4A)** or **Full Video (1080p/720p MP4)**.
* Automatically embeds metadata & album art, saves to your local library, and indexes instantly.

### 3. 🎬 Offline Movie & Video Streaming
* Stream `.mp4`, `.mkv`, `.webm`, `.mov` files with **HTTP 206 Byte-Range Seeking** over local Wi-Fi.
* Instant scrubbing without buffering.
* Integrated responsive video player modal with fullscreen & picture-in-picture.

### 4. 🌐 Zero-Config Wi-Fi Peer Discovery (Mesh Network)
* Devices on the same Wi-Fi / Hotspot automatically discover each other via **mDNS / Zeroconf**.
* Browse collective songs and movies shared across everyone's devices on the network.

### 5. 💾 One-Tap "Save to Device" (High-Speed Wi-Fi Transfer)
* Any phone or laptop connected over Wi-Fi can tap the Download icon to save a song or movie directly to their local device storage at full Wi-Fi speeds (300–800 Mbps).

---

## 🚀 Getting Started

### 1. 1-Click Launch (Windows)
Double-click `start_player.bat` in the project folder. It will:
* Check Python & auto-install dependencies.
* Launch the Media Player server with terminal QR pairing code.
* Automatically open the web player in your browser (`http://localhost:8000`).

### 2. Manual CLI Start
```bash
python run_server.py
```
* **Desktop Browser**: `http://localhost:8000`
* **Phone on Same Wi-Fi**: `http://<your-pc-ip>:8000` (scan the terminal QR code with your phone camera).

### 3. Worldwide Remote Access (Optional on 4G/5G)
```bash
python run_server.py --tunnel
```

---

## 📱 Navigation Guide

* 🎵 **Music**: Browse all indexed songs, artists, albums, and playlists with lock screen controls.
* 🎬 **Movies & Videos**: Grid view of all shared video files with duration and video player.
* 📥 **Downloader**: Paste a YouTube link, pick Audio/Video & Quality, and track download progress.
* 🌐 **Wi-Fi Peers**: View active devices sharing media on your local network.
* 🔒 **Privacy & Folders**: Add/remove shared folders, edit device name, and toggle Stealth mode.

---

## 🧪 Running Tests
```bash
python test_hub.py
```
