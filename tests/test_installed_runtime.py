from io import BytesIO
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile
import pytest
from ai_event_editor.installed_runtime import safe_extract,configure_tools_path,install_media_tools
from ai_event_editor.service import configure_plugin


def archive_bytes(entries):
    output=BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for name,value in entries.items():archive.writestr(name,value)
    return output.getvalue()


@pytest.mark.parametrize('path',['../secret','/absolute','root/../../bad','C:/bad','root\\..\\bad'])
def test_archive_cannot_escape_tools_folder(tmp_path,path):
    archive=tmp_path/'tools.zip';archive.write_bytes(archive_bytes({path:'bad'}))
    with pytest.raises(ValueError):safe_extract(archive,tmp_path/'out')


def test_location_cannot_escape_tools_folder(tmp_path):
    (tmp_path/'tools-location.json').write_text(json.dumps({'bin':'../../secret'}))
    with pytest.raises(ValueError):configure_tools_path(tmp_path)


def test_download_is_verified_and_reused(tmp_path,monkeypatch):
    import ai_event_editor.installed_runtime as runtime
    data=archive_bytes({'publisher/bin/ffmpeg.exe':'fixture','publisher/bin/ffprobe.exe':'fixture','publisher/LICENSE.txt':'publisher notice'})
    monkeypatch.setattr(runtime,'MEDIA_SHA256',hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(runtime.shutil,'which',lambda name:None)
    calls=[]
    def download(*args,**kwargs):
        calls.append(args);response=BytesIO(data);response.headers={'Content-Length':str(len(data))};return response
    monkeypatch.setattr(runtime.urllib.request,'urlopen',download)
    folder=install_media_tools(tmp_path)
    assert (folder/'ffmpeg.exe').is_file()
    assert (folder.parent/'LICENSE.txt').is_file()
    assert install_media_tools(tmp_path)==folder
    assert len(calls)==1


def test_checksum_failure_does_not_install_tools(tmp_path,monkeypatch):
    import ai_event_editor.installed_runtime as runtime
    monkeypatch.setattr(runtime.shutil,'which',lambda name:None)
    def download(*args,**kwargs):
        response=BytesIO(b'corrupt');response.headers={};return response
    monkeypatch.setattr(runtime.urllib.request,'urlopen',download)
    with pytest.raises(ValueError,match='checksum'):install_media_tools(tmp_path)
    assert not (tmp_path/'tools-location.json').exists()


def test_frozen_configuration_launches_exe_without_python_module(tmp_path,monkeypatch):
    import sys
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'executable',str(tmp_path/'AIEventEngine.exe'))
    config=configure_plugin(base=tmp_path/'user-data')
    launcher=(config.parent/'Start-AI-Event-Engine.cmd').read_text()
    assert 'AIEventEngine.exe' in launcher and '--background' in launcher
    assert '-m ai_event_editor' not in launcher
    assert 'pythonw.exe' not in launcher


def test_adobe_package_has_manifest_at_root(tmp_path):
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('windows_package',root/'packaging/windows/package.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    destination=tmp_path/'panel.ccx';module.package_panel(destination)
    with zipfile.ZipFile(destination) as archive:
        assert 'manifest.json' in archive.namelist()
        assert 'main.js' in archive.namelist()
        assert json.loads(archive.read('manifest.json'))['host']['app']=='premierepro'
        assert archive.testzip() is None
