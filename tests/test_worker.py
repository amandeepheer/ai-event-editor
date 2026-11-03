from ai_event_editor.analysis_worker import sample_times

def test_empty_video():
    assert sample_times(0) == []

def test_short_video():
    times = sample_times(2)
    assert len(times) == 1
    assert 0 <= times[0] < 2

def test_long_video():
    times = sample_times(10)
    assert len(times) == 3
    assert all(0 <= t < 10 for t in times)
