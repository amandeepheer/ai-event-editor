from pathlib import Path
import subprocess
import pytest
from ai_event_editor.workflow import Setup
from ai_event_editor.instructions import interpret
from test_engine_service import running, request, wait


def test_read_only_project_panel_selection_without_timeline():
    root=Path(__file__).resolve().parents[1]
    subprocess.run(['node',str(root/'tests/project_media.cjs')],cwd=root,check=True)


def test_selected_pool_instruction_references_are_bounded():
    result=interpret('Use these clips and this music to make a one-minute energetic highlight',Setup(music='/song.wav'),[])
    assert not result['unsupported']
    assert result['setup']['duration']==60 and result['setup']['pacing']=='Energetic'
    assert interpret('Use these clips and this music',Setup(),[])['unsupported']
    assert interpret('Use all these clips',Setup(),[])['unsupported']  # No guarantee every source is used.
    assert interpret('Make this music louder',Setup(music='/song.wav'),[])['unsupported']


@pytest.mark.parametrize('paths',[[],['relative.mp4'],'/a.mp4',[True]])
def test_project_media_rejects_invalid_input(paths):
    with running() as (engine,port):
        assert request(port,'/v1/project-media',engine.token,{'paths':paths})[0]==400
        assert request(port,'/v1/project-media','wrong',{'paths':['/a.mp4']})[0]==401


def test_project_media_real_files_to_reviewed_plan(tmp_path):
    video=tmp_path/'event.mp4';music=tmp_path/'music.wav';bad=tmp_path/'notes.txt'
    bad.write_text('not video')
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=25:d=32',
                    '-c:v','libx264',str(video)],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=8000:duration=35',str(music)],check=True)
    before={p:p.read_bytes() for p in (video,music,bad)}
    with running() as (engine,port):
        code,job,_=request(port,'/v1/project-media',engine.token,{'paths':[str(video),str(music),str(video),str(bad)]})
        assert code==202
        result=wait(port,engine.token,job['job_id'])
        assert result['status']=='completed',result
        media=result['result']
        assert [v['path'] for v in media['videos']]==[str(video)]
        assert [a['path'] for a in media['audio']]==[str(music)]
        assert len(media['errors'])==1
        _,job,_=request(port,'/v1/prepare',engine.token,{'paths':[v['path'] for v in media['videos']]})
        prepared=wait(port,engine.token,job['job_id'])['result']
        _,job,_=request(port,'/v1/build',engine.token,{'session_id':prepared['session_id'],
            'setup':{'duration':30,'music':str(music)},'instruction':'Use these clips and this music to make a 30-second energetic highlight'})
        built=wait(port,engine.token,job['job_id'])
        assert built['status']=='completed',built
        plan=built['result']['plan']
        assert plan['duration_seconds']==30 and plan['audio']['path']==str(music)
        assert all(s['path']==str(video) for s in plan['segments'])
    assert before=={p:p.read_bytes() for p in before}


def test_audio_cover_art_is_not_footage(monkeypatch):
    monkeypatch.setattr('ai_event_editor.media.probe',lambda p:{'path':p,'duration':60,'streams':[
        {'codec_type':'video','disposition':{'attached_pic':1}},{'codec_type':'audio'}]})
    with running() as (engine,port):
        _,job,_=request(port,'/v1/project-media',engine.token,{'paths':['/song-with-cover.mp3']})
        result=wait(port,engine.token,job['job_id'])['result']
        assert not result['videos'] and len(result['audio'])==1
