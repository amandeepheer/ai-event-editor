"""Contract tests exercise Python and the actual panel validator with the same plans."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import pytest
from ai_event_editor.edit_plan import validate_plan, preflight_plan
from ai_event_editor.planner import plan, ORDER, Shot

ROOT = Path(__file__).resolve().parents[1]


def base():
    return {"fps": 25, "duration_frames": 50, "segments": [
        {"path": "camera.mp4", "duration_frames": 25, "source_in_frame": 50},
        {"path": "drone.mp4", "duration_frames": 25, "source_in_seconds": 0.4}]}


def cases():
    valid = base()
    result = [("legacy", valid, True)]
    versioned = validate_plan(valid)
    result.append(("versioned", versioned, True))
    mixed = deepcopy(versioned)
    mixed['segments'][0]['source_fps'] = 50
    mixed['segments'][1]['source_fps'] = 29.97
    result.append(("mixed-source-fps", mixed, True))
    decimal = deepcopy(versioned)
    decimal['schema_version'] = 1.0
    decimal['segments'][0]['duration_frames'] = 25.0
    result.append(("json-integral-number", decimal, True))
    speed = deepcopy(versioned)
    speed['segments'][0]['speed_effect'] = {'kind': 'slow_motion', 'speed': 0.5}
    result.append(("speed-metadata", speed, True))
    edits = [
        ("version", ('schema_version',), 2),
        ("boolean-version", ('schema_version',), True),
        ("boolean-fps", ('fps',), True),
        ("zero-fps", ('fps',), 0),
        ("bad-total", ('duration_frames',), 49),
        ("boolean-total", ('duration_frames',), True),
        ("seconds-mismatch", ('duration_seconds',), 3),
        ("gap", ('segments', 1, 'timeline_start'), 26),
        ("overlap", ('segments', 1, 'timeline_start'), 24),
        ("negative-source", ('segments', 0, 'source_in_seconds'), -1),
        ("conflicting-offset", ('segments', 0, 'source_in_seconds'), 3),
        ("zero-length", ('segments', 0, 'duration_frames'), 0),
        ("fractional-length", ('segments', 0, 'duration_frames'), 0.5),
        ("duplicate-id", ('segments', 1, 'id'), 'clip-00001'),
        ("null-id", ('segments', 1, 'id'), None),
        ("empty-path", ('segments', 0, 'path'), ' '),
        ("bad-source-fps", ('segments', 0, 'source_fps'), 0),
        ("short-source", ('segments', 0, 'source_end_seconds'), 2.5),
        ("unknown-effect", ('segments', 0, 'speed_effect'), {'kind': 'magic'}),
        ("normal-with-speed", ('segments', 0, 'speed_effect'), {'kind': 'normal', 'speed': 2}),
        ("negative-speed", ('segments', 0, 'speed'), -1),
    ]
    for name, keys, value in edits:
        item = deepcopy(versioned)
        target = item
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        result.append((name, item, False))
    return result


@pytest.mark.parametrize('name,value,valid', cases(), ids=lambda x: x if isinstance(x, str) else None)
def test_python_contract(name, value, valid):
    original = deepcopy(value)
    if valid:
        normalized = validate_plan(value)
        assert normalized['schema_version'] == 1
        assert normalized['segments'][0]['source_in_seconds'] == 2
    else:
        with pytest.raises(ValueError):
            validate_plan(value)
    assert value == original


def test_panel_python_parity():
    # Node is required in CI; no mocked validator or conditional skip.
    script = r'''
const {validatePlan, preflightPlan} = require('./premiere-plugin/edit-plan.js');
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));
console.log(JSON.stringify(cases.map(([name, value]) => {
  try { return {name, plan: validatePlan(value), report: preflightPlan(value)}; }
  catch (error) { return {name, invalid: true}; }
})));
'''
    samples = cases()
    proc = subprocess.run(['node', '-e', script], input=json.dumps(samples),
                          text=True, capture_output=True, cwd=ROOT, check=True)
    results = json.loads(proc.stdout)
    for (name, value, valid), result in zip(samples, results):
        assert result['name'] == name
        assert ('invalid' not in result) == valid, name
        if valid:
            assert result['plan'] == validate_plan(value), name
            assert result['report'] == preflight_plan(value), name


@pytest.mark.parametrize('value', [None, [], True, {}, {'fps': float('nan')},
                                     {'fps': float('inf')}])
def test_invalid_root_and_nonfinite(value):
    with pytest.raises(ValueError):
        validate_plan(value)


def test_generated_plans_have_stable_ids_and_source_seconds():
    shots = [Shot(f'{cat}-{n}.mp4', cat, 2, 7, fps=50) for cat in ORDER for n in range(6)]
    first = plan(shots, [])
    assert first == plan(shots, [])
    assert len({s['id'] for s in first['segments']}) == len(first['segments'])
    assert all(s['source_in_seconds'] == 2 and s['source_fps'] == 50 for s in first['segments'])
    assert validate_plan(first) == first


def test_preflight_reports_unsupported_speed():
    value = base()
    value['segments'][0]['speed'] = 2
    report = preflight_plan(value)
    assert not report['standalone_supported']
    assert report['unsupported_speed_clips'] == ['clip-00001']


def test_cli_preflight(tmp_path):
    path = tmp_path / 'plan.json'
    path.write_text(json.dumps(base()))
    import sys
    result = subprocess.run([sys.executable, '-m', 'ai_event_editor.cli', 'validate-plan', str(path)],
                            text=True, capture_output=True, check=True, cwd=ROOT)
    assert json.loads(result.stdout)['clips'] == 2
    path.write_text('{}')
    result = subprocess.run([sys.executable, '-m', 'ai_event_editor.cli', 'validate-plan', str(path)],
                            text=True, capture_output=True, cwd=ROOT)
    assert result.returncode != 0
    assert 'Traceback' not in result.stderr


@pytest.mark.parametrize('bad', ['gap', 'speed', 'unknown-version'])
def test_render_rejects_before_subprocess(tmp_path, monkeypatch, bad):
    from ai_event_editor.render import render
    value = validate_plan(base())
    if bad == 'gap':
        value['segments'][1]['timeline_start'] += 1
    elif bad == 'speed':
        value['segments'][0]['speed'] = 2
    else:
        value['schema_version'] = 99
    def unexpected(*args, **kwargs):
        pytest.fail('Invalid plan started FFmpeg')
    monkeypatch.setattr('ai_event_editor.render.subprocess.run', unexpected)
    with pytest.raises(ValueError):
        render(value, tmp_path / 'out.mp4')
    assert not (tmp_path / 'out.mp4').exists()


def test_mixed_fps_nonzero_source_render(tmp_path):
    import hashlib
    import shutil
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('FFmpeg and FFprobe required')
    from ai_event_editor.render import render
    sources = [tmp_path / '50fps.mp4', tmp_path / '30fps.mp4']
    for source, fps in zip(sources, [50, 30]):
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                        '-f', 'lavfi', '-i', f'testsrc2=s=160x90:r={fps}:d=3',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
    value = base()
    for segment, path, fps in zip(value['segments'], sources, [50, 30]):
        segment['path'] = str(path)
        segment['source_fps'] = fps
    destination = tmp_path / 'highlight.mp4'
    render(value, destination, width=160, height=90)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                            '-show_entries', 'stream=nb_frames,r_frame_rate,duration',
                            '-of', 'json', str(destination)], text=True, capture_output=True, check=True)
    stream = json.loads(probe.stdout)['streams'][0]
    assert int(stream['nb_frames']) == 50
    assert stream['r_frame_rate'] == '25/1'
    assert float(stream['duration']) == pytest.approx(2, abs=.04)
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources] == hashes
