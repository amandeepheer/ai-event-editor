# Development status

## Implemented in source
- ffprobe-based media inventory
- librosa music beat extraction (optional dependency)
- FFmpeg scene cut detection (new)
- metadata-based candidate ranking and missing-category reporting (new)
- deterministic 60-second frame-based timeline planner
- experimental FCP7 XML writer
- automated unit tests

## Not yet implemented
- Automated vision-model shot classification (labels must be provided)
- Musical beat synchronization of every individual cut (current planner only nudges section boundaries)
- Local desktop GUI, proxies, previews, slow-motion effects, speed ramps
- Reliable 50/60/100/120 fps conform and variable frame-rate support
- Validation of XML import in Adobe Premiere Pro
- Windows installer

## Safety / limitations
This is a research prototype. The XML writer assumes 25 fps sources and has not been tested in Premiere. The user should not use it for paid client delivery until a real-world end-to-end import and render passes. No video footage is uploaded. Keep API keys out of GitHub. The repository is currently public.
