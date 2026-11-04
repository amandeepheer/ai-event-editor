from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import pytest
from ai_event_editor import ai_runtime,local_language
from ai_event_editor.workflow import Setup


def candidates():
    return [dict(id=str(i),path='local.mp4',category='crowd',start=i*4,end=(i+1)*4,quality=.5,decision='keep') for i in range(12)]


def patch(**changes):
    return {'duration':None,'pacing':None,'style':None,'include_categories':[],
            'exclude_categories':[],'unsupported_requests':[],**changes}


def response(value):return BytesIO(json.dumps({'message':{'content':json.dumps(value)}}).encode())


def test_local_language_schema_applies_only_valid_changes(monkeypatch):
    calls=[]
    def request(path,body,timeout):
        calls.append((path,body));return response(patch(duration=90,pacing='Calm',style='wedding',include_categories=['crowd']))
    monkeypatch.setattr(local_language,'request',request)
    data=candidates();data[0]['decision']='reject';before=deepcopy(data)
    report=local_language.interpret_local('Give it a relaxed feeling and focus on guests',Setup(),data)
    assert not report['unsupported']
    assert report['setup']['duration']==90 and report['setup']['pacing']=='Calm'
    assert report['candidates'][0]['decision']=='reject'
    assert any(c['decision']=='must_include' for c in report['candidates'])
    assert data==before
    body=calls[0][1]
    assert body['model']=='qwen3:8b' and body['stream'] is False and body['keep_alive']==0
    assert body['format']['additionalProperties'] is False
    assert 'local.mp4' not in json.dumps(body)


@pytest.mark.parametrize('text',['Make a 60-second recap','add slow motion','Add titles please','include dancing','calm energetic'])
def test_clear_rules_and_unsupported_actions_never_need_model(monkeypatch,text):
    monkeypatch.setattr(local_language,'request',lambda *a,**k:pytest.fail('Unnecessary model call'))
    local_language.interpret_local(text,Setup(),candidates())


@pytest.mark.parametrize('value',[
    patch(duration=True),patch(duration=20),patch(duration=300.5),patch(style='delete-files'),
    patch(pacing='Ultra'),patch(include_categories=['people']),patch(include_categories=['crowd','crowd']),
    patch(include_categories=['crowd'],exclude_categories=['crowd']),patch(unsupported_requests=[42]),
    {**patch(),'execute':'remove files'},[],{},
])
def test_model_cannot_return_unknown_actions(value):
    with pytest.raises(ValueError):local_language.validate_patch(value)


def test_model_unavailable_blocks_instead_of_silent_fallback(monkeypatch):
    def fail(*args,**kwargs):raise OSError('not running')
    monkeypatch.setattr(local_language,'request',fail)
    with pytest.raises(ValueError,match='turn off local language'):
        local_language.interpret_local('a relaxed feeling',Setup(),candidates())


def test_unsupported_and_empty_model_output_are_disclosed(monkeypatch):
    monkeypatch.setattr(local_language,'request',lambda *a,**k:response(patch(unsupported_requests=['Subject tracking is unavailable'])))
    assert local_language.interpret_local('follow the main performer',Setup(),candidates())['unsupported']
    monkeypatch.setattr(local_language,'request',lambda *a,**k:response(patch()))
    assert local_language.interpret_local('make it amazing',Setup(),candidates())['unsupported']


def test_only_loopback_known_endpoints(monkeypatch):
    with pytest.raises(ValueError):local_language.request('https://elsewhere.example')
    with pytest.raises(ValueError):local_language.NoRedirect().redirect_request(None,None,302,None,None,'https://elsewhere.example')
    calls=[]
    class Opener:
        def open(self,request,timeout):calls.append(request.full_url);return BytesIO(b'{}')
    monkeypatch.setattr(local_language.urllib.request,'build_opener',lambda *handlers:Opener())
    local_language.request('/api/tags')
    assert calls==['http://127.0.0.1:11434/api/tags']


def test_language_model_presence_is_exact_local_tag(monkeypatch):
    monkeypatch.setattr(local_language,'request',lambda *a,**k:BytesIO(b'{"models":[{"name":"qwen3:8b-cloud"}]}'))
    assert not local_language.model_available()
    monkeypatch.setattr(local_language,'request',lambda *a,**k:BytesIO(b'{"models":[{"name":"qwen3:8b"}]}'))
    assert local_language.model_available()


def seed_runtime(tmp_path,monkeypatch):
    root=tmp_path/'AIAddon';(root/'python').mkdir(parents=True)
    (root/'python'/'python.exe').touch();(root/'wheels').mkdir();(root/'wheels'/'pip-test.whl').touch()
    source=root/'source'/'ai_event_editor';source.mkdir(parents=True);(source/'ai_worker.py').touch()
    state=tmp_path/'state.json'
    monkeypatch.setattr(ai_runtime,'addon_root',lambda:root)
    monkeypatch.setattr(ai_runtime,'state_file',lambda:state)
    return root,state


def test_readiness_requires_completed_verified_runtime(tmp_path,monkeypatch):
    root,state=seed_runtime(tmp_path,monkeypatch)
    assert not ai_runtime.ready()
    state.write_text(json.dumps({'version':1,'root':str(root),'device':'cpu'}))
    assert ai_runtime.ready()
    (root/'installing').touch();assert not ai_runtime.ready()


def test_ai_setup_only_marks_ready_after_inference(tmp_path,monkeypatch):
    root,state=seed_runtime(tmp_path,monkeypatch)
    commands=[];monkeypatch.setattr(ai_runtime,'run_lines',lambda command,*a,**k:commands.append(command))
    class Result:returncode=0;stderr='';stdout=json.dumps({'device':'cpu','inference_verified':True,'model':'openai/clip-vit-base-patch32','torch':'2.10.0'})
    monkeypatch.setattr(ai_runtime.subprocess,'run',lambda *a,**k:Result())
    report=ai_runtime.install_clip('cpu')
    assert report['inference_verified'] and ai_runtime.ready()
    assert any('https://download.pytorch.org/whl/cpu' in c for c in commands)
    assert not (root/'installing').exists()


def test_failed_ai_setup_stays_unavailable(tmp_path,monkeypatch):
    root,state=seed_runtime(tmp_path,monkeypatch)
    def fail(*args,**kwargs):raise RuntimeError('download failed')
    monkeypatch.setattr(ai_runtime,'run_lines',fail)
    with pytest.raises(RuntimeError):ai_runtime.install_clip('cuda')
    assert not ai_runtime.ready() and not state.exists()
    with pytest.raises(ValueError):ai_runtime.install_clip('unknown')


def test_analyze_never_downloads_models(tmp_path,monkeypatch):
    root,state=seed_runtime(tmp_path,monkeypatch)
    state.write_text(json.dumps({'version':1,'root':str(root),'device':'cpu'}))
    calls=[]
    class Result:returncode=0;stderr='';stdout='[]'
    monkeypatch.setattr(ai_runtime.subprocess,'run',lambda *a,**k:(calls.append(k) or Result()))
    assert ai_runtime.analyze([])==[]
    assert calls[0]['env']['HF_HUB_OFFLINE']=='1'


def test_vendor_installer_hash_uses_streamed_bytes(tmp_path):
    import hashlib
    data=b'test vendor download'*1024
    path=tmp_path/'installer.exe';path.write_bytes(data)
    assert local_language.file_digest(path)==hashlib.sha256(data).hexdigest()
