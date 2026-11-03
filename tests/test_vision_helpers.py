import pytest
from ai_event_editor.vision import PROMPTS
from ai_event_editor.frame_sampling import extract_frame

def test_prompt_categories():
    assert set(PROMPTS) == {"drone", "stalls", "performance", "dancing", "crowd", "finale"}

def test_bad_frame_timestamp():
    with pytest.raises(ValueError):
        extract_frame("missing.mp4", -1, "frame.jpg")

def test_missing_media():
    with pytest.raises(FileNotFoundError):
        extract_frame("missing.mp4", 1, "frame.jpg")
