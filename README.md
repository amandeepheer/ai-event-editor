# AI Event Editor

Local-first event highlight editing with one shared Python engine, a Windows-friendly desktop workflow and an experimental Adobe Premiere Pro UXP panel.

**Start here:** [Plain-language user guide](USER_GUIDE.md) — first-time setup, automatic startup, everyday editing, supported instructions, saving work and troubleshooting.

## Windows AI Edition installer preview

The [Windows installer workflow](https://github.com/amandeepheer/ai-event-editor/actions/workflows/windows-installer.yml) builds **AI-Event-Editor-AI-Setup-0.4.0-Windows-x64.exe**, available in its successful **AI-Event-Editor-AI-Installer** artifact. Extract the download and run Setup. No system Python or terminal commands are needed. Artifacts expire after 30 days; use the latest passing build.

The updated installer includes the basic engine, setup/status app, Adobe CCX panel and an isolated Python runtime for optional AI. Finish basic setup, install the Adobe panel, then optionally install CLIP (CPU or NVIDIA) through Setup and Status. Optional Ollama and Qwen download buttons enable broader local interpretation when selected in the panel. Downloads can be several GB; they are explicit setup operations and are not silently performed when the panel opens.

No advanced editing capability is implied by a model download. Effects, speed remapping, titles and speech editing remain unfinished. NVIDIA hardware, actual Ollama/Qwen and native Premiere must still be verified on the user's computer. See [AI add-on details](docs/AI_ADDON.md) and [installer details](docs/WINDOWS_INSTALLER.md). Existing source and standalone workflows remain below.

## Guided desktop workflow

With Python 3.10+ and FFmpeg/FFprobe/FFplay on your PATH:

```sh
python -m pip install -e .
python -m ai_event_editor.desktop
```

1. Add clips or a footage folder. Choose optional music, excerpt start/end, 30–300 second edit length, style and Calm / Balanced / Energetic pacing.
2. Prepare moments locally. The default mode creates unranked windows and thumbnails without AI packages or model downloads. Optional category suggestions require vision extras and an already cached CLIP model.
3. Review thumbnails and play moments. Keep makes a moment eligible; Reject excludes it; Must include guarantees an excerpt from that moment. Relabel categories and save/reopen your review.
4. Create the reviewed edit. Missing categories produce coverage warnings, not errors. Insufficient unique footage or conflicting pinned moments produce actionable errors instead of repeating footage.
5. Render a normal-speed MP4 locally, or save the edit file and open it in the Premiere panel. You do not need to write or paste JSON.

The existing manual plan renderer is still available through **Render an existing plan** or `python -m ai_event_editor.desktop --legacy`.

## Premiere-first workflow (experimental)

On Windows, run `scripts/Configure-Premiere-Autostart.cmd` once. Load `premiere-plugin/` with Adobe UXP Developer Tool, click **Set up automatic start** and select the generated `engine-connection.json`. The panel remembers the connection and starts or reconnects to the background helper when opened. Adobe may show a launch-permission dialog, with an option to remember your choice. Manual startup and code pairing remain available as a fallback.

Inside the panel: **Add footage → choose music/length/style → Prepare moments → review thumbnails and Keep/Reject/Must include → type supported instructions → Build reviewed edit → Create Premiere sequence**. Source and music previews open in Premiere's Source Monitor. Continue editing and export with Premiere's normal tools. There is no requirement to open the standalone editor or transfer JSON files.

Typed instructions currently support duration, pacing, style and explicit include/exclude category commands, for example `Make a one-minute cinematic recap with energetic pacing`. The default is an offline rules interpreter. Optional local Ollama/Qwen can translate broader phrasing into the same bounded settings, with validation and human review. Unknown instructions and requests for unfinished features are shown before generation rather than silently dropped.

Native assembly requires Premiere 26.3+. The adapter creates a new bin, source subclips and an editable sequence; it does not edit existing sequences, change source marks, delete items or automatically save the project. Default Premiere geometry is retained. Native creation, Source Monitor preview and UXP network behavior still need verification in installed Premiere. Automated panel/native tests use explicit test doubles; real loopback HTTP and FFmpeg tests also run.

Automatic startup requires the one-time Windows configuration above and Python with `pythonw.exe`. A basic Windows installer build is now available through the Windows installer workflow. Windows/Premiere launch behavior has not yet been verified on the user’s computer. See [Premiere setup and supported instructions](docs/PREMIERE_WORKFLOW.md).

## Current limitations

- Windows visual QA and real-camera testing are pending; automated CI runs on Linux.
- Beat/moment analysis is heuristic. Basic mode does not rank meaningful moments; optional CLIP labels require review. Local music RMS/onset analysis varies pacing around louder passages and approximate onsets; it is not reliable BPM, musical-structure or emotion recognition.
- Speed ramps and slow motion are planning metadata; rendering refuses them. Style choices affect pacing/coverage, not colour grading or implemented transitions.
- Effects intensity, interview quote selection, speech ducking, editable native titles, NVIDIA performance verification and broader editing capabilities remain later milestones.
- Experimental XML export remains available and is not proof of native Premiere compatibility.

See [workflow details](docs/GUIDED_WORKFLOW.md), [edit-plan contract](docs/EDIT_PLAN.md), and [development plan](docs/DEVELOPMENT_PLAN.md).

## CLI and tests

Existing scan/analyze/select-shots/build/render commands remain available. Check a saved plan without rendering:

```sh
python -m ai_event_editor.cli validate-plan reviewed-edit.json
python -m pip install -e '.[test]'
python -m pytest -q
```

Node.js is required for Python/panel parity and native adapter contract tests. FFmpeg and FFprobe are required for real render tests. No paid cloud service is required.
