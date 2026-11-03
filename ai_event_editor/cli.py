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
    p = sub.add_parser("build")
    p.add_argument("shots")
    p.add_argument("--beats")
    p.add_argument("--music")
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
    else:
        shots = [Shot.from_dict(x) for x in json.loads(Path(args.shots).read_text(encoding="utf-8"))]
        beat_times = json.loads(Path(args.beats).read_text(encoding="utf-8")) if args.beats else []
        result = plan(shots, beat_times)
        Path(args.plan).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Plan: {args.plan}")
        print(f"Premiere XML candidate: {export(result, args.xml, args.music)}")
if __name__ == "__main__":
    main()
