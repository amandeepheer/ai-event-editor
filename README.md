# AI Event Editor

**Plugin-first AI event video editor for Adobe Premiere Pro**, powered by a shared local-first Python editing engine. Optional standalone MP4 rendering uses FFmpeg.

Development status: early prototype. The Premiere plugin has **not** been implemented yet. Existing FCP7 XML export is experimental and has not been verified in Premiere Pro.

## Current prototype
- Media scanning, AI-assisted shot classification and ranking
- Music beat detection, timeline planning and adjustable energy
- Speed-ramp and slow-motion **planning metadata** (not yet rendered)
- Timed title specifications and initial FFmpeg overlay support
- Basic standalone MP4 rendering for normal-speed footage
- Experimental Premiere XML export

## Primary next milestone
Create and verify a Premiere Pro plugin panel that applies the shared AI edit plan to an editable Premiere timeline. Confirm Adobe API compatibility first; advanced effects may require fallbacks.

See [development plan](docs/DEVELOPMENT_PLAN.md) for scope, stages, limitations and acceptance criteria.
