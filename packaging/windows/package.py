"""Bundle the engine, independent Adobe CCX and per-user Windows installer."""
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]


def package_panel(destination):
    source=ROOT/'premiere-plugin'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(source).as_posix())
    with zipfile.ZipFile(destination) as archive:
        assert 'manifest.json' in archive.namelist()
        assert archive.testzip() is None


def main():
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
        '--name','AIEventEngine','--paths',str(ROOT),'--exclude-module','torch',
        '--exclude-module','transformers','--exclude-module','PIL',
        str(ROOT/'packaging/windows/engine_entry.py')],cwd=ROOT,check=True)
    output=ROOT/'dist'/'AIEventEngine'
    package_panel(output/'AIEventEditor-Premiere.ccx')
    shutil.copy2(ROOT/'packaging/windows/INSTALL_README.txt',output)
    shutil.copy2(ROOT/'USER_GUIDE.md',output)
    python_license=Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.is_file():shutil.copy2(python_license,output/'PYTHON_LICENSE.txt')
    (output/'THIRD_PARTY_NOTICES.txt').write_text('This package includes CPython and the PyInstaller bootloader/runtime.\nPython: https://docs.python.org/3/license.html\nPyInstaller licence and bootloader exception: https://pyinstaller.org/en/stable/license.html\nInstaller built with Inno Setup: https://jrsoftware.org/isinfo.php\nFFmpeg is downloaded directly from BtbN during first setup; its archive retains its notices.\n',encoding='utf-8')
    compiler=Path(r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
    if not compiler.is_file():raise FileNotFoundError('Inno Setup compiler not installed')
    subprocess.run([str(compiler),str(ROOT/'packaging/windows/installer.iss')],cwd=ROOT,check=True)
    download=ROOT/'dist'/'download';download.mkdir(parents=True,exist_ok=True)
    for installer in (ROOT/'dist'/'installer').glob('*.exe'):shutil.copy2(installer,download)
    shutil.copy2(ROOT/'packaging/windows/INSTALL_README.txt',download)

if __name__=='__main__':main()
