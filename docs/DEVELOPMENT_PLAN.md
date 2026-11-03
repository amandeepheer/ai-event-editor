# AI Event Editor — Development Plan

## Product direction (approved November 2026)
Build one local-first Python AI editing engine with **Adobe Premiere Pro plugin first** and **optional standalone MP4 rendering**. Work on `main` only. Do not modify FotoDigger. Prefer local processing and low-cost CI; no mandatory paid cloud AI.

## Intended workflow
1. Open Premiere Pro and the AI Event Editor panel.
2. Select source clips, music, desired duration (30–300 seconds), and editing style.
3. Optionally type a plain-English instruction describing pacing, titles, transitions, and effects.
4. Analyze media locally; rank footage; preview and adjust the proposed edit.
5. Apply the plan to an **editable Premiere timeline**, preserving source references and user adjustments.
6. Fine-tune natively in Premiere. Re-run AI only on explicitly selected/unlocked elements.
7. Optionally render an MP4 independently with FFmpeg.

## Architecture
- `ai_event_editor/`: shared media analysis, shot selection, beat detection, planning, title specifications, and validation.
- Premiere integration: plugin panel and a supported Adobe API bridge (API/version compatibility must be investigated and proven before implementation). Do not assume XML can express every effect.
- Standalone: FFmpeg renderer for previews and optional final output; may not match Premiere effects perfectly.
- Common versioned, validated JSON edit-plan format, with stable IDs, source timecodes, audio offsets, effect specifications, and edit ownership/locks.
- Clearly distinguish native editable effects from fallback rendered overlays and unsupported features.

## Revised stages
1. **Footage analysis** — implemented prototype; real-camera quality evaluation pending.
2. **Beat-aware edit planning** — implemented prototype; accurate source/timeline time mapping and validation pending.
3. **Shared engine hardening** — in progress: version 1 timeline contract, stable IDs, duration/source-range validation and Python/panel parity tests implemented. Actual time remapping remains pending.
4. **Premiere plugin MVP** — priority: research current supported Premiere extension APIs, panel with media/music/length/style/instruction inputs, engine communication, import and editable sequence creation. Test in installed Premiere.
5. **Premiere-native effects and text** — support compatible transitions, time remapping, native editable titles where possible; manually adjustable X/Y, size, colour, opacity, timing, animation and locks. For effects not exposed through APIs, provide clear alternatives (rendered overlays or manual Premiere edits).
6. **Optional standalone export** — maintain and improve FFmpeg MP4 output, audio, speed effects, overlays; standalone GUI is not launch-critical.
7. **Verification and release** — unit tests, synthetic render smoke tests, real Sony/drone footage tests, Windows and Premiere compatibility, visual QA, performance, installer and documentation.

## Current verified vs unverified
- Code exists for analysis, candidate selection, music beats, edit planning, experimental FCP7 XML, simple FFmpeg MP4 rendering, and timed titles.
- Advanced speed effects are currently planning metadata; renderer explicitly refuses unsupported speed effects.
- Premiere UXP panel validates plans, opens locally generated reviewed edits and includes an experimental new-sequence adapter using documented subclip/timeline actions. Contract tests use a mock Adobe host; native sequence editing has not been verified inside installed Premiere. Direct engine communication and native effects remain pending.
- Title specifications include position presets, coordinates, opacity and animations; advanced visual controls and instruction interpreter are not implemented.
- Baseline GitHub Actions run #76 passed at commit `1fcac3a`. Subsequent changes must pass the complete suite before being reported as verified.
- XML export is experimental and is not proof of a working Premiere plugin.

## Priorities and acceptance criteria
- First milestone: a small plugin panel that can create a real editable Premiere sequence from a shared edit plan, verified in Premiere.
- Preserve manual Premiere edits; no destructive overwrite on regeneration.
- Allow manual adjustment of titles, transitions, and timing where supported; disclose fallback effects.
- Keep original media unchanged; explicit user approval before applying edits.
- Maintain main-only GitHub workflow and inexpensive tests.
- Test locally on Windows/Premiere when the home PC is available; cloud CI alone cannot verify native Premiere integration.


## Guided workflow milestone (November 2026)
- Desktop footage/music setup, excerpt validation, length/style/pacing controls and temporary thumbnails.
- Keep/Reject/Must include decisions, source preview playback, category correction and saved reviews.
- Flexible category coverage, capacity-aware timing, non-overlapping source use and protected moment selection.
- Local RMS/onset music analysis for approximate anchors and louder-passage pacing.
- Plan handoff by file into a Premiere panel; experimental native new-sequence assembly behind explicit confirmation.
- Existing CLI, legacy desktop renderer and XML export retained.

Next acceptance gate: installed Windows/Premiere walkthrough using real Sony/drone footage, including multiple uses of the same source, music offsets, mixed fps, framing, failure recovery and preservation of a manually edited sequence. Effects frequency and interview/speech mixing follow this gate; they are not complete.
