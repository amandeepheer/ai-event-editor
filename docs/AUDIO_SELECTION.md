# Non-destructive music excerpt selection

The original audio file is never rewritten. The editor reads only the requested
range for beat detection and references source in/out offsets in the experimental
Premiere XML.

Example: select 30.2s through 200.5s from a full song, then build a 60s video:

```bash
ai-event-editor preview-audio song.mp3 --audio-start 30.2 --audio-end 200.5
ai-event-editor beats song.mp3 --audio-start 30.2 --audio-end 200.5 --output beats.json
ai-event-editor build shots.json --music song.mp3 --audio-start 30.2 --audio-end 200.5 --analyze-music --duration 60 --dynamic-mix
```

Beat timestamps are **relative to the selected excerpt**, starting at zero.
The export places the original song on the timeline with a source in-point
at 30.2s. For a 60-second video, the song source out-point is 90.2s.
The selected end of 200.5s is the available upper bound, not a request to
stretch 170.3s of music into 60s.

Audio preview uses installed `ffplay` (part of FFmpeg); beat analysis requires
the optional `media` dependencies. XML Premiere compatibility is not yet
verified. The CLI has no waveform or GUI yet.
