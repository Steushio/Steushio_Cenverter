# Sconvert - v1.0.0 Initial Release

Welcome to the first official release of **Sconvert**! 
This release introduces a fully portable, native desktop experience for high-performance FFmpeg video and audio conversion.

## 🚀 Key Features

- **Standalone Portable Executable**: Requires zero installation. `FFmpeg` is statically bundled within the `.exe`, ensuring it works silently offline without modifying your system `PATH` or requiring Python.
- **Drag & Drop Batch Processing**: Smoothly queue up dozens of media files simply by dragging them into the CustomTkinter UI.
- **Live Visual Progress Tracking**: Automatically maps complex background FFmpeg terminal calculations (`time=00:00:00.00`) directly onto a native graphical progress bar.
- **Smart Presets**: One-click targeted configurations, including:
  - Extract Audio
  - Pro-Editing Proxies
  - Remuxing bypassing re-encode
  - Full Re-encode
  - Compress (High-efficiency defaults)
  - OBS Fix & YouTube Optimizations
- **Advanced Toggles & Syncing**: Fix desyncing issues natively with `-vsync 1` and `-fflags +genpts` timestamp reconstruction flags.
- **Granular Backend Pipeline**: Full UI mapping for critical parameters like Codec variations, CRF (Constant Rate Factor) quality sliders, Audio Bitrates, and Sample Rates (44.1k/48k).

## 📥 Installation
1. Go to the "Assets" section below.
2. Download `Sconvert.exe`.
3. Double-click the file to launch it instantly! No setup required.

## 📜 Licensing
**Licensed to Amitraj S.**
This application is absolutely **Free of Use**, but it is **Not for Sale**. See the embedded `LICENSE` for more details.
