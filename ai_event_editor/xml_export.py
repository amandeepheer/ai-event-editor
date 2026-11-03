"""Experimental FCP7 XML exporter; not yet verified in Premiere."""
from pathlib import Path
import xml.etree.ElementTree as ET
def element(parent, tag, value=None, **attrs):
    node = ET.SubElement(parent, tag, attrs)
    if value is not None:
        node.text = str(value)
    return node
def export(plan: dict, output: str, music: str | None = None, audio_start: float = 0, audio_end: float | None = None) -> str:
    from .music import AudioRange
    if audio_end is not None:
        selection = AudioRange(audio_start, audio_end).validate()
        if selection.duration * plan["fps"] + 1e-6 < plan["duration_frames"]:
            raise ValueError("Selected audio excerpt is shorter than the video")
    elif audio_start != 0:
        raise ValueError("Audio end is required when audio start is specified")
    root = ET.Element("xmeml", {"version": "4"})
    sequence = element(root, "sequence", id="sequence-1")
    element(sequence, "name", "Energetic Event Recap - 60 seconds")
    element(sequence, "duration", plan["duration_frames"])
    rate = element(sequence, "rate")
    element(rate, "timebase", plan["fps"])
    element(rate, "ntsc", "FALSE")
    media = element(sequence, "media")
    track = element(element(media, "video"), "track")
    for n, shot in enumerate(plan["segments"], 1):
        clip = element(track, "clipitem", id=f"clip-{n}")
        element(clip, "name", Path(shot["path"]).name)
        element(clip, "start", shot["timeline_start"])
        element(clip, "end", shot["timeline_start"] + shot["duration_frames"])
        element(clip, "in", shot["source_in_frame"])
        element(clip, "out", shot["source_in_frame"] + shot["duration_frames"])
        file = element(clip, "file", id=f"file-{n}")
        element(file, "name", Path(shot["path"]).name)
        element(file, "pathurl", Path(shot["path"]).expanduser().resolve().as_uri())
        r = element(file, "rate")
        element(r, "timebase", plan["fps"])
        element(r, "ntsc", "FALSE")
        element(file, "duration", shot["source_in_frame"] + shot["duration_frames"])
    if music:
        clip = element(element(element(media, "audio"), "track"), "clipitem", id="music-1")
        element(clip, "name", Path(music).name)
        element(clip, "start", 0)
        element(clip, "end", plan["duration_frames"])
        audio_in = round(audio_start * plan["fps"])
        element(clip, "in", audio_in)
        element(clip, "out", audio_in + plan["duration_frames"])
        file = element(clip, "file", id="music-file")
        element(file, "name", Path(music).name)
        element(file, "pathurl", Path(music).expanduser().resolve().as_uri())
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
    return str(destination)
