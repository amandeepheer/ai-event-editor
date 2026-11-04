"""PyInstaller entry: background service, diagnostics or the setup/status window."""
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


def main():
    from ai_event_editor.installed_runtime import configure_tools_path, data_directory, install_media_tools
    base=data_directory();base.mkdir(parents=True,exist_ok=True)
    if sys.stdout is None:sys.stdout=(base/'engine.log').open('a',encoding='utf-8')
    if sys.stderr is None:sys.stderr=sys.stdout
    if os.name=='nt':
        original=subprocess.Popen
        def quiet(*args,**kwargs):
            kwargs['creationflags']=kwargs.get('creationflags',0)|subprocess.CREATE_NO_WINDOW
            return original(*args,**kwargs)
        subprocess.Popen=quiet
    try:configure_tools_path()
    except (ValueError,KeyError,FileNotFoundError):
        if "--background" in sys.argv:raise
        print("Media tools need repair; use Finish setup.")
    if '--install-runtime' in sys.argv:
        install_media_tools(progress=print)
        from ai_event_editor.service import configure_plugin
        configure_plugin();return
    if '--diagnostics' in sys.argv:
        path=Path(sys.argv[sys.argv.index('--diagnostics')+1])
        import shutil
        versions={}
        for tool in ('ffmpeg','ffprobe'):
            available=shutil.which(tool)
            versions[tool]=subprocess.run([tool,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0] if available else None
        path.write_text(json.dumps({'frozen':bool(getattr(sys,'frozen',False)),'tools':versions,'configuration_exists':(base/'engine-connection.json').is_file()}),encoding='utf-8');return
    if '--background' in sys.argv or '--configure-plugin' in sys.argv:
        from ai_event_editor.service import main as service_main
        service_main();return
    from ai_event_editor.installer_ui import main as setup_main
    setup_main()

if __name__=='__main__':
    try:main()
    except Exception:
        traceback.print_exc();sys.exit(1)
