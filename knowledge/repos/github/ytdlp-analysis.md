# yt-dlp Analysis

**Repository:** https://github.com/yt-dlp/yt-dlp
**Clone:** `~/.hermes/hermes-agent/yt-dlp-clone`
**Last Commit:** acf8ab7a6 (2026-05-26)
**License:** The Unlicense (public domain)

---

## Overview

yt-dlp is a feature-rich command-line audio/video downloader and extractor, forked from youtube-dl and based on the now-inactive youtube-dlc. It is one of the most popular and actively maintained projects of its kind, supporting **1000+ sites** via a modular extractor architecture.

Key numbers:
- **335K+ GitHub stars**
- **1000+ built-in site extractors**
- **Python 3.10+** (also runs on PyPy)
- **Single-file dependency** option via PyInstaller bundle
- **No runtime dependencies** by default (FFmpeg optional for post-processing)

---

## Architecture

### Core Components

```
yt_dlp/
  YoutubeDL.py       # Main download engine (~4500 lines)
  extractor/
    common.py        # Base InfoExtractor class (~4200 lines)
    _extractors.py   # Imports all 1000+ extractors
    [1000+ site files]
  downloader/       # Protocol handlers (http, hls, dash, ffmpeg, rtmp, etc.)
  postprocessor/    # FFmpeg transforms, metadata editing, thumb embedding
  networking/       # HTTP/websocket client, auth, proxy, impersonation
  utils/            # Shared utilities (format parsing, crypto, browser emulation)
  jsinterp.py       # JavaScript runtime for deciphering signatures
  aes.py            # AES encryption/decryption utilities
  cookies.py        # Browser cookie extraction
  options.py        # CLI argument parsing
  plugins.py        # Plugin loading system
```

### Entry Point

- `yt_dlp/__main__.py` -> `YoutubeDL.main()` -> `parseOpts()` + `YoutubeDL()` instance

### Main Class: `YoutubeDL`

`yt_dlp/YoutubeDL.py` (line 199) is the core engine. Key subsystems:

1. **InfoExtractor pipeline** - Each site has an `InfoExtractor` subclass that:
   - Validates URL patterns
   - Fetches and parses page content
   - Extracts video metadata (title, duration, thumbnails, subtitles)
   - Provides format selection data (resolution, codec, bitrate)

2. **Format selection & sorting** - Rich format filtering/sorting system via `FormatSorter`

3. **Downloader layer** - Delegates to protocol-specific downloaders (HTTP, HLS, DASH, RTMP, WebSocket, etc.)

4. **Post-processor pipeline** - Sequential transforms: merge streams, remux, transcode, embed thumbs/subs/metadata, modify chapters, SponsorBlock

5. **Archive system** - Tracks downloaded videos to avoid re-downloading

### Extractor Pattern

Every site extractor inherits from `InfoExtractor` (yt_dlp/extractor/common.py, line 105). A minimal extractor implements:
- `IE_NAME`, `IE_DESC`, `valid_url` regex
- `real_extract(url)` - fetches page, returns `dict` with video info

### Downloader Pattern

Protocol-specific downloaders in `yt_dlp/downloader/`:
- `http.py`, `hls.py`, `dash.py` - streaming protocols
- `ffmpeg.py` - uses external ffmpeg binary for muxing/transcoding
- `common.py` - base `FileDownloader` class with fragment-level parallel download support

---

## Key Features

### Download
- **Multi-protocol** support (HTTP, HTTPS, HLS, DASH, RTMP, RTSP, WebSocket, Fritware)
- **Adaptive streaming** - Select specific quality/resolution tracks
- **Fragment downloading** - Parallel chunk-based download with resume
- **Range downloads** - Download partial byte ranges
- **Resumable downloads** via `.part` files and archive tracking
- **External downloader integration** (aria2c, avconv, curl, ffmpeg, mkvmerge, mpv, etc.)
- **Proxy support** - HTTP(S)/SOCKS proxy routing
- **Geo-restriction bypass** via extractor arguments

### Format Selection
- **Format sorting** by resolution, fps, codec, bitrate, size, tbr, vbr, abr
- **Format filtering** with complex expressions
- **Video+audio track merging** via ffmpeg
- **Format fallback chains**

### Post-Processing
- **FFmpeg-based**: transcoding, remuxing, merging audio/video
- **Thumbnail embedding** (xattr, EXIF, video metadata)
- **Subtitle extraction and embedding** (SRT, VTT, ASS)
- **Metadata editing** (title, uploader, upload date, chapters, etc.)
- **SponsorBlock** integration (skip sponsored segments)
- **Chapter generation and modification**

