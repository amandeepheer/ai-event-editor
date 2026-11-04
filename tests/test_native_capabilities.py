from pathlib import Path
import subprocess


def test_native_inventory_only_reads_and_reports_evidence_limits():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['node', str(root/'tests/native_capabilities.cjs')], cwd=root, check=True)
