"""User decisions, flexible coverage, music pacing and real local workflow tests."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from ai_event_editor.workflow import (Setup, create_edit, prepare_footage, reviewed_shots,
    coverage, save_session, load_session, analyze_music)
from ai_event_editor.planner import Shot, plan


def moments(count=20):
    return [dict(id=f'shot-{i}',path='camera.mp4',start=i*4,end=(i+1)*4,
                 category='performance',quality=.5,fps=50,decision='keep') for i in range(count)]


def test_single_category_and_short_category_redistribution():
    result = create_edit(moments(), Setup(duration=30))
    assert result['duration_frames'] == 750
    assert 'crowd' in result['missing_categories']
    assert all(s['category']=='performance' for s in result['segments'])
    data = moments()
    data[0]['category'] = 'drone'
    result = create_edit(data, Setup(duration=60))
    assert sum(s['duration_frames'] for s in result['segments'] if s['category']=='drone') <= 100
    assert result['duration_frames'] == 1500


def test_reject_never_used_pin_survives_low_quality_and_short_duration():
    data = moments(40)
    data[0]['decision'] = 'reject'
    data[-1].update(decision='must_include',quality=0)
    result = create_edit(data, Setup(duration=30))
    ids = {s['shot_id'] for s in result['segments']}
    assert 'shot-0' not in ids
    assert 'shot-39' in ids
    assert any(s['must_include'] for s in result['segments'])


def test_multiple_pins_with_music_reserves_every_pin():
    shots = [Shot('camera.mp4','performance',i*5,(i+1)*5, id=str(i),must_include=True) for i in range(10)]
    result = plan(shots,[i*.5 for i in range(60)],duration=30,
                  music_energy=[{'time':0,'energy':0}])
    assert {s['shot_id'] for s in result['segments']} == {str(i) for i in range(10)}
    assert result['duration_frames']==750


def test_conflicting_pins_are_reported():
    data = moments()
    data[0]['decision'] = data[1]['decision'] = 'must_include'
    data[1]['start'] = 1
    with pytest.raises(ValueError, match='overlap'):
        create_edit(data, Setup(duration=30))


def test_not_enough_footage_and_rejected_all():
    with pytest.raises(ValueError,match='Insufficient unique footage'):
        create_edit(moments(2), Setup(duration=30))
    data = moments()
    for c in data: c['decision']='reject'
    with pytest.raises(ValueError,match='No kept footage'):
        create_edit(data, Setup(duration=30))


def test_source_ranges_never_repeat():
    result = create_edit(moments(),Setup(duration=60))
    spans = []
    for s in result['segments']:
        start = s['source_in_seconds']
        end = start+s['duration_frames']/result['fps']
        assert all(not(start<b and a<end-1e-7) for a,b in spans)
        spans.append((start,end))


def test_long_single_source_can_fill_edit_without_duplication():
    result = plan([Shot('a.mp4','crowd',0,60)],[],duration=60)
    assert result['duration_frames']==1500
    assert result['segments'][-1]['source_in_seconds']+result['segments'][-1]['duration_frames']/25==60


def test_pacing_changes_cut_count_without_effects():
    calm = create_edit(moments(), Setup(duration=30,pacing='Calm'))
    fast = create_edit(moments(), Setup(duration=30,pacing='Energetic'))
    assert len(fast['segments']) > len(calm['segments'])
    assert all(s['speed_effect']['kind']=='normal' for s in fast['segments'])


def test_louder_passages_shorten_cut_targets():
    shots=[Shot('camera.mp4','performance',0,60)]
    quiet=plan(shots,[],duration=30,music_energy=[{'time':0,'energy':0}])
    loud=plan(shots,[],duration=30,music_energy=[{'time':0,'energy':1}])
    assert len(loud['segments']) > len(quiet['segments'])


@pytest.mark.parametrize('patch', [{'duration':True},{'duration':29},{'duration':301},{'pacing':'Other'},
    {'audio_start':-1},{'audio_start':float('nan')},{'audio_end':10},{'style':'unknown'}])
def test_setup_invalid(patch):
    with pytest.raises((ValueError,FileNotFoundError)):
        replace(Setup(), **patch).validate()


@pytest.mark.parametrize('patch',[{'decision':'maybe'},{'id':None},{'start':float('nan')},
                                    {'fps':0},{'category':'magic'}])
def test_invalid_decisions_and_shots(patch):
    data=moments(); data[0].update(patch)
    with pytest.raises(ValueError): reviewed_shots(data)


def test_review_roundtrip(tmp_path):
    data=moments()
    data[2]['decision']='must_include'; data[3]['decision']='reject'
    original=deepcopy(data)
    path=tmp_path/'review.json'
    save_session(path,data,Setup(duration=30,pacing='Calm'))
    shots,setup=load_session(path)
    assert shots==original and data==original
    assert setup.duration==30 and setup.pacing=='Calm'
    assert coverage(shots)['must_include']==1
    assert coverage(shots)['kept']==19


def test_no_implicit_model_download(monkeypatch,tmp_path):
    import ai_event_editor.analysis_worker as worker
    calls=[]
    class CachedOnly:
        def __init__(self, **kwargs): calls.append(kwargs)
    monkeypatch.setattr(worker,'VisionWorker',CachedOnly)
    monkeypatch.setattr(worker,'analyze_media',lambda media,worker:[])
    monkeypatch.setattr('ai_event_editor.workflow.probe',lambda path:{'path':path,'duration':5,'streams':[{'codec_type':'video'}]})
    prepare_footage(['test.mp4'],tmp_path,use_ai=True)
    assert calls==[{'local_files_only':True}]


@pytest.fixture
def media(tmp_path):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('FFmpeg/FFprobe required')
    video=tmp_path/'event.mp4'; music=tmp_path/'music.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=160x90:r=25:d=36',
                    '-c:v','libx264','-preset','ultrafast',str(video)],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=40',str(music)],check=True)
    return video,music


def test_complete_local_workflow_without_handwritten_json(media,tmp_path):
    from ai_event_editor.render import render_file
    video,music=media
    originals=[hashlib.sha256(p.read_bytes()).hexdigest() for p in media]
    prepared=prepare_footage([video,video,tmp_path/'broken.mov'],tmp_path/'thumbs')
    assert len(prepared['errors'])==1
    assert len(prepared['candidates'])==9
    assert all(Path(c['thumbnail']).is_file() for c in prepared['candidates'])
    assert all(c['fps']==25 for c in prepared['candidates'])
    prepared['candidates'][0]['decision']='reject'
    prepared['candidates'][-1]['decision']='must_include'
    setup=Setup(duration=30,music=str(music),audio_start=5,audio_end=36)
    edit=create_edit(prepared['candidates'],setup)
    assert edit['audio']['start_seconds']==5
    assert edit['coverage']['must_include']==1
    assert prepared['candidates'][0]['id'] not in {s['shot_id'] for s in edit['segments']}
    path=tmp_path/'reviewed-edit.json'; path.write_text(json.dumps(edit))
    output=tmp_path/'highlight.mp4'
    render_file(path,output)
    result=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,nb_frames',
                           '-of','json',str(output)],check=True,capture_output=True,text=True)
    info=json.loads(result.stdout)
    assert float(info['format']['duration'])==pytest.approx(30,abs=.08)
    assert {s['codec_type'] for s in info['streams']}=={'audio','video'}
    assert next(s for s in info['streams'] if s['codec_type']=='video')['nb_frames']=='750'
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in media]==originals


def test_excerpt_bounds_and_silence(media,tmp_path):
    video,music=media
    with pytest.raises(ValueError,match='shorter'):
        Setup(duration=30,music=str(music),audio_end=20).validate()
    with pytest.raises(ValueError,match='beyond'):
        Setup(duration=30,music=str(music),audio_start=20).validate()
    result=analyze_music(str(music),5,30)
    assert len(result['energy'])==120
    assert all(0 <= b < 30 for b in result['beats'])
    silence=tmp_path/'silence.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','anullsrc=r=8000:cl=mono','-t','1',str(silence)],check=True)
    result=analyze_music(str(silence),0,1)
    assert result['beats']==[]
    assert all(e['energy']==0 for e in result['energy'])


def test_render_cannot_overwrite_source(media):
    from ai_event_editor.render import render
    video,music=media
    edit=plan([Shot(str(video),'performance',0,36)],[],duration=30)
    with pytest.raises(ValueError,match='overwrite'):
        render(edit,video)
