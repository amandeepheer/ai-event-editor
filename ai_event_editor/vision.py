"""Optional local zero-shot image classification using transformers.

First run downloads model weights from Hugging Face. Subsequent runs use
the local model cache. Images are not uploaded by this module.
"""
from __future__ import annotations
from pathlib import Path

PROMPTS = {
    "drone": "aerial drone view of an outdoor event or venue",
    "stalls": "food or merchandise stalls at a festival",
    "performance": "performers on a stage at a cultural event",
    "dancing": "people dancing at a celebration",
    "crowd": "audience members watching an event",
    "finale": "exciting celebration finale with performers and lights",
}

def classify_image(image_path: str, model_name: str = "openai/clip-vit-base-patch32") -> dict:
    """Return predicted category and per-category scores, not guaranteed accuracy."""
    try:
        import torch
        from PIL import Image
        from transformers import CLIPModel, CLIPProcessor
    except ImportError as exc:
        raise RuntimeError('Install vision extras: pip install ".[vision]"') from exc
    if not Path(image_path).is_file():
        raise FileNotFoundError(image_path)
    model = CLIPModel.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device).eval()
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    labels = list(PROMPTS)
    inputs = processor(text=[PROMPTS[k] for k in labels], images=image, return_tensors="pt", padding=True)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        scores = model(**inputs).logits_per_image.softmax(dim=1)[0].cpu().tolist()
    values = dict(zip(labels, (round(float(x), 5) for x in scores)))
    label = max(values, key=values.get)
    return {"category": label, "confidence": values[label], "scores": values, "model": model_name}
