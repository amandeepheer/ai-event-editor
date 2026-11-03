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
    p = sub.add_parser("beats")
    p.add_argument("music")
    p.add_argument("--output", default="beats.json")
    p = sub.add_parser("analyze")
    p.add_argument("folder")
    p.add_argument("--output", default="shot-candidates.json")
    p.add_argument("--max-clips", type=int, default=None)
    p = sub.add_parser("styles")
    p.add_argument("--directory", default="my-styles")
    p = sub.add_parser("learn-style")
    p.add_argument("slug")
    p.add_argument("name")
    p.add_argument("references", nargs="+")
    p.add_argument("--base", default="energetic-event")
    p.add_argument("--directory", default="my-styles")
    p = sub.add_parser("build")
    p.add_argument("shots")
    p.add_argument("--beats")
    p.add_argument("--music")
    p.add_argument("--duration", type=int, default=60, help="30 to 300 seconds")
    p.add_argument("--style", default=None, help="Style slug")
    p.add_argument("--dynamic-mix", action="store_true", help="Auto mix cinematic, energetic, fast cuts and emotional")
    p.add_argument("--mix-energy", type=int, default=75, help="Mix energy 0-100")
    p.add_argument("--styles-dir", default="my-styles")
    p.add_argument("--xml", default="recap.xml")
    p.add_argument("--plan", default="edit-plan.json")
    args = parser.parse_args()
    if args.command == "scan":
        data = scan(args.folder)
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Found {len(data)} clips: {args.output}")
    elif args.command == "beats":
        data = detect_beats(args.music)
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Detected {len(data)} beats: {args.output}")
    elif args.command == "analyze":
        from .analysis_worker import analyze_folder
        data = analyze_folder(args.folder, max_clips=args.max_clips)
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Generated {len(data)} candidates: {args.output}")
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
        beat_times = json.loads(Path(args.beats).read_text(encoding="utf-8")) if args.beats else []
        style = load_style(args.style, args.styles_dir) if args.style else None
        from .dynamic_mix import DynamicMix
        mix = DynamicMix(energy=args.mix_energy) if args.dynamic_mix else None
        if mix is not None and style is not None:
            parser.error("Choose --style or --dynamic-mix, not both")
        result = plan(shots, beat_times, duration=args.duration, style=style, mix=mix)
        Path(args.plan).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Plan: {args.plan}")
        print(f"Premiere XML candidate: {export(result, args.xml, args.music)}")
if __name__ == "__main__":
    main()
