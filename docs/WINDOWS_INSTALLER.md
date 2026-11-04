# Basic Windows installer preview

The Windows installer job builds a real x64 Setup executable with PyInstaller (bundled Python helper), Inno Setup (per-user installation) and an independent Adobe CCX ZIP package. Existing source, manual pairing and standalone-editor workflows are retained.

## User installation

Download **AI-Event-Editor-Windows-Installer** from a successful [Windows installer workflow run](https://github.com/amandeepheer/ai-event-editor/actions/workflows/windows-installer.yml). Extract the artifact ZIP, run Setup, then use **AI Event Editor Setup and Status** from Start:

1. Finish setup: media tools are downloaded directly from the publisher if necessary, checked against a pinned SHA-256, and configured in the user's application data. Python is already bundled; no pip commands are needed.
2. Install Premiere panel: opens the included `.ccx` through Creative Cloud Desktop, which handles Adobe's confirmation dialogs. The archive has manifest.json at its root.
3. Open Premiere 26.3+ and the AI Event Editor panel. Use Set up automatic start and select the generated private engine-connection.json. Adobe may require plugin Developer Mode or launch consent.

The helper can start automatically from the panel after pairing. Initial media download is approximately 81 MB. There is no paid cloud API in this installation. The fixed upstream build, digest and downloader are in `ai_event_editor/installed_runtime.py`; if that publisher archive becomes unavailable, a maintainer must update the verified pin rather than bypass checksum checks.

## Included and excluded

Included: bundled Python engine, setup/status window, Adobe CCX, guides and basic unranked footage review/planning. Existing system FFmpeg/FFprobe can be reused; otherwise the media archive is obtained directly at setup time. Downloaded publisher notices/licenses are retained. The installer does not redistribute that FFmpeg archive.

Not included: Premiere/Creative Cloud, CLIP/Torch GPU packages or model weights, Ollama, advanced language understanding or the standalone MP4 editor. GPU suggestions are disabled when the packaged engine reports those packages absent. This changes installed-runtime capability reporting, not the existing source feature. The LGPL media build is sufficient for the Premiere engine's decoding, thumbnails and music analysis; the separate source standalone renderer still has its existing libx264 requirement.

This is an unsigned development build. No code-signing certificate or paid installer service is used. Windows/Adobe may show publisher or installation prompts. A basic installer/HTTP smoke test does not establish actual Creative Cloud acceptance or native Premiere compatibility.

## Build and verification

The workflow uses Windows Server 2025, Python 3.12, PyInstaller and the runner's Inno Setup compiler. Run locally on a suitable Windows development machine with `python packaging/windows/package.py` after installing the build tools. No branches other than main are created.

The job compiles the engine and installer, installs Setup silently into a temporary folder, and runs the installed `.exe` to download/verify media tools, configure frozen startup, inspect its bundled runtime and run actual footage preparation and typed edit building over authenticated loopback HTTP. It structurally validates the CCX archive. The smoke test terminates only its own synthetic helper process; it does not kill a user's running engine.

On success it uploads the executable and installation readme as one artifact with 30-day retention. It uploads diagnostics on failure. PyInstaller/installer outputs live under ignored `build/` and `dist/` folders, not in git. The CI test does not install licensed Premiere or prove GUI/Adobe dialogs.

## Updates and uninstall

Close/save your work and stop an older helper before updating. Installed files are under the user's local Programs folder. Generated pairing configuration, logs and downloaded tools are under `%LOCALAPPDATA%/AIEventEditor`. Uninstall removes program files; it preserves user data, footage and Premiere projects. It also leaves pairing/media-tool state for deliberate user management. Automatic startup will need repair/reconfiguration after uninstall or moving the application.

## References

- PyInstaller runtime paths: https://pyinstaller.org/en/stable/runtime-information.html
- Inno Setup per-user installation: https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm
- Adobe CCX packaging: https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/package/
- Adobe installation: https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/install/
- Media publisher: https://github.com/BtbN/FFmpeg-Builds
