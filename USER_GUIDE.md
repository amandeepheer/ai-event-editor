# AI Event Editor — Start here

A practical reference for setting up and using the project, including after a long break.

**Project:** [amandeepheer/ai-event-editor](https://github.com/amandeepheer/ai-event-editor)  
**Use this branch:** `main`  
**Guide updated:** 4 November 2026  
**Current release in the repository:** development preview, version 0.5.2

> The automated tests passed, but this preview has not yet been verified inside installed Windows/Premiere Pro. A basic installer preview is available through a successful Windows build; it is not a verified production release. Test with a small copy of an event project before using it for a client delivery.

## 1. What this project does

### Connection permission fix in 0.5.2

If the panel says **Permission denied ... Manifest entry not found**, Premiere is blocking the plugin's network declaration. Both port-qualified and host-only entries failed on the user's installed Premiere 26.5.2. Version 0.5.2 uses Adobe's documented `domains: "all"` compatibility permission. Adobe may describe this as broad network access; the application client still restricts every request to `http://127.0.0.1:8765`, rejects other hosts/ports and disables redirects. No cloud service was added. Install/update the Premiere panel, fully close Premiere 2025 and 2026, and reopen 2026. Confirm **Panel version 0.5.2** at the top. Pairing again or repeatedly starting the helper cannot repair a manifest permission denial. This workaround still needs installed-host verification; automated tests do not execute Adobe's permission matcher.

The main goal is to prepare an event highlight **inside Adobe Premiere Pro**, then let you continue editing and export normally in Premiere.

The intended direction is to control Premiere's native editing tools from your instructions, with editable clips, effects, transitions and keyframes. [Native capability audit](docs/PREMIERE_NATIVE_AUDIT.md) lists what Adobe exposes, what our plugin implements and the remaining manual steps. In the updated panel, **Native Premiere tools > Check native tools** reads the installed APIs/catalogs without changing your project. **Save tool report** saves that inventory locally; it does not prove that editing operations work.

## Use imported Project panel media (version 0.5)

1. Import videos and music into Premiere's **Project panel**. Select source clips or bins containing them. No sequence or timeline placement is needed.
2. Connect the plugin to the local helper, then click **Use selected project media**. It includes nested bins and lists skipped/unreadable items. This replaces the source pool.
3. One audio-only file is selected as music. If several are found, choose one in **Music from selected project audio**, or choose **No music**. Set the excerpt start/end if needed.
4. Type `Use these clips and this music to make a one-minute energetic highlight`. If no music is chosen, omit `and this music`.
5. Click **Build reviewed edit**. It prepares moments automatically if needed. For more control, use **Prepare moments** first and choose Keep/Reject/Must include.
6. Review the summary, tick **Create a new sequence**, then click **Create Premiere sequence**. Clips and the chosen music excerpt remain editable. Save/export normally in Premiere.

If the source pool is empty, Build also attempts to read the current Project panel selection. Once captured, changing the selection does not silently change an edit; use the selection button again. A captured pool is tied to its active project; switch projects and you must capture the media again.

This preview uses whole linked files, not source In/Out marks or subclip boundaries. Source effects, proxies and interpretation overrides are not transferred to fresh source references. Original project items and sequences are preserved; new source references/subclips may appear, but original files are not copied on disk. Video source audio is currently omitted; the selected audio-only file supplies music. Sources are eligible, not guaranteed to all appear; Must include pins reviewed moments. Merged/multicam items, sequences, offline files and still images are unsupported sources.

Project panel selection and native sequence creation still need installed-Premiere verification. Automated tests cover Adobe API doubles, real local classification/preparation/build and Windows packaging. Effects, transitions, retiming and automatic reframing remain unfinished.

| Part | What it means | Do I need to open it? |
| --- | --- | --- |
| Premiere plugin | The panel where you choose footage/music, review moments, type supported instructions and request a new sequence | Yes, for the Premiere workflow |
| Local engine/helper | The Python program doing analysis and edit planning on your computer | After one-time setup, the panel starts or reconnects to it automatically |
| Standalone editor | A separate desktop interface using the same engine, with local MP4 rendering | Optional; not required for editing inside Premiere |

The helper connection does not upload your footage or use a paid cloud AI service. Optional AI category suggestions need installed packages and already cached model weights. Installing software/packages can require internet access; processing your event is local.

## Windows installer route — no Python commands

Use the latest successful [Windows installer build](https://github.com/amandeepheer/ai-event-editor/actions/workflows/windows-installer.yml). Download **AI-Event-Editor-AI-Installer**, extract the ZIP and run the Setup `.exe` inside. GitHub may require you to sign in to download Actions artifacts.

1. Run Setup and open **AI Event Editor Setup and Status**.
2. Click **Finish setup**. It downloads media tools once if needed (approximately 81 MB; internet required), verifies the archive and prepares automatic startup.
3. Click **Install Premiere panel**. Adobe Creative Cloud Desktop installs the included `.ccx` after its confirmation prompts.
4. Open Premiere 26.3+, then **Window > UXP Plugins > AI Event Editor**. Enable plugin Developer Mode if Adobe requires it for this preview.
5. In the panel click **Set up automatic start**. Select `engine-connection.json` from the setup window's **Open connection-file folder** location. Keep that private file.
6. Continue with the everyday editing section below. You do not need the source-development/Python steps that follow.

The installer includes the basic engine and an AI runtime. Use Setup and Status to optionally download CLIP packages/model (CPU or NVIDIA), install Ollama and download Qwen. Large AI downloads are not embedded in Setup and require internet/free disk space. Premiere itself and a standalone MP4 editor are not included. Adobe installation/permissions and real Premiere behavior still need verification on your PC. Source-development setup remains documented below for developers and for the optional standalone editor.

## 2. First-time Windows setup

You need:

- A compatible Premiere Pro installation. Native sequence creation and source preview seeking currently require Premiere **26.3 or newer**.
- Python **3.10 or newer**, including `pythonw.exe` for background startup.
- FFmpeg and FFprobe available on your Windows PATH. FFplay is useful for previews in the optional standalone editor.
- Adobe UXP Developer Tool to load this development plugin.
- The latest project from the repository's **main** branch.

These terminal-based steps are the source-development route. If you use the basic Windows installer above, skip them.

### A. Keep the project in a permanent folder

For example, use `C:\AI-Event-Editor`. Keep your original footage in its normal event folder; adding it to the plugin does not move it into the code repository.

Keep the project folder and Python installation in the same locations after configuration. The automatic launcher remembers those locations. If you move them later, repeat the automatic-start setup.

### B. Install the Python project

Open a terminal in the project folder and run:

```powershell
python -m pip install -e .
```

To check that Windows can find the main prerequisites:

```powershell
python --version
ffmpeg -version
ffprobe -version
```

If a command says it is not recognised, install that prerequisite or correct its PATH before continuing. If software/PATH was changed while Premiere was open, restart Premiere so the helper receives the updated environment.

### C. Configure automatic engine startup once

1. Open the project's `scripts` folder.
2. Double-click **`Configure-Premiere-Autostart.cmd`**.
3. Read the result. The script prints the location of **`engine-connection.json`**. If it reports an error, resolve that error before continuing.
4. The generated files normally live in `%LOCALAPPDATA%\AIEventEditor`. You can paste that folder into File Explorer's address bar.

The configuration creates a background launcher and a private connection file for your Windows user. It does not add a Windows login task or require registry changes. Keep `engine-connection.json` private: it contains the local pairing credential. Do not commit or share it.

### D. Load the plugin and remember the connection

1. Load **`premiere-plugin/manifest.json`** with Adobe UXP Developer Tool.
2. Open your Premiere project and the **AI Event Editor** panel.
3. Click **Set up automatic start**.
4. Select the generated **`engine-connection.json`**, not a saved edit-plan file.
5. If Adobe asks permission to launch the helper, allow it. If Adobe offers a remember-choice option, you can use it.
6. Wait for the connected status.

After this setup, opening the panel attempts to connect automatically. If the helper is already running, it is reused; otherwise the panel launches it and waits for it to become ready. You do not need to open the standalone editor or copy a pairing code every time. Adobe may still ask for launch consent if its permission choice was not remembered.

The short launcher window may flash; there is no persistent helper console to keep open. Actual startup and permission behaviour still need verification on your Windows/Premiere installation.

## 3. Everyday editing inside Premiere

### Step 1 — Add footage and music

- Open the plugin and wait for the local engine connection.
- Click **Add footage** and select the event clips.
- Click **Choose music**, or use **No music** for an edit without a music track.
- Set music start/end in **seconds**. For example, start `30`, end `90` selects a 60-second excerpt. A blank end means start plus the requested edit length.
- Choose an edit length from **30–300 seconds**, a style and Calm / Balanced / Energetic pacing.

The music excerpt must be long enough for the edit and must exist within the music file. Style choices currently affect pacing and coverage; they do not apply colour grading or native visual transitions.

### Step 2 — Prepare and review moments

Click **Prepare moments**. Wait for the thumbnails and review list.

Default preparation creates unranked windows from the footage. It does **not** claim to know the most important moment or person. The default `performance` category is a manual-review starting label; change categories where needed. Optional cached AI can suggest categories, but its suggestions still need review.

| Control | What it does |
| --- | --- |
| Keep | Makes the moment eligible; it may or may not be selected for the final length |
| Reject | Excludes the moment from the proposed edit |
| Must include | Guarantees an excerpt from that moment when it can fit; it does not guarantee the entire source clip |
| Category dropdown | Lets you correct the suggested/manual category |
| Preview in Premiere | Opens the source in Premiere's Source Monitor at the moment's start time |
| Previous / Next | Moves through pages of reviewed moments |

Use Premiere's playback controls to inspect the moment. The displayed end time is a guide; preview playback does not automatically stop there.

Categories are drone, stalls, performance, dancing, crowd and finale. You do not need footage in every category. Missing categories show coverage warnings. Insufficient total usable footage, overlapping pinned moments or too many pins for the selected length can still block creation.

### Step 3 — Type an instruction, if useful

Supported examples:

```text
Make a one-minute cinematic recap with energetic pacing.
```

```text
Create a 30-second wedding highlight with calm pacing.
```

```text
Make a 2-minute concert recap with balanced pacing.
```

```text
Include crowd. Exclude stalls.
```

Click **Review instructions** to see the proposed changes. Then adjust your choices if needed.

The current interpreter understands a limited set of offline rules: duration, one style, one pacing choice, and explicit category inclusion/exclusion. The default rules are **not** a general chat assistant. Optional local Ollama/Qwen can interpret broader phrasing when installed and enabled; its proposed changes must still be reviewed. See [AI setup](docs/AI_ADDON.md).

`Include crowd` pins one kept crowd moment. If there is no kept moment labelled crowd, the plugin asks you to keep/relabel one. Repeat commands for multiple categories, for example `Include crowd. Include dancing.` User-rejected moments are not automatically restored.

Requests for slow motion, speed ramps, effects, titles/captions, grading or speech editing are not implemented and are flagged before generation. Unknown or contradictory instructions also block generation. You can leave the instruction box blank and use the ordinary controls instead.

### Step 4 — Build the proposed edit

Click **Build reviewed edit**. This prepares a plan using your current setup, review choices and supported instructions.

Check the displayed length, clip count and warnings. Building a plan does not change your Premiere timeline.

Changing footage, music, supported setup controls, review choices or instructions invalidates the previous proposed edit. Build again before applying it.

### Step 5 — Create a Premiere sequence

1. Tick **Create a new sequence from this reviewed edit**.
2. Click **Create Premiere sequence**.
3. Wait for the new sequence, then inspect it in Premiere.

The adapter is intended to create individual editable video clips and the selected music excerpt. It creates a new bin, subclips and a new sequence; it does not overwrite your existing sequence or source marks. It does not automatically save the Premiere project.

Native assembly is still experimental. A failed attempt may leave newly imported items or a partial new sequence for inspection. Do not assume a partial result is ready for delivery.

### Step 6 — Finish and export in Premiere

Review framing, shot choices, timing and music. Adjust clips and add any finishing work manually in Premiere, then save the project and export using Premiere's normal tools.

The plugin uses Premiere's default sequence geometry, so check the frame size and framing. Typing instructions does not currently modify arbitrary existing Premiere timeline elements. Regenerating creates another new sequence; it does not carry your manual timeline adjustments into a new AI plan automatically.

## 4. Saving work and returning later

- **Save your Premiere project** normally to preserve the actual timeline and manual adjustments.
- Use **Save edit** in the plugin to save the proposed edit-plan file. Use **Open saved edit** to reopen that plan later.
- A saved plan is not a media backup and does not contain the original footage/music. Keep those files available at their referenced paths.
- Full shot-review recovery after closing/reloading the panel is not implemented. The helper retains only a limited number of recent sessions, so save the final plan before closing. The optional standalone editor separately supports saved review sessions.
- The helper can remain idle after Premiere closes and is reused the next time the panel opens. Review/analysis jobs are not automatically resubmitted after a disconnect.

## 5. Troubleshooting

| What you see | What to check |
| --- | --- |
| Python or FFmpeg is not recognised | Check installation/PATH, then restart the terminal and Premiere |
| Setup says `pythonw.exe` is missing | Use a Windows Python installation that includes the background interpreter; do not rename `python.exe` |
| Automatic-start file moved or access expired | Run the configuration script again and select its generated file through **Set up automatic start** |
| Adobe launch was declined | Allow the launch request when appropriate, or use manual startup below |
| Helper did not become ready | Check Python, FFmpeg, project location and Windows script permissions; read the manual-start console for errors |
| Pairing denied or an incompatible service is using port 8765 | Check that the matching helper is running; do not repeatedly launch more copies. Rerun configuration if needed |
| Session expired | Prepare footage again and reapply the required review choices |
| Requested category is unavailable | Keep/relabel an appropriate moment, or remove that include instruction |
| Insufficient unique footage | Add more usable footage, reject fewer moments or shorten the edit |
| Must include moments overlap or cannot fit | Unpin some moments or choose a longer edit |
| Unsupported instruction | Remove the unsupported request and use supported controls; add that effect manually in Premiere |
| Source media cannot be found | Check that the original files/drives are connected and have not moved |
| Native sequence creation fails | Keep the displayed error and inspect any new partial sequence. Installed Premiere compatibility is still under verification |

### Manual-start fallback

If automatic startup cannot be used:

1. Double-click **`scripts/Start-Local-Engine.cmd`**, or run the following in the project folder:

   ```powershell
   python -m ai_event_editor.service
   ```

2. Keep that helper console running.
3. Paste its pairing code into the Premiere panel and click **Connect**.

This is a fallback, not the required everyday workflow after automatic startup has been configured successfully.

### Reporting a problem

Record the exact panel/helper error, Premiere version, action that triggered it, clip format/frame rate and whether the issue can be reproduced with a small sample. Share a screenshot if helpful, but hide pairing codes and the contents of `engine-connection.json`.

## 6. Current capabilities and unfinished work

| Status | Feature |
| --- | --- |
| Implemented in code; covered by automated tests | Local engine connection, automatic-start state handling, remembered configuration, setup, thumbnails/review, supported typed rules and edit planning |
| Implemented; still requires installed Windows/Premiere verification | Actual helper launch/permissions, panel rendering, Source Monitor preview and native editable-sequence creation |
| Available separately | Standalone desktop workflow, normal-speed MP4 rendering, CLI tools and experimental XML export |
| Not implemented for the plugin workflow | Actual slow motion/speed ramps, effect-intensity controls, native titles/captions, interview/speech editing and music ducking |
| Still pending | NVIDIA/real-Qwen verification, arbitrary timeline understanding, full review-session recovery and real-camera visual/performance evaluation |

**Verified baseline:** GitHub Actions [run #80](https://github.com/amandeepheer/ai-event-editor/actions/runs/41747250384) passed **249 tests** on code commit `6acccd2`. This is a dated reference, not a claim about all future revisions. Check the [latest Actions runs](https://github.com/amandeepheer/ai-event-editor/actions) after later updates. Automated tests do not prove installed Premiere behaviour.

## 7. Updating the project or continuing development

Use the latest **main** branch. Keep the plugin and helper from the same project version. After updating, reload the plugin through UXP Developer Tool and restart an older running helper when necessary. Repeat automatic-start configuration if Python or the project moved.

For a future development session, refer to this repository and these documents:

| Document | Purpose |
| --- | --- |
| [README.md](README.md) | Project overview and entry points |
| [USER_GUIDE.md](USER_GUIDE.md) | This practical reference |
| [Premiere workflow](docs/PREMIERE_WORKFLOW.md) | Detailed connection/startup behaviour and current technical limitations |
| [Development plan](docs/DEVELOPMENT_PLAN.md) | Priorities and acceptance criteria |
| [Edit-plan contract](docs/EDIT_PLAN.md) | Shared plan format and timing rules |
| [Standalone workflow](docs/GUIDED_WORKFLOW.md) | Optional desktop workflow |

Development rules: work on `main` only, do not modify FotoDigger, preserve existing functionality/data, prioritise local processing and minimal cloud cost, and distinguish passing automated tests from Windows/Premiere verification. The next practical acceptance gate is a small real-footage walkthrough on the Windows/Premiere computer.
