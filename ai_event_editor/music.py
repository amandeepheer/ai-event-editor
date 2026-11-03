"""Non-destructive audio excerpt selection and optional beat detection."""
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import subprocess

@dataclass(frozen=True)
class AudioRange:
    start: float
    end: float

    def validate(self):
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x) for x in (self.start, self.end)):
            raise ValueError("Audio times must be finite numbers")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("Audio end must be greater than nonnegative start")
        return self

    @property
    def duration(self):
        return self.end - self.start

def detect_beats(path: str, start: float = 0, end: float | None = None) -> list[float]:
    """Return beat times relative to selected excerpt start."""
    try:
        import librosa
    except ImportError as err:
        raise RuntimeError('Install extras: pip install ".[media]"') from err
    if end is not None:
        selection = AudioRange(start, end).validate()
        audio, sr = librosa.load(path, sr=22050, mono=True, offset=selection.start, duration=selection.duration)
    else:
        if start < 0 or not isfinite(start):
            raise ValueError("Invalid audio start")
        audio, sr = librosa.load(path, sr=22050, mono=True, offset=start)
    if len(audio) == 0:
        raise ValueError("Selected audio range is empty")
    _, beats = librosa.beat.beat_track(y=audio, sr=sr, units="time", trim=False)
    return [float(t) for t in beats if float(t) >= 0]

def preview_audio(path: str, start: float, end: float, player: str = "ffplay") -> None:
    """Play selected excerpt without creating or altering an audio file."""
    selection = AudioRange(start, end).validate()
    if not Path(path).is_file():
        raise FileNotFoundError(path)
    subprocess.run([player, "-nodisp", "-autoexit", "-ss", str(selection.start),
                    "-t", str(selection.duration), path], check=True)
