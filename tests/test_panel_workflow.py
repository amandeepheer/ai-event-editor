from pathlib import Path
import json
import subprocess


def test_panel_events_cover_local_setup_review_and_build():
    root=Path(__file__).resolve().parents[1]
    subprocess.run(['node',str(root/'tests'/'panel_workflow.cjs')],cwd=root,check=True)


def test_plugin_only_declares_local_engine_network_access():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'premiere-plugin'/'manifest.json').read_text())
    assert manifest['requiredPermissions']['network']['domains']==['http://127.0.0.1:8765']
