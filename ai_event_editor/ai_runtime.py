"""Managed local AI runtime for the installed edition; no system Python/pip needed."""
from pathlib import Path
import json
import os
import subprocess
import sys
import threading
from .installed_runtime import data_directory

TORCH_VERSION='2.10.0'


def addon_root():
    return (Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1])/'AIAddon'


def state_file():return data_directory()/'ai-runtime.json'


def ready():
    root=addon_root()
    if (root/'installing').exists():return False
    try:
        state=json.loads(state_file().read_text(encoding='utf-8'))
        return (state.get('version')==1 and Path(state.get('root','')).resolve()==root.resolve()
                and (root/'python'/'python.exe').is_file() and (root/'source'/'ai_event_editor'/'ai_worker.py').is_file() and state.get('device') in ('cpu','cuda'))
    except (OSError,ValueError,TypeError):return False


def environment():
    return {**os.environ,'HF_HOME':str(data_directory()/'models'/'clip'),
            'HF_HUB_DISABLE_TELEMETRY':'1','HF_HUB_DISABLE_IMPLICIT_TOKEN':'1',
            'HF_HUB_DISABLE_XET':'1','PYTHONUTF8':'1','TOKENIZERS_PARALLELISM':'false'}


def run_lines(command,progress,env=None,timeout=1800):
    # Managed Python and all arguments are fixed by this app, never by model output.
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
                          encoding='utf-8',errors='replace',env=env or environment()) as process:
        timer=threading.Timer(timeout,process.kill);timer.start()
        try:
            tail=[]
            for line in process.stdout:
                tail.append(line.rstrip());tail=tail[-12:]
                if line.strip():progress(line.strip()[-240:])
            code=process.wait()
            if code:raise RuntimeError('AI setup failed or timed out:\n'+'\n'.join(tail))
        finally:timer.cancel()


def install_clip(mode='cpu',progress=lambda text:None):
    if mode not in ('cpu','cuda'):raise ValueError('Choose CPU or NVIDIA GPU mode')
    root=addon_root();python=root/'python'/'python.exe'
    wheels=list((root/'wheels').glob('pip-*.whl'))
    if not python.is_file() or len(wheels)!=1:
        raise RuntimeError('Install the AI Edition/add-on installer first; the managed Python runtime is missing')
    root.mkdir(exist_ok=True);(root/'installing').write_text(mode)
    bootstrap=root/'source'/'pip_bootstrap.py'
    common=[str(python),str(bootstrap),str(wheels[0]),'install','--disable-pip-version-check','--no-warn-script-location','--upgrade']
    progress('Installing local AI packages. CPU downloads hundreds of MB; NVIDIA CUDA downloads can be several GB…')
    run_lines([*common,'torch=='+TORCH_VERSION,'--index-url','https://download.pytorch.org/whl/'+('cpu' if mode=='cpu' else 'cu130')],progress)
    run_lines([*common,'transformers>=4.48,<5','pillow>=10','numpy>=1.26,<3'],progress)
    progress('Downloading CLIP weights once, then testing real local inference…')
    env=environment();env['AI_EVENT_DEVICE']=mode
    result=subprocess.run([str(python),'-m','ai_event_editor.ai_worker','--download-model'],
                          capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=900)
    if result.returncode:
        raise RuntimeError('Model setup/inference failed. For GPU mode check NVIDIA drivers, or select CPU mode.\n'+result.stderr[-2500:])
    report=json.loads(result.stdout)
    if report.get('device')!=('cuda' if mode=='cuda' else 'cpu') or not report.get('inference_verified'):
        raise RuntimeError('AI runtime did not verify the selected processing device')
    state_file().parent.mkdir(parents=True,exist_ok=True)
    state_file().write_text(json.dumps({'version':1,'root':str(root.resolve()),'device':report['device'],
                                     'model':report['model'],'torch':report['torch']}),encoding='utf-8')
    (root/'installing').unlink()
    progress('CLIP ready on '+report['device']+'. Reconnect the Premiere panel to refresh its AI options.')
    return report


def analyze(media):
    if not ready():raise RuntimeError('Install and verify CLIP through Setup and Status first')
    root=addon_root();state=json.loads(state_file().read_text())
    env=environment();env['AI_EVENT_DEVICE']=state['device'];env['HF_HUB_OFFLINE']='1'
    result=subprocess.run([str(root/'python'/'python.exe'),'-m','ai_event_editor.ai_worker'],
        input=json.dumps({'media':media}),capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=3600)
    if result.returncode:raise RuntimeError('Local AI analysis failed: '+result.stderr[-1800:])
    values=json.loads(result.stdout)
    if not isinstance(values,list):raise ValueError('Invalid local AI worker result')
    return values
