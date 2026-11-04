# Premiere-first local workflow

The Premiere panel now contains footage/music setup, thumbnail review, typed instruction feedback, local edit generation and native new-sequence creation. There is no requirement to open the standalone desktop editor or manually transfer JSON. Finish, adjust and export using Premiere's normal editing tools after the sequence is created.

This is an integrated development preview, not a verified installer release. Automated tests cover the Python engine, the real loopback HTTP service, panel events using explicit DOM/UXP test doubles, and native sequence assembly using an Adobe API test double. They do not establish installed Premiere compatibility or Windows visual quality.

## First-time setup on Windows

1. Install Python 3.10+ and FFmpeg (including FFprobe) on PATH. From the repository directory run `python -m pip install -e .`.
2. Run `scripts/Configure-Premiere-Autostart.cmd` once (or `python -m ai_event_editor.service --configure-plugin`). It creates a user-local launcher and `engine-connection.json`, and prints the file location. Python for Windows must include `pythonw.exe`.
3. Load `premiere-plugin/` through Adobe UXP Developer Tool and open a Premiere project. Click **Set up automatic start**, select the generated `engine-connection.json` and allow Adobe’s launch request if shown. Adobe can remember the permission choice. The panel remembers the selected configuration using a UXP persistent file token. On subsequent opens it reconnects to a running helper or starts it, then waits for readiness. Manual code pairing remains a fallback. Port 8765 is fixed; incompatible/unauthorized services on that port produce errors rather than automatic relaunches.
4. Import videos/audio into Premiere's Project panel, select source clips or bins and choose **Use selected project media**. No sequence is needed. The helper separates videos and audio-only music candidates; choose one music file when several are found. Set excerpt start/end, length (30–300 seconds), style and pacing. **Add footage** / **Choose music** file pickers remain available. **Preview in Premiere** opens source media in Source Monitor.
5. Click **Prepare moments**. The default creates unranked windows and local thumbnails. Optional cached CLIP suggestions require vision extras and already downloaded model weights; the panel does not download a model.
6. Review thumbnails, preview moments, correct categories and choose Keep, Reject or Must include. Reviews are paginated to keep the panel usable with larger events. Keep is eligible; Must include guarantees an excerpt from the moment when it fits.
7. Type an optional instruction and click **Review instructions** to inspect supported changes. **Build reviewed edit** applies supported instructions and displays the plan summary. Steps 5–6 are optional: Interpret/Build prepare moments automatically when no review session exists; if the source pool is empty they first read the current Project panel selection. Multiple music candidates require a choice before analysis. Building a plan does not change Premiere's timeline.
8. Confirm **Create a new sequence**, then click **Create Premiere sequence**. Individual clips and the selected music excerpt are assembled in a new sequence. Continue editing and export in Premiere. Default Premiere preset geometry is used, so inspect framing.

Native creation and Source Monitor seeking require Premiere 26.3+ and still need testing in an installed Premiere environment. Earlier compatible UXP hosts can retain inspect/validate functions. Source files, existing sequences and source marks are not overwritten. Failure can leave newly imported items or a partial new sequence for review; nothing is automatically deleted or saved.

A packaged Windows installer is available; see the main README for the latest successful build. Automatic review-session recovery is not implemented. Automatic helper startup and restored pairing use the one-time setup above; actual Adobe launch/permission behavior still requires installed-host verification. Review state lives in the open panel and bounded helper sessions. Save the final edit with **Save edit** before closing; **Open saved edit** and standalone review sessions remain available.

## Supported typed instructions

The default interpreter is a deterministic offline parser. The AI Edition optionally uses local Ollama/Qwen for broader phrasing, translated into validated supported settings; see `AI_ADDON.md`. Supported examples:

- `Make a one-minute cinematic recap with energetic pacing.`
- `Use these clips and this music to make a one-minute energetic highlight.` (Choose music first.)
- `Create a 30-second wedding highlight with calm pacing.`
- `Make a 2-minute concert recap with balanced pacing.`
- `Include crowd. Exclude stalls.`

Supported controls are duration, one style, one pacing choice and explicit include/exclude category commands. `Include crowd` pins one kept crowd moment, not every crowd shot. User-rejected moments are not automatically restored. Repeated category commands can be used for multiple categories. Category names are drone, stalls, performance, dancing, crowd and finale. Missing categories never block the planner by themselves.

Unknown phrases, conflicting settings, missing requested categories and unsupported features are reported and block generation. Slow motion, speed ramps, titles/captions, visual effects, grading and interview/speech editing are not implemented through typed instructions. Style names affect pacing/coverage, not native colour grades or transitions. `Make a cinematic recap with slow motion` will report that slow motion is unavailable instead of silently ignoring it.

