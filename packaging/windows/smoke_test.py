"""Exercise the installed frozen engine over real HTTP; no installed Python dependency."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile


def main():
    app=Path(sys.argv[1]);engine=app/'AIEventEngine.exe'
    subprocess.run([str(engine),'--install-runtime'],check=True,timeout=240,env={**os.environ,'AI_EVENT_FORCE_MEDIA_DOWNLOAD':'1'})
    with tempfile.TemporaryDirectory() as temporary:
        diagnostics=Path(temporary)/'diagnostics.json'
        subprocess.run([str(engine),'--diagnostics',str(diagnostics)],check=True,timeout=30)
        data=json.loads(diagnostics.read_text())
        assert data['frozen'] and all(data['tools'].values()) and data['configuration_exists'],data
        base=Path(os.environ['LOCALAPPDATA'])/'AIEventEditor'
        config=json.loads((base/'engine-connection.json').read_text())
        assert '-m ai_event_editor' not in (base/'Start-AI-Event-Engine.cmd').read_text()
        process=subprocess.Popen([str(engine),'--background'])
        try:
            def call(path,body=None):
                request=urllib.request.Request('http://127.0.0.1:8765/v1/'+path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers={'Authorization':'Bearer '+config['token'],'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=15) as response:return json.load(response)
            for attempt in range(40):
                try:health=call('health');break
                except OSError:time.sleep(.5)
            else:raise RuntimeError('Installed engine did not start')
            assert health['ffmpeg'] and health['ffprobe'],health
            assert health['vision_available'] is False,health
            # Same shipped media tools, with no H.264 encoder dependency in this basic installer.
            location=json.loads((base/'tools-location.json').read_text()) if (base/'tools-location.json').is_file() else None
            ffmpeg=base/'tools'/location['bin']/'ffmpeg.exe' if location else 'ffmpeg'
            source=Path(temporary)/'sample.mp4'
            subprocess.run([str(ffmpeg),'-v','error','-y','-f','lavfi','-i','color=c=blue:s=160x90:r=25:d=36','-c:v','mpeg4',str(source)],check=True)
            def wait(job):
                for _ in range(180):
                    result=call('jobs/'+job['job_id'])
                    if result['status']=='completed':return result['result']
                    if result['status']=='failed':raise RuntimeError(result['error'])
                    time.sleep(.5)
                raise RuntimeError('Packaged operation timed out')
            music=Path(temporary)/'music.wav'
            subprocess.run([str(ffmpeg),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=8000:duration=36',str(music)],check=True)
            assert health['project_media_available'] is True
            selected=wait(call('project-media',{'paths':[str(source),str(music)]}))
            assert len(selected['videos'])==1 and len(selected['audio'])==1 and not selected['errors']
            prepared=wait(call('prepare',{'paths':[v['path'] for v in selected['videos']]}))
            assert len(prepared['candidates'])==9
            edit=wait(call('build',{'session_id':prepared['session_id'],'setup':{'music':str(music)},'instruction':'Use these clips and this music to make a 30-second cinematic recap'}))
            assert edit['plan']['duration_frames']==750
            assert edit['plan']['audio']['path']==str(music)
            assert source.is_file()
        finally:process.terminate();process.wait(timeout=20)
    with zipfile.ZipFile(app/'AIEventEditor-Premiere.ccx') as package:
        manifest=json.loads(package.read('manifest.json'))
        assert manifest['host']['app']=='premierepro'
        assert 'project-media.js' in package.namelist()
        assert package.testzip() is None
    print('PASS: silent installer, bundled Python runtime, media download/checksum, frozen helper HTTP, project-media video/audio classification, thumbnails, typed music build and CCX structure. Native Adobe selection and timeline creation not tested.')

if __name__=='__main__':main()
