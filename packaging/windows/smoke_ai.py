"""Install real CPU packages/model and classify real footage in the installed AI edition."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request


def main():
    app=Path(sys.argv[1]);engine=app/'AIEventEngine.exe'
    subprocess.run([str(engine),'--install-ai-cpu'],check=True,timeout=1200)
    base=Path(os.environ['LOCALAPPDATA'])/'AIEventEditor'
    state=json.loads((base/'ai-runtime.json').read_text())
    assert state['device']=='cpu' and state['model']=='openai/clip-vit-base-patch32'
    config=json.loads((base/'engine-connection.json').read_text())
    location=json.loads((base/'tools-location.json').read_text())
    ffmpeg=base/'tools'/location['bin']/'ffmpeg.exe'
    process=subprocess.Popen([str(engine),'--background'])
    try:
        def call(path,body=None):
            request=urllib.request.Request('http://127.0.0.1:8765/v1/'+path,
                data=json.dumps(body).encode() if body is not None else None,
                headers={'Authorization':'Bearer '+config['token'],'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)
        for _ in range(50):
            try:health=call('health');break
            except OSError:time.sleep(.3)
        else:raise RuntimeError('AI-edition helper did not start')
        assert health['vision_available'] is True
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'sample.mp4'
            subprocess.run([str(ffmpeg),'-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=25:d=3','-c:v','mpeg4',str(source)],check=True)
            job=call('prepare',{'paths':[str(source)],'use_ai':True})
            for _ in range(240):
                result=call('jobs/'+job['job_id'])
                if result['status']=='completed':break
                if result['status']=='failed':raise RuntimeError(result['error'])
                time.sleep(.5)
            else:raise RuntimeError('Real AI footage preparation timed out')
            values=result['result']['candidates']
            assert values and all(c['model']=='openai/clip-vit-base-patch32' for c in values)
            assert all(c['review_required'] and c['thumbnail_data'] for c in values)
            assert source.is_file()
    finally:process.terminate();process.wait(timeout=20)
    print('PASS: installed managed Python, CPU Torch, cached CLIP download and real inference, engine capability detection and AI footage suggestions over authenticated HTTP. NVIDIA and real Ollama/Qwen not tested on this runner.')

if __name__=='__main__':main()
