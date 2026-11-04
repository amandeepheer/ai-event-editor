"""UI-independent local setup, shot review, music analysis and edit creation."""
from array import array
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from math import isfinite, sqrt
from pathlib import Path
import subprocess
import sys
from .media import probe
from .planner import Shot, plan, ORDER
from .styles import load_style
from .music import AudioRange

PACING = {'Calm': 25, 'Balanced': 50, 'Energetic': 85}
DECISIONS = ('keep', 'reject', 'must_include')

@dataclass(frozen=True)
class Setup:
    duration: int = 60
    style: str = 'energetic-event'
    pacing: str = 'Balanced'
    music: str = ''
    audio_start: float = 0
    audio_end: float | None = None

    def validate(self):
        if isinstance(self.duration, bool) or not isinstance(self.duration, int) or not 30 <= self.duration <= 300:
            raise ValueError('Choose a whole duration from 30 to 300 seconds')
        if self.pacing not in PACING:
            raise ValueError('Choose Calm, Balanced or Energetic pacing')
        load_style(self.style)
        if not isinstance(self.audio_start, (int, float)) or isinstance(self.audio_start, bool) or not isfinite(self.audio_start) or self.audio_start < 0:
            raise ValueError('Music start must be finite and nonnegative')
        if self.music:
            if not Path(self.music).is_file():
                raise FileNotFoundError(self.music)
            end = self.audio_end if self.audio_end is not None else self.audio_start+self.duration
            selection = AudioRange(self.audio_start, end).validate()
            if selection.duration + 1e-7 < self.duration:
                raise ValueError('Music excerpt is shorter than the requested edit')
            info = probe(self.music)
            if not any(s.get('codec_type') == 'audio' for s in info['streams']):
                raise ValueError('Selected music file has no audio stream')
            if end > info['duration'] + 0.04:
                raise ValueError('Music excerpt extends beyond the music file')
        elif self.audio_start != 0 or self.audio_end is not None:
            raise ValueError('Choose a music file before setting an excerpt')
        return self


def prepare_footage(paths, cache_dir, use_ai=False, progress=None, thumbnail_format="ppm"):
    """Default: honest unranked four-second windows, no model/network required.

    Optional CLIP uses ONLY already cached model weights. Failed files are
    reported individually; thumbnail failure never silently rejects a moment.
    """
    from .analysis_worker import analyze_media, source_fps, VisionWorker
    if thumbnail_format not in ("ppm", "png"):
        raise ValueError("Unsupported thumbnail format")
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    media, errors = [], []
    for index, path in enumerate(dict.fromkeys(str(Path(p).expanduser().resolve()) for p in paths)):
        if progress:
            progress(f'Inspecting clip {index+1}: {Path(path).name}')
        try:
            info = probe(path)
            if not any(s.get('codec_type') == 'video' for s in info['streams']) or not isfinite(info['duration']) or info['duration'] <= 0:
                raise ValueError('No usable video stream')
            media.append(info)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append(f'{Path(path).name}: {error}')
    if use_ai:
        if progress:
            progress('Analyzing locally with cached CLIP model…')
        from .ai_runtime import ready,analyze as managed_analyze
        observations = (managed_analyze(media) if ready() else analyze_media(media, VisionWorker(local_files_only=True))) if media else []
    else:
        observations = []
        for clip in media:
            for index in range(int((clip['duration']-0.000001)//4)+1):
                start, end = index*4.0, min(clip['duration'], (index+1)*4.0)
                if end-start >= .5:
                    observations.append(dict(path=clip['path'], start=start, end=end,
                        category='performance', quality=.5, confidence=0, fps=source_fps(clip),
                        model='manual-review', review_required=True))
    candidates = []
    for index, candidate in enumerate(observations):
        if progress:
            progress(f'Preparing moment {index+1}/{len(observations)}')
        identifier = hashlib.sha256(f"{candidate['path']}\0{candidate['start']:.6f}\0{candidate['end']:.6f}".encode()).hexdigest()[:20]
        thumb = cache / (identifier+'.'+thumbnail_format)
        warning = None
        if not thumb.exists():
            try:
                subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-ss', str((candidate['start']+candidate['end'])/2), '-i', candidate['path'],
                    '-frames:v', '1', '-vf', 'scale=160:90:force_original_aspect_ratio=decrease,pad=160:90:(ow-iw)/2:(oh-ih)/2',
                    str(thumb)], check=True, capture_output=True)
            except (OSError, subprocess.SubprocessError):
                warning = 'Thumbnail unavailable; preview the source before deciding'
        candidates.append({**candidate, 'id': identifier, 'decision': 'keep',
                           'thumbnail': str(thumb) if thumb.is_file() else None,
                           'warning': warning})
    return {'candidates': candidates, 'errors': errors,
            'analysis': 'Cached local CLIP suggestions' if use_ai else 'Unranked windows — review and label moments manually'}


