"""Use the real HTTP server on an ephemeral loopback port, including auth boundaries."""
from contextlib import contextmanager
import json
from pathlib import Path
import secrets
import threading
import time
import urllib.request
import urllib.error
import pytest
from ai_event_editor.service import Engine, create_server

@contextmanager
def running():
    engine=Engine(secrets.token_urlsafe(32))
    server=create_server(engine,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield engine,server.server_port
    finally:server.shutdown();server.server_close();engine.close();thread.join()


def request(port,path,token,body=None,headers=None,method=None):
    data=json.dumps(body).encode() if body is not None else None
    values={'Authorization':'Bearer '+token}
    if body is not None:values['Content-Type']='application/json'
    values.update(headers or {})
    req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=data,headers=values,method=method)
    try:
        with urllib.request.urlopen(req,timeout=10) as result:return result.status,json.loads(result.read()),dict(result.headers)
    except urllib.error.HTTPError as result:return result.code,json.loads(result.read()),dict(result.headers)


def wait(port,token,identifier):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        status,job,_=request(port,'/v1/jobs/'+identifier,token)
        assert status==200
        if job['status']!='running':return job
        time.sleep(.02)
    pytest.fail('Local engine job did not finish')


def candidates(path='/a.mp4'):
    return [dict(id=str(i),path=path,start=i*4,end=(i+1)*4,category='performance',quality=.5,
                 decision='keep',fps=25,thumbnail=None,model='manual-review') for i in range(12)]


def seed(engine):
    engine.sessions['review']=candidates()
    return {'session_id':'review','setup':{'duration':30},'review':[],
            'instruction':'make a 30-second cinematic recap with energetic pacing'}


def test_health_auth_origin_and_rebinding():
    with running() as (engine,port):
        assert request(port,'/v1/health','wrong')[0]==401
        assert request(port,'/v1/health',engine.token,headers={'Origin':'https://evil.example'})[0]==403
        assert request(port,'/v1/health',engine.token,headers={'Host':'evil.example'})[0]==403
        code,result,headers=request(port,'/v1/health',engine.token,headers={'Origin':'null'})
        assert code==200 and result['api_version']==1
        assert headers['Access-Control-Allow-Origin']=='null'
        assert headers['Cache-Control']=='no-store'
        assert engine.token not in json.dumps(result)
        assert request(port,'/v1/health?token=bad',engine.token)[0]==400
        assert request(port,'/not-a-file',engine.token)[0]==404
        assert request(port,'/v1/jobs/missing',engine.token)[0]==404


def test_preflight_cors():
    with running() as (engine,port):
        code,_,headers=request(port,'/v1/build','',headers={'Origin':'null'},method='OPTIONS')
        assert code==200 and 'Authorization' in headers['Access-Control-Allow-Headers']
        assert request(port,'/v1/build','',headers={'Origin':'https://web.example'},method='OPTIONS')[0]==403


def test_panel_instruction_review_and_build_over_http():
    with running() as (engine,port):
        body=seed(engine)
        body['review']=[{'id':'0','decision':'reject'},{'id':'11','decision':'must_include'}]
        code,result,_=request(port,'/v1/interpret',engine.token,body)
        assert code==200 and not result['unsupported']
        assert result['setup']['pacing']=='Energetic'
        assert all(set(c)=={'id','decision','category'} for c in result['candidates'])
        code,result,_=request(port,'/v1/build',engine.token,body)
        assert code==202
        job=wait(port,engine.token,result['job_id'])
        assert job['status']=='completed',job
        plan=job['result']['plan']
        assert plan['duration_frames']==750
        assert '0' not in {c['shot_id'] for c in plan['segments']}
        assert '11' in {c['shot_id'] for c in plan['segments']}
        assert engine.sessions['review'][0]['decision']=='keep'  # Requests never mutate stored sources.


@pytest.mark.parametrize('patch',[
    {'review':[{'id':'0','path':'/secret.txt'}]},
    {'review':[{'id':'unknown','decision':'keep'}]},
    {'review':[{'id':'0'},{'id':'0'}]},
    {'review':[{'id':'0','decision':'unknown'}]},
    {'session_id':'expired'}, {'setup':{'unknown':42}},
])
def test_review_requests_cannot_inject_paths_or_invalid_decisions(patch):
    with running() as (engine,port):
        body=seed(engine);body.update(patch)
        assert request(port,'/v1/build',engine.token,body)[0]==400


def test_unsupported_instructions_never_start_build():
    with running() as (engine,port):
        body=seed(engine);body['instruction']='make a 30-second recap with slow motion'
        code,result,_=request(port,'/v1/build',engine.token,body)
        assert code==400 and 'Slow motion' in result['error']
        assert not engine.jobs


