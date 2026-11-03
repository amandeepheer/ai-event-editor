# AI Event Editor

Local-first event highlight editing with one shared Python engine, a Windows-friendly desktop workflow and an experimental Adobe Premiere Pro UXP panel.

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

## Premiere workflow (experimental)

Load `premiere-plugin/` with Adobe UXP Developer Tool. Open a Premiere project, choose **Open reviewed edit**, select the desktop-generated edit file, review it, and explicitly confirm **Create new sequence**.

The native adapter uses documented Adobe APIs to import media into a new bin, create video-only source subclips and an optional audio-only music subclip, and assemble individual editable clips in a new sequence. It does not edit existing sequences, change source marks, delete items, or automatically save the project. Sequence geometry uses Premiere's default preset; review framing after import.

Native creation requires Premiere 26.3+; the earlier inspection/validation scaffold remains available on compatible older UXP hosts. The adapter is covered by API contract tests with a test double. **It has not yet been verified inside installed Premiere.** On failure, newly imported media/subclips and any partial new sequence are retained for review.

## Current limitations

- Windows visual QA and real-camera testing are pending; automated CI runs on Linux.
- Beat/moment analysis is heuristic. Basic mode does not rank meaningful moments; optional CLIP labels require review. Local music RMS/onset analysis varies pacing around louder passages and approximate onsets; it is not reliable BPM, musical-structure or emotion recognition.
- Speed ramps and slow motion are planning metadata; rendering refuses them. Style choices affect pacing/coverage, not colour grading or implemented transitions.
- Effects intensity, interview quote selection, speech ducking, editable native titles, an installer, and direct panel-to-engine communication remain later milestones.
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