def reviewed_shots(candidates):
    """Pins override quality ranking and are never silently dropped by overlap filtering."""
    if not isinstance(candidates, list) or any(not isinstance(c, dict) for c in candidates):
        raise ValueError("Candidates must be a list of shot objects")
    selected = []
    ids = set()
    for c in candidates:
        if c.get('decision') not in DECISIONS:
            raise ValueError('Unknown shot decision')
        if not isinstance(c.get('id'), str) or not c['id'] or c['id'] in ids:
            raise ValueError('Shot IDs must be unique')
        ids.add(c['id'])
        if c['decision'] != 'reject':
            selected.append(Shot.from_dict({**c, 'must_include': c['decision'] == 'must_include'}))
    return selected


def coverage(candidates):
    shots = reviewed_shots(candidates)
    counts = {cat: sum(s.category == cat for s in shots) for cat in ORDER}
    return {'kept': len(shots), 'must_include': sum(s.must_include for s in shots),
            'counts': counts, 'missing_categories': [c for c, n in counts.items() if not n],
            'available_seconds': round(sum(s.end-s.start for s in shots), 2)}


def analyze_music(path, start, duration):
    """Bounded PCM RMS/onset heuristic, not semantic music or accurate BPM analysis."""
    AudioRange(start, start+duration).validate()
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', str(start),
               '-i', str(path), '-t', str(duration), '-vn', '-ac', '1', '-ar', '8000', '-f', 's16le', 'pipe:1']
    result = subprocess.run(command, capture_output=True, check=True)
    samples = array('h')
    samples.frombytes(result.stdout)
    if sys.byteorder != 'little':
        samples.byteswap()
    if len(samples) < duration*8000-800:
        raise ValueError('Decoded music excerpt is shorter than the requested edit')
    size = 2000  # 250ms windows; at most 1200 windows for a five-minute edit.
    rms = [sqrt(sum(v*v for v in samples[i:i+size])/len(samples[i:i+size])) for i in range(0, len(samples), size)]
    peak = max(rms, default=0)
    energies = [r/peak if peak else 0 for r in rms]
    envelope = [{'time': round(i*.25, 3), 'energy': round(e, 5)} for i, e in enumerate(energies)]
    onsets, last = [], -1
    for i in range(1, len(energies)-1):
        t = i*.25
        if energies[i] > .15 and energies[i] > energies[i-1]*1.15 and energies[i] >= energies[i+1] and t-last >= .4:
            onsets.append(t)
            last = t
    return {'beats': onsets, 'energy': envelope, 'method': 'Local RMS/onset heuristic; no BPM guarantee'}


def create_edit(candidates, setup: Setup):
    from dataclasses import replace
    setup.validate()
    shots = reviewed_shots(candidates)
    style = load_style(setup.style)
    factor = {'Calm': 1.5, 'Balanced': 1, 'Energetic': .65}[setup.pacing]
    style = replace(style, cut_seconds=max(.5, min(15, style.cut_seconds*factor)))
    music = analyze_music(setup.music, setup.audio_start, setup.duration) if setup.music else None
    result = plan(shots, music['beats'] if music else [], duration=setup.duration, style=style,
                  music_energy=music['energy'] if music else None)
    result['pacing'] = setup.pacing
    result['coverage'] = coverage(candidates)
    if music:
        result['audio'] = {'path': str(Path(setup.music).expanduser().resolve()),
            'start_seconds': setup.audio_start, 'duration_seconds': setup.duration}
        result['music_analysis'] = music['method']
    return result


def save_session(path, candidates, setup):
    from dataclasses import asdict
    data = {'session_version': 1, 'setup': asdict(setup), 'candidates': deepcopy(candidates)}
    reviewed_shots(candidates)
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def load_session(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('session_version') != 1:
        raise ValueError('Unsupported review session')
    reviewed_shots(data['candidates'])
    setup = Setup(**data['setup'])
    return data['candidates'], setup
