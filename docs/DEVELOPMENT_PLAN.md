# AI Event Editor — Development Plan

## Product direction (approved November 2026)
Build one local-first Python AI editing engine with **Adobe Premiere Pro plugin first** and **optional standalone MP4 rendering**. Work on `main` only. Do not modify FotoDigger. Prefer local processing and low-cost CI; no mandatory paid cloud AI.

Clarified direction: typed instructions should control Premiere's own native editing tools, keeping effects, transitions, source clips and keyframes editable. Native Auto Reframe/tracking must not be replaced by baked external crop files. The [native-control audit](PREMIERE_NATIVE_AUDIT.md) distinguishes documented API routes, existing implementation, host verification and manual steps. A read-only **Check native tools** inventory is available for installed-host discovery; it does not apply edits or mark future features complete.

## Intended workflow
1. Open Premiere Pro and the AI Event Editor panel.
2. Select source clips, music, desired duration (30–300 seconds), and editing style.
3. Optionally type a plain-English instruction describing pacing, titles, transitions, and effects.
4. Analyze media locally; rank footage; preview and adjust the proposed edit.
5. Apply the plan to an **editable Premiere timeline**, preserving source references and user adjustments.
6. Fine-tune natively in Premiere. Re-run AI only on explicitly selected/unlocked elements.
7. Optionally render an MP4 independently with FFmpeg.

## Project panel source workflow (version 0.5)

The plugin reads selected Project panel clips/bins, expands nested bins read-only and asks the loopback helper to classify local streams. It offers explicit music selection when several audio-only files are found. Interpret/Build prepare footage automatically if needed; no existing timeline is required. Whole linked files are used; source marks/subclip bounds/effects/proxy/interpretation overrides are not transferred. The existing new-bin/source-subclip assembly remains unchanged apart from a project-identity guard. Original source items and files are preserved. Source collection, ambiguous audio, offline/error handling, project-switch guards, real HTTP media-to-plan and packaged Windows classification/build are test-covered; installed Premiere acceptance remains pending. Effects/transition/tracking/retiming controls are separate milestones.

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
- Premiere UXP panel validates plans, opens locally generated reviewed edits and includes an experimental new-sequence adapter using documented subclip/timeline actions. Contract tests use a mock Adobe host; native sequence editing has not been verified inside installed Premiere. Direct engine communication now uses the authenticated loopback helper; native effects remain pending.
- Title specifications include position presets, coordinates, opacity and animations; advanced visual controls and general language understanding are not implemented. A bounded offline instruction parser now supports length, style, pacing and category selection.
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


## Premiere-first integration milestone

The panel now performs footage/music setup, review, typed instruction feedback and plan generation through an authenticated loopback companion. The standalone UI and legacy plan handoff remain available but are no longer required for this workflow. Previews open in Premiere's Source Monitor. Current typed interpretation is limited offline parsing of duration, style, pacing and explicit category inclusion/exclusion; unsupported requests block generation.

Completed code is covered by local HTTP integration tests, real FFmpeg tests and panel/native API test doubles. Installed Windows/Premiere verification, packaged installation, general instruction understanding and advanced effects remain acceptance gates. See `PREMIERE_WORKFLOW.md` for accurate startup and feature boundaries.


## Automatic companion startup

One-time per-user Windows configuration generates a background launcher and private connection file. The panel remembers a user-approved UXP file token, reconnects on opening, and launches the fixed helper only when no running service responds. Adobe launch consent is handled normally and can be remembered. Duplicate launch prevention, timeout, denial, expired file access and invalid pairing are covered by tests. A packaged installer, installed Windows/Adobe verification and automatic review-state recovery remain pending.


## AI Edition / add-on milestone

A managed Windows Python runtime is bundled with the updated installer. Setup buttons install/verify CPU or NVIDIA Torch and CLIP without user commands. Optional pinned Ollama installation/model pulling and constrained local-language interpretation are connected to the panel. Model output only maps to implemented settings. Known unsupported requests remain blocked. Windows CI verifies real CPU inference and cached AI footage preparation; NVIDIA/real Qwen performance and installed Premiere remain user-machine verification. No speed effects, titles or speech editing are implied by these downloads.
