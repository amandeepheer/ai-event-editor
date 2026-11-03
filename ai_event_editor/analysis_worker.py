"""Local batch video analyzer: load CLIP once and classify sampled frames.

Requires FFmpeg, ffprobe, and optional vision dependencies.
The categories are suggestions, not reliable semantic truth.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from .media import scan
from .frame_sampling import extract_frame
from .vision import PROMPTS

class VisionWorker:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise RuntimeError('Install vision dependencies: pip install ".[vision]"') from exc
        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device).eval()
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.labels = list(PROMPTS)
        self.model_name = model_name

    def classify(self, paths: list[str]) -> list[dict]:
        from PIL import Image
        if not paths:
            return []
        with self.torch.inference_mode():
            images = []
            for path in paths:
                with Image.open(path) as source:
                    images.append(source.convert("RGB"))
            inputs = self.processor(text=[PROMPTS[k] for k in self.labels],
                                    images=images, return_tensors="pt", padding=True)
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            scores = self.model(**inputs).logits_per_image.softmax(dim=1).cpu().tolist()
        results = []
        for row in scores:
            values = dict(zip(self.labels, (round(float(x), 5) for x in row)))
            category = max(values, key=values.get)
            results.append({"category": category, "confidence": values[category], "scores": values})
        return results

def sample_times(duration: float, interval: float = 4.0) -> list[float]:
    if duration <= 0:
        return []
    if interval <= 0:
        raise ValueError("interval must be positive")
    return [round(min((index + 0.5) * interval, duration / 2 if duration < interval else duration - 0.1), 3)
            for index in range(max(1, int((duration - 0.001) // interval) + 1))
            if index * interval < duration]

def analyze_folder(folder: str, max_clips: int | None = None, worker=None) -> list[dict]:
    if max_clips is not None and max_clips <= 0:
        raise ValueError("max_clips must be positive")
    media = scan(folder)
    if max_clips is not None:
        media = media[:max_clips]
    if not media:
        return []
    worker = worker if worker is not None else VisionWorker()
    candidates = []
    with TemporaryDirectory(prefix="event-editor-") as temp:
        for clip_index, clip in enumerate(media):
            duration = float(clip["duration"])
            times = sample_times(duration)
            paths = []
            for frame_index, timestamp in enumerate(times):
                path = str(Path(temp) / f"frame-{clip_index}-{frame_index}.jpg")
                try:
                    extract_frame(clip["path"], timestamp, path)
                    paths.append((timestamp, path))
                except Exception:
                    continue
            if not paths:
                continue
            labels = worker.classify([path for _, path in paths])
            for index, ((timestamp, _), result) in enumerate(zip(paths, labels)):
                # Non-overlapping candidate windows; the operator can adjust these later.
                start = max(0.0, timestamp - 1.5)
                end = min(duration, timestamp + 1.5)
                candidates.append({"path": clip["path"], "start": start, "end": end,
                                   "category": result["category"], "confidence": result["confidence"],
                                   "quality": 0.5, "model": getattr(worker, "model_name", "test-worker"),
                                   "review_required": True})
    return candidates
