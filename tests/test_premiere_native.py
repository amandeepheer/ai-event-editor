"""Exercise the native adapter using an explicit Adobe API test double."""
from pathlib import Path
import subprocess


def test_new_sequence_adapter_contract():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['node',str(root/'tests'/'premiere_native.cjs')],cwd=root,check=True)
