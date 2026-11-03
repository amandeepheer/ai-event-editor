import pytest
from ai_event_editor.titles import validate_titles, filter_chain

@pytest.mark.parametrize("position", [
    "top-left", "top", "top-right", "left", "center", "right",
    "bottom-left", "bottom", "bottom-right"])
def test_nine_positions(position):
    result = validate_titles([{"text": "Event", "start": 0, "end": 3, "position": position}], 5)
    assert result[0]["position"] == position

@pytest.mark.parametrize("animation", ["none", "fade", "zoom", "slide-left", "slide-right", "pop"])
def test_animation_presets(animation, tmp_path):
    title = {"text": "Event", "start": 0, "end": 3, "animation": animation}
    assert "drawtext=" in filter_chain([title], tmp_path, 5)

def test_manual_adjustments_and_lock():
    result = validate_titles([{"text": "Event", "start": 1, "end": 4, "x": 27.5,
                              "y": 68, "opacity": 60, "animation_duration": 1.2,
                              "locked": True}], 5)[0]
    assert (result["x"], result["y"], result["opacity"], result["locked"]) == (27.5, 68, 60, True)

@pytest.mark.parametrize("extra", [{"x": 101}, {"y": -1}, {"opacity": 110},
                                    {"animation_duration": 0}, {"animation": "unknown"}])
def test_invalid_manual_controls(extra):
    with pytest.raises(ValueError):
        validate_titles([{"text": "Event", "start": 0, "end": 2, **extra}], 5)
