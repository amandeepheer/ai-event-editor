import json
from pathlib import Path
import subprocess
import pytest
from ai_event_editor.service import configure_plugin


def test_automatic_launch_state_machine():
    root=Path(__file__).resolve().parents[1]
    subprocess.run(['node',str(root/'tests'/'autostart.cjs')],cwd=root,check=True)


def test_configuration_creates_stable_pairing_and_quoted_hidden_launcher(tmp_path):
    path=configure_plugin(base=tmp_path,executable=r'C:\Program Files\Python\pythonw.exe',working_directory=r'C:\Video Projects\Aman & Family')
    data=json.loads(path.read_text())
    assert data['base']=='http://127.0.0.1:8765'
    assert len(data['token'])>=32
    script=(tmp_path/'Start-AI-Event-Engine.cmd').read_text(encoding='utf-8')
    assert '"C:\\Program Files\\Python\\pythonw.exe"' in script
    assert 'Aman & Family' in script
    assert 'ai_event_editor.service --background' in script
    assert 'start "" /b' in script  # Background GUI interpreter; no persistent console.
    assert data['token'] not in script
    assert json.loads(configure_plugin(base=tmp_path,executable=r'C:\Python\pythonw.exe').read_text())['token']==data['token']


@pytest.mark.parametrize('value',['C:\\bad%PATH%\\python.exe','bad\ncommand','bad\rcommand'])
def test_launcher_rejects_environment_expansion_and_line_injection(tmp_path,value):
    with pytest.raises(ValueError):configure_plugin(base=tmp_path,executable=value)
    assert not (tmp_path/'Start-AI-Event-Engine.cmd').exists()


def test_only_cmd_launch_permission_is_declared():
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/'premiere-plugin'/'manifest.json').read_text())
    assert data['requiredPermissions']['launchProcess']=={'extensions':['.cmd']}


def test_default_setup_requires_background_python(tmp_path,monkeypatch):
    import sys
    monkeypatch.setattr(sys,'executable',str(tmp_path/'python.exe'))
    with pytest.raises(ValueError,match='pythonw.exe'):configure_plugin(base=tmp_path/'config')


def test_default_setup_uses_pythonw(tmp_path,monkeypatch):
    import sys
    (tmp_path/'pythonw.exe').touch()
    monkeypatch.setattr(sys,'executable',str(tmp_path/'python.exe'))
    path=configure_plugin(base=tmp_path/'config')
    script=(path.parent/'Start-AI-Event-Engine.cmd').read_text()
    assert str(tmp_path/'pythonw.exe') in script
    assert '--background' in script