Instructions regenerate a proposed edit from reviewed source moments. They do not edit arbitrary existing Premiere timeline elements, interpret every natural-language command, preserve manual edits through AI regeneration or provide a chat assistant. Existing sequences remain available because each apply action creates a new sequence.

## Local service contract

The stdlib helper binds only `127.0.0.1`. The panel uses Adobe's documented `domains: "all"` compatibility permission after local-host declarations failed on installed Premiere 26.5.2. This permission is broad; the application client independently fixes every request to `http://127.0.0.1:8765`, rejects alternate hosts/ports and disallows redirects. Files and paths/thumbnail data travel only over loopback. No external API, paid service, model download or media upload is used by this connection. Adobe's permission matching must still be retested in the installed host; the runtime destination guard is automated-test-covered.

Every endpoint requires the pairing token in an Authorization header. Tokens are never sent in URLs or request logs. The helper also validates the Host header and restricts browser origins, provides no arbitrary file-serving endpoint and rejects unknown/duplicate shot IDs or attempts to replace source paths/ranges through review patches. Thumbnail PNGs are returned as data URLs in authenticated job results. The local pairing token is stored in the current user's application data and displayed by the helper; keep it private. The panel persists only the UXP access token for the user-selected configuration file, not a plaintext pairing secret. Each reconnect rereads that approved file. Manual pairing remains memory-only.

Long operations run in one background worker with status polling; concurrent operations are rejected. Completed job metadata is bounded to 16 jobs and four review sessions. Expired sessions produce a message to prepare footage again. Temporary thumbnails are removed when the helper shuts down. A disconnected panel does not automatically resubmit processing or mutate a timeline.

Endpoints (all under `/v1`): health, project-media, prepare, interpret, interpret-local, build and jobs/{id}. Project-media probes up to 2000 absolute local paths and returns video/audio candidates and per-file issues. Album artwork is not treated as footage. Project-media/prepare/build/interpret-local return job IDs. Source ranges remain authoritative in the helper; only decision/category review patches are accepted.

Project selection reads `ProjectUtils.getSelection(project).getItems()` and nested `FolderItem.getItems()` without requiring an active sequence. Offline, sequence, merged/multicam and unreadable items are disclosed. Whole linked files are used, not source marks/subclip bounds or source effects/proxy/interpretation overrides. The current adapter reimports source references in its own bin; original files/items are preserved. A captured selection replaces the source pool and is guarded by the project GUID before build and sequence creation. Changing selection alone does not change the pool; capture again explicitly.

## Remaining verification

Test on the user's Windows/Premiere computer: UXP network origin/permission behavior, pairing, file picker access, thumbnail display, Source Monitor preview, mixed-fps Sony/drone sources, native subclips, frame rate/framing, music offsets, partial failures, preservation of an existing client sequence and normal Premiere export. macOS HTTP restrictions are outside this Windows preview's verified scope.

Adobe references checked for this implementation:
- https://developer.adobe.com/premiere-pro/uxp/resources/recipes/network/
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/sourcemonitor
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/project
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/clipprojectitem
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/sequenceeditor


## Automatic startup details

The per-user setup creates `Start-AI-Event-Engine.cmd` and `engine-connection.json` under `%LOCALAPPDATA%/AIEventEditor`. No registry edits, administrator permissions or login tasks are added. The generated launcher uses the exact Python installation and project location from setup; it starts `pythonw.exe` with the local engine module in background mode. The short launcher window may flash, but there is no persistent helper console to keep open. Keep the project/Python location available; rerun configuration after moving them.

The plugin only declares `.cmd` launch permission. It launches the fixed filename beside the approved connection file through Adobe's `shell.openPath`, with clear purpose text for Adobe's consent dialog. It does not pass shell commands or command-line parameters through UXP. Adobe may display permission each time unless the user remembers the choice. Denial, moved configuration, invalid pairing, unsupported platforms and startup timeout all produce actionable messages; the panel does not silently fall back to a different executable or repeatedly launch copies.

The helper can remain idle after Premiere closes and is reused on the next opening. Manual startup remains available via `Start-Local-Engine.cmd` or `python -m ai_event_editor.service`. Configuration and launcher generation are tested on synthetic paths; automatic launch/consent are tested with an explicit UXP shell test double. Installed Windows launch, persistence and Adobe dialogs are still unverified.

Launch API reference: https://developer.adobe.com/premiere-pro/uxp/resources/recipes/external-process/
