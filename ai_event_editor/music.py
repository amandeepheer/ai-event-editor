"""Optional local music beat detection."""
def detect_beats(path: str) -> list[float]:
    try:
        import librosa
    except ImportError as err:
        raise RuntimeError('Install extras: pip install ".[media]"') from err
    audio, sr = librosa.load(path, sr=22050, mono=True)
    _, beats = librosa.beat.beat_track(y=audio, sr=sr, units="time", trim=False)
    return [float(t) for t in beats if float(t) <= 60]
