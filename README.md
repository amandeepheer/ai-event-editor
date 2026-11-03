# AI Event Editor

**Plugin-first AI event video editor for Adobe Premiere Pro**, powered by a shared local-first Python editing engine. Optional standalone MP4 rendering uses FFmpeg.

Development status: early prototype. The Premiere panel is a non-destructive scaffold; native timeline creation is **not** implemented yet. Existing FCP7 XML export is experimental and has not been verified in Premiere Pro.

## Current prototype
- Media scanning, AI-assisted shot classification and ranking
- Music beat detection, timeline planning and adjustable energy
- Speed-ramp and slow-motion **planning metadata** (not yet rendered)
- Timed title specifications and initial FFmpeg overlay support
- Basic standalone MP4 rendering for normal-speed footage
- Experimental Premiere XML export
- Version 1 edit plans with stable clip IDs, legacy compatibility, timing validation and local preflight
- Matching Python/Premiere panel contract tests

## Primary next milestone
Create and verify a Premiere Pro plugin panel that applies the shared AI edit plan to an editable Premiere timeline. Confirm Adobe API compatibility first; advanced effects may require fallbacks.

See [development plan](docs/DEVELOPMENT_PLAN.md) for scope, stages, limitations and acceptance criteria.

## Standalone desktop preview

On a Windows machine with Python and FFmpeg installed, launch `python -m ai_event_editor.desktop`. This minimal Tkinter UI opens an existing edit-plan JSON and renders a normal-speed MP4. It is not yet a full visual editor or packaged installer.

## Premiere plugin preview

The `premiere-plugin/` directory contains an early Adobe UXP panel scaffold. Load it with Adobe UXP Developer Tool into a compatible Premiere version; it currently validates JSON plans and inspects the active project without changing the timeline. It now reports clip count, duration and unsupported standalone speed effects using the same tested contract as Python. Native sequence editing remains the next integration milestone.

## Check a plan locally

Run `python -m ai_event_editor.cli validate-plan edit-plan.json`, use **Check edit plan** in the desktop window, or paste JSON into the Premiere panel and click **Validate plan**. These checks validate timing without starting FFmpeg, loading AI models, or contacting a cloud service. Media existence and decodability are checked during rendering, not by preflight.

See [edit-plan contract](docs/EDIT_PLAN.md) for timing units and compatibility. Speed ramps and slow motion remain suggestions; standalone rendering refuses them rather than silently dropping the requested effect.
