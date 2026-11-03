# Local visual classification (experimental)

The first visual classifier is optional and uses CLIP. Install separately:

```powershell
pip install -e ".[vision]"
```

Call `ai_event_editor.vision.classify_image("frame.jpg")` from Python after extracting a representative frame using `ai_event_editor.frame_sampling.extract_frame`.

This initial implementation loads the model per call and is intended for proof-of-concept testing only; a batch worker that loads it once, classifies multiple frames, and aggregates per-shot results is needed before normal use. Classification scores are relative to the six prompts, **not calibrated probabilities**. A 'finale' label cannot be reliably inferred from a single frame and must be reviewed. Model weights download on first use. No original video is uploaded to an API by these modules. Do not assume any model is suitable for commercial use without checking its terms.

Future work: persistent model worker, automatic sampling per scene, confidence calibration, temporal motion analysis, manual override UI and robust source-frame-rate handling.