def test_background_failure_is_actionable_and_releases_busy_state():
    with running() as (engine,port):
        body=seed(engine);engine.sessions['review']=candidates()[:2]
        _,result,_=request(port,'/v1/build',engine.token,body)
        job=wait(port,engine.token,result['job_id'])
        assert job['status']=='failed' and 'Insufficient unique footage' in job['error']
        assert engine.active is None


def test_one_job_at_a_time_and_bounded_history():
    engine=Engine();release=threading.Event()
    try:
        job=engine.submit(lambda progress:release.wait(2))
        with pytest.raises(RuntimeError,match='busy'):engine.submit(lambda p:None)
        release.set();engine.worker.join()
        for _ in range(20):engine.submit(lambda p:{'ok':True});engine.worker.join()
        assert len(engine.jobs)<=16
    finally:release.set();engine.close()


def test_prepare_thumbnails_travel_as_data_not_public_file_routes(tmp_path,monkeypatch):
    png=tmp_path/'shot.png';png.write_bytes(b'PNG test payload')
    prepared=candidates(str(tmp_path/'camera.mp4'))
    for c in prepared:c['thumbnail']=str(png)
    monkeypatch.setattr('ai_event_editor.service.prepare_footage',lambda *args,**kwargs:{'candidates':prepared,'analysis':'test','errors':[]})
    with running() as (engine,port):
        code,result,_=request(port,'/v1/prepare',engine.token,{'paths':[str(tmp_path/'camera.mp4')]})
        assert code==202
        job=wait(port,engine.token,result['job_id'])
        assert job['status']=='completed'
        c=job['result']['candidates'][0]
        assert c['thumbnail_data'].startswith('data:image/png;base64,')
        assert 'thumbnail' not in c
        assert request(port,'/v1/files/'+str(png),engine.token)[0]==404


@pytest.mark.parametrize('body',[{'paths':[]},{'paths':['relative.mp4']},{'paths':[42]},{'paths':['/a.mp4'],'use_ai':'yes'}])
def test_prepare_input_bounds(body):
    engine=Engine()
    try:
        with pytest.raises(ValueError):engine.prepare(body)
    finally:engine.close()


def test_real_footage_to_reviewed_plan_through_http(tmp_path):
    import hashlib
    import shutil
    import subprocess
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):pytest.skip('FFmpeg required')
    source=tmp_path/'event.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=25:d=36',
                    '-c:v','libx264','-preset','ultrafast',str(source)],check=True)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    with running() as (engine,port):
        status,result,_=request(port,'/v1/prepare',engine.token,{'paths':[str(source)]})
        assert status==202
        job=wait(port,engine.token,result['job_id'])
        assert job['status']=='completed',job
        review=job['result']
        assert len(review['candidates'])==9
        assert all(c['thumbnail_data'].startswith('data:image/png;base64,iVBOR') for c in review['candidates'])
        patches=[{'id':review['candidates'][0]['id'],'decision':'reject'},
                 {'id':review['candidates'][-1]['id'],'decision':'must_include'}]
        body={'session_id':review['session_id'],'setup':{},'review':patches,
              'instruction':'Make a 30-second cinematic recap with energetic pacing'}
        status,result,_=request(port,'/v1/build',engine.token,body)
        assert status==202
        built=wait(port,engine.token,result['job_id'])
        assert built['status']=='completed',built
        plan=built['result']['plan']
        assert plan['duration_frames']==750
        assert plan['pacing']=='Energetic' and plan['style']=='cinematic'
        assert patches[0]['id'] not in {s['shot_id'] for s in plan['segments']}
        assert patches[1]['id'] in {s['shot_id'] for s in plan['segments']}
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest


def test_optional_local_interpretation_runs_as_polled_job(monkeypatch):
    from ai_event_editor.instructions import interpret
    monkeypatch.setattr('ai_event_editor.local_language.interpret_local',lambda text,setup,shots:interpret('30 seconds calm',setup,shots))
    with running() as (engine,port):
        body=seed(engine);body['instruction']='a relaxed feeling';body['instruction_mode']='ollama'
        code,result,_=request(port,'/v1/interpret-local',engine.token,body)
        assert code==202
        job=wait(port,engine.token,result['job_id'])
        assert job['status']=='completed'
        assert job['result']['setup']['pacing']=='Calm'
        code,result,_=request(port,'/v1/build',engine.token,body)
        assert code==202
        assert wait(port,engine.token,result['job_id'])['result']['plan']['pacing']=='Calm'
