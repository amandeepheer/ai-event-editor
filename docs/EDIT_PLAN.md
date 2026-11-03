# Edit-plan contract, version 1

The local Python engine produces this JSON format. The desktop renderer consumes it; the Premiere scaffold validates it before future native integration. JavaScript contains only contract validation, not a second AI engine. The Python and JavaScript validators run identical valid/invalid examples in CI.

```json
{
  "schema_version": 1,
  "fps": 25,
  "duration_frames": 50,
  "duration_seconds": 2,
  "segments": [
    {
      "id": "clip-00001",
      "path": "C:/Footage/dancing.mp4",
      "timeline_start": 0,
      "duration_frames": 50,
      "source_in_seconds": 3.2,
      "source_end_seconds": 6,
      "source_fps": 50,
      "speed": 1,
      "speed_effect": {"kind": "normal", "speed": 1}
    }
  ]
}
```

- `fps` is the timeline rate. `timeline_start`, `duration_frames` and legacy `source_in_frame` use timeline frames, including for 50/60 fps sources. They must be nonnegative integral numbers; durations must be positive.
- `source_in_seconds` is authoritative and independent of source fps. `source_fps` describes source media, not the timeline rate. If both source offset forms exist, they must agree within half a timeline frame.
- Source ranges are optional for legacy compatibility. When present, `source_end_seconds` is an exclusive bound; normal-speed edits cannot exceed it. The validator cannot establish physical media duration without decoding/probing the file.
- Segments must be ordered and contiguous from frame zero. No gaps or overlaps are supported on the current single video track. Their total must equal `duration_frames`; optional `duration_seconds` must agree.
- `id` values are unique. Missing IDs receive deterministic positional defaults. Existing IDs and additional metadata are preserved, as are speed suggestions. IDs persist when a saved plan is revalidated; regeneration/reordering does not yet track clip identity across edits.
- Unversioned plans are accepted and normalized to version 1, including inferred contiguous starts and source seconds derived from legacy frame offsets. Explicit version 1 plans require timeline starts. Unknown versions are rejected. Neither validator mutates the supplied object.
- `normal`, `slow_motion` and `ramp` are accepted effect kinds. Non-normal effects and non-unit `speed` are reported as unsupported for standalone rendering. Ramp envelopes are preserved planning metadata; they are not interpreted or retimed in this milestone.

`python -m ai_event_editor.cli validate-plan edit-plan.json` prints a JSON preflight summary. Invalid contracts exit nonzero. A valid contract with speed suggestions exits successfully but reports `standalone_supported: false`. This check does not verify source files, FFmpeg availability, Adobe compatibility or visual quality.

The desktop window uses the Python validator. Its render worker receives a snapshot of input paths and sends completion messages through a queue; all Tkinter operations remain on the UI thread. Windows visual verification is still pending.

Native Premiere sequence creation, engine-to-panel communication, editable effects/titles, true speed rendering, Windows packaging and real-camera evaluation remain separate unfinished work. XML export remains experimental; it is not an implementation of this complete contract or native effects.
