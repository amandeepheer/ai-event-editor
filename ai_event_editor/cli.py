"""Command line interface for MVP."""
import argparse
import json
from pathlib import Path
from .media import scan
from .music import detect_beats
from .planner import Shot, plan
from .xml_export import export

def main():
    parser = argparse.ArgumentParser(description="Local event editor prototype")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("scan")
    p.add_argument("folder")
    p.add_argument("--output", default="media-inventory.json")
    p = sub.add_parser("preview-audio")
    p.add_argument("music")
    p.add_argument("--audio-start", type=float, required=True)
    p.add_argument("--audio-end", type=float, required=True)
    p = sub.add_parser("beats")
    p.add_argument("music")
    p.add_argument("--audio-start", type=float, default=0)
    p.add_argument("--audio-end", type=float)
    p.add_argument("--output", default="beats.json")
    p = sub.add_parser("analyze")
    p.add_argument("folder")
    p.add_argument("--output", default="shot-candidates.json")
    p.add_argument("--max-clips", type=int, default=None)
    p = sub.add_parser("select-shots")
    p.add_argument("candidates", help="JSON output from analyze")
    p.add_argument("--output", default="selected-shots.json")
    p.add_argument("--report", default="selection-report.json")
    p.add_argument("--min-confidence", type=float, default=0.0)
    p.add_argument("--max-per-category", type=int, default=None)
    p = sub.add_parser("styles")
    p.add_argument("--directory", default="my-styles")
    p = sub.add_parser("learn-style")
    p.add_argument("slug")
    p.add_argument("name")
    p.add_argument("references", nargs="+")
    p.add_argument("--base", default="energetic-event")
    p.add_argument("--directory", default="my-styles")
    p = sub.add_parser("render")
    p.add_argument("plan", help="JSON edit plan")
    p.add_argument("--output", default="highlight.mp4")
    p.add_argument("--titles", help="JSON list of editable timed titles")
    p.add_argument("--music")
    p.add_argument("--audio-start", type=float, default=0)
    p = sub.add_parser("build")
    p.add_argument("shots")
    p.add_argument("--beats")
    p.add_argument("--music")
    p.add_argument("--audio-start", type=float, default=0)
    p.add_argument("--audio-end", type=float)
    p.add_argument("--analyze-music", action="store_true", help="Detect beats in selected excerpt")
    p.add_argument("--duration", type=int, default=60, help="30 to 300 seconds")
    p.add_argument("--style", default=None, help="Style slug")
    p.add_argument("--dynamic-mix", action="store_true", help="Auto mix cinematic, energetic, fast cuts and emotional")
    p.add_argument("--mix-energy", type=int, default=75, help="Mix energy 0-100")
    p.add_argument("--auto-speed", action="store_true", help="Plan slow motion and speed ramps; not rendered or exported as effects yet")
    p.add_argument("--section-energy", help='JSON file of per-category energy values, e.g. {"drone":25,"dancing":95}')
    p.add_argument("--styles-dir", default="my-styles")
    p.add_argument("--xml", default="recap.xml")
    p.add_argument("--plan", default="edit-plan.json")
    args = parser.parse_args()
    if args.command == "scan":
        data = scan(args.folder)
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Found {len(data)} clips: {args.output}")
    elif args.command == "preview-audio":
        from .music import preview_audio
        preview_audio(args.music, args.audio_start, args.audio_end)
    elif args.command == "beats":
        data = detect_beats(args.music, start=args.audio_start, end=args.audio_end)
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Detected {len(data)} beats: {args.output}")
    elif args.command == "analyze":
        from .analysis_worker import analyze_folder
        data = analyze_folder(args.folder, max_clips=args.max_clips)
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Generated {len(data)} candidates: {args.output}")
    elif args.command == "select-shots":
        from .auto_selection import select_shots, selection_report
        candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
        selected = select_shots(candidates, min_confidence=args.min_confidence,
                                max_per_category=args.max_per_category)
        Path(args.output).write_text(json.dumps(selected, indent=2), encoding="utf-8")
        report = selection_report(selected)
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Selected {len(selected)} non-overlapping shots: {args.output}")
        print(json.dumps(report, indent=2))
    elif args.command == "render":
        from .render import render_file
        print(f"Rendered: {render_file(args.plan, args.output, args.music, args.audio_start, args.titles)}")
    elif args.command == "styles":
        from .styles import PRESETS
        print("\\n".join(f"{slug}: {style.name}" for slug, style in PRESETS.items()))
    elif args.command == "learn-style":
        from .style_learning import learn_style
        from .styles import save_style
        style, report = learn_style(args.references, args.slug, args.name, base=args.base)
        path = save_style(style, args.directory)
        print(f"Saved {path}")
        print(json.dumps(report, indent=2))
    else:
        from .styles import load_style
        shots = [Shot.from_dict(x) for x in json.loads(Path(args.shots).read_text(encoding="utf-8"))]
        if args.audio_end is not None:
            from .music import AudioRange
            selection = AudioRange(args.audio_start, args.audio_end).validate()
            if selection.duration < args.duration:
                parser.error("Audio selection must be at least as long as video duration")
        elif args.audio_start != 0:
            parser.error("--audio-end is required with --audio-start")
        if (args.audio_start != 0 or args.audio_end is not None) and not args.music:
            parser.error("Audio range requires --music")
        if args.analyze_music and not args.music:
            parser.error("--analyze-music requires --music")
        if args.analyze_music and args.beats:
            parser.error("Choose --beats or --analyze-music")
        beat_times = (detect_beats(args.music, start=args.audio_start, end=args.audio_end) if args.analyze_music else json.loads(Path(args.beats).read_text(encoding="utf-8")) if args.beats else [])
        style = load_style(args.style, args.styles_dir) if args.style else None
        from .dynamic_mix import DynamicMix
        mix = DynamicMix(energy=args.mix_energy) if args.dynamic_mix else None
        if mix is not None and style is not None:
            parser.error("Choose --style or --dynamic-mix, not both")
        section_energy = json.loads(Path(args.section_energy).read_text(encoding="utf-8")) if args.section_energy else None
        result = plan(shots, beat_times, duration=args.duration, style=style, mix=mix, section_energy=section_energy, auto_speed=args.auto_speed)
        Path(args.plan).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Plan: {args.plan}")
        print(f"Premiere XML candidate: {export(result, args.xml, args.music, audio_start=args.audio_start, audio_end=args.audio_end)}")
if __name__ == "__main__":
    main()
