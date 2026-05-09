# wiz-downloader

A dark-themed GUI front-end for **yt-dlp** that lets you download audio or video from YouTube playlists, single videos, and any other site yt-dlp supports — without touching the command line.

---

## Requirements

| Dependency | Notes |
|---|---|
| **Python 3.10+** | Must be on your `PATH` |
| **yt-dlp.exe** | Place on `PATH` or point the GUI at it |
| **ffmpeg.exe** | Required for audio extraction and video merging; must be on `PATH` |

---

## How to run

```
run_gui.cmd          # double-click, or run from a terminal
python gui.py        # alternatively run directly
```

---

## How it works

`engine.cmd` is the original bare yt-dlp command that the project was built around.  
`gui.py` is a Python/tkinter application that builds the same command dynamically from your GUI choices and runs it as a subprocess, streaming its output live into the log panel.

The UI is split into two columns:

- **Left panel** — all settings, scrollable
- **Right panel** — live output log, always visible

### Settings

| Section | What it controls |
|---|---|
| **Source URLs** | One URL per line — playlists, single videos, channels, or any yt-dlp-supported URL |
| **Output** | Download folder (with folder browser) and filename template using yt-dlp variables like `%(title)s`, `%(uploader)s`, `%(upload_date)s` |
| **Format — Audio Only** | Extracts audio; choose format (mp3, m4a, flac, opus …) and bitrate quality |
| **Format — Video + Audio** | Downloads best video + audio and merges into mp4/mkv/webm |
| **Format — Custom** | Free-form yt-dlp format string |
| **Options** | Ignore errors, embed thumbnail, embed metadata, yes-playlist, HLS native, no overwrites, subtitles, description, info JSON |
| **Advanced** | Rate limit, retries, concurrent fragments, sleep between downloads, cookies-from-browser, proxy |
| **Download Archive** | Toggle archive tracking — keeps a text file of already-downloaded IDs so re-running skips them |
| **yt-dlp Executable** | Path to `yt-dlp.exe`; defaults to whatever is on your `PATH` |

### Controls

| Button | Action |
|---|---|
| **Preview Command** | Prints the full yt-dlp command to the log without running it |
| **▶ Download** | Builds and runs the command; live output streams into the log panel |
| **■ Stop** | Kills yt-dlp **and all its child processes** (e.g. ffmpeg) immediately using `taskkill /F /T` on Windows |

Log lines are colour-coded: errors in red, warnings in yellow, section headers in blue.

---

## Files

```
gui.py          Main application
run_gui.cmd     Launcher — runs gui.py with Python
engine.cmd      Original bare yt-dlp command (reference)
```
