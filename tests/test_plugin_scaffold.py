import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "premiere-plugin"

def test_plugin_manifest_and_entrypoint():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert manifest["host"][0]["app"] == "PPRO"
    assert manifest["entrypoints"][0]["type"] == "panel"
    assert (ROOT / manifest["main"]).is_file()

def test_plugin_panel_non_destructive():
    script = (ROOT / "main.js").read_text()
    assert 'require("premierepro")' in script
    assert "getActiveProject" in script
    assert "createOverwriteItemAction" not in script
