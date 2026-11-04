from pathlib import Path
import json
import subprocess


def test_panel_events_cover_local_setup_review_and_build():
    root=Path(__file__).resolve().parents[1]
    subprocess.run(['node',str(root/'tests'/'panel_workflow.cjs')],cwd=root,check=True)


def test_plugin_declares_network_compatibility_permission():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'premiere-plugin'/'manifest.json').read_text())
    # Local-host entries failed on the installed Premiere host; the client enforces loopback.
    assert manifest['requiredPermissions']['network']['domains']=='all'


def test_loopback_client_permission_failure_and_fixed_destination():
    root=Path(__file__).resolve().parents[1]
    subprocess.run(['node',str(root/'tests'/'engine_permissions.cjs')],cwd=root,check=True)
