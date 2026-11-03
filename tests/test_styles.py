import pytest
from ai_event_editor.styles import Style, PRESETS, blend_styles, load_style, save_style
from ai_event_editor.style_learning import estimate_cut_lengths, learn_style

def test_six_presets():
    assert len(PRESETS) == 6
    for style in PRESETS.values():
        style.validate()

def test_save_load(tmp_path):
    style = PRESETS["wedding"]
    save_style(style, tmp_path)
    assert load_style("wedding", tmp_path) == style

def test_blend():
    mixed = blend_styles(PRESETS["cinematic"], PRESETS["social-reel"], 0.5, "hybrid", "Hybrid")
    assert 0.9 < mixed.cut_seconds < 4
    assert mixed.source == "blend"

def test_invalid_slug(tmp_path):
    with pytest.raises(ValueError):
        save_style(Style("../bad", "bad", "bad"), tmp_path)

def test_invalid_profile(tmp_path):
    (tmp_path / "custom.json").write_text('{"slug":"custom","name":"X","description":"X","cut_seconds":-1}')
    with pytest.raises(ValueError):
        load_style("custom", tmp_path)

def test_cut_lengths():
    assert estimate_cut_lengths(10, [2, 4, 9]) == [2, 2, 5, 1]

def test_learning_requires_video():
    with pytest.raises(ValueError):
        learn_style([], "example", "Example")