### Authentication & Access
- **Cookie import** from browsers (Chrome, Firefox, Edge, Safari, etc.)
- **NetRC** machine-based credential files
- **HTTP Basic/Digest Auth**, OAuth, JWT, token-based auth
- **2-channel authentication** (TV + phone)
- **Age limit bypass** via configurator

### Browser & Anti-Bot Evasion
- **TLS/TCP stream impersonation** via curl-cffi (mimics real browser fingerprints)
- **JSInterp** - Embedded JavaScript interpreter to decode obfuscated signatures
- **AES decryption** - For encrypted media signatures
- **User-agent rotation**
- **Accept-Language spoofing**

### Output & UX
- **Template-driven filenames** (`%(title)s.%(ext)s`)
- **Progress hooks** (download %, speed, ETA, file size)
- **Console title updates** with progress state
- **Color output** (terminal ANSI colors)
- **Quiet/batch modes** for scripting
- **Simultaneous downloads** (multiple instances or queue)
- **Playlist extraction** (full or partial, by date range or index)
- **Multi-archive support**

### Extensibility
- **Plugin system** (`yt_dlp/plugins.py`) - load custom extractors/post-processors
- **Extractor arguments** (`--extractor-args`) - pass site-specific parameters
- **Configuration files** - system-wide, per-site, per-directory precedence
- **Environment variable support**

### Auto-Update
- **Self-update** via `yt-dlp --update` (checks GitHub releases)
- **Binary bundle** via PyInstaller

---

## Hermes Integration Potential

### Why Hermes Would Use yt-dlp

1. **Multimedia download orchestration** - Hermes could dispatch download tasks to yt-dlp for any of 1000+ supported sites, making it a universal media fetcher.

2. **Plugin architecture** - yt-dlp's plugin system (`yt_dlp/plugins.py`) allows custom extractors and post-processors. Hermes could load domain-specific plugins that wrap yt-dlp calls.

3. **Python API** - yt-dlp is designed to be imported and driven programmatically:
   ```python
   from yt_dlp import YoutubeDL
   with YoutubeDL({'format': 'best'}) as ydl:
       ydl.download(['https://example.com/video'])
   ```
   This makes it trivial to subprocess or import within Hermes tooling.

4. **Progress hooks** - Provides callbacks for download progress, errors, completion. Hermes could wire these into its own task tracking.

5. **No deep 入庫 analysis needed** - yt-dlp is well-documented, battle-tested, and has an active upstream. No security audit/review is needed.

### Integration Patterns

- **Subprocess wrapper** - Hermes spawns `yt-dlp` as a CLI tool with JSON output (`--quiet --print json`) and parses results.
- **Library import** - For tighter coupling, import `yt_dlp.YoutubeDL` directly in Hermes Python tasks.
- **Post-processor pipeline** - Chain Hermes-specific post-processing (e.g., OCI image layer embedding, artifact archival) via yt-dlp's hook system.
- **Extractor arguments** - Pass site-specific params (auth tokens, cookies) from Hermes task context.

### Considerations

- **FFmpeg dependency** - Best features (merging, transcoding, subtitle embedding) require `ffmpeg` binary. May need to bundle or require it.
- **Python version** - Requires Python 3.10+; Hermes must ensure compatibility.
- **Large codebase** - 10K+ lines across core files. Direct API integration should be careful about API stability.
- **Not a library by design** - yt-dlp's primary interface is CLI; programmatic use works but is not the primary focus.

---

## File Inventory of Clone

| Path | Description |
|---|---|
| `README.md` | Primary docs (178K) |
| `supportedsites.md` | 1000+ supported site list |
| `Changelog.md` | Release history |
| `yt_dlp/YoutubeDL.py` | Core engine (4512 lines) |
| `yt_dlp/extractor/common.py` | Base InfoExtractor class (4189 lines) |
| `yt_dlp/extractor/_extractors.py` | 1000+ extractor imports |
| `yt_dlp/downloader/common.py` | Base downloader class |
| `yt_dlp/downloader/hls.py`, `dash.py`, `http.py` | Protocol handlers |
| `yt_dlp/postprocessor/` | FFmpeg and metadata processors |
| `yt_dlp/networking/` | HTTP/websocket client |
| `yt_dlp/utils/` | Shared utilities |
| `bundle/` | PyInstaller bundle support |
| `test/` | Test suite |

---

## Summary

yt-dlp is a mature, production-grade multimedia downloader with a highly modular architecture. Its plugin-friendly design, rich Python API, and zero-dependency core make it an excellent candidate for integration into Hermes workflows. The main integration path is via subprocess wrapper or direct Python import, leveraging yt-dlp's extensibility hooks for progress tracking and post-processing customization.