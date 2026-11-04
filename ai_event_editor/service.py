"""Authenticated loopback companion for Premiere. Stdlib only; no cloud API."""
from copy import deepcopy
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import base64
import json
import os
import secrets
import shutil
import tempfile
import threading
from urllib.parse import urlsplit
from .workflow import Setup, prepare_footage, create_edit, reviewed_shots
from .instructions import interpret

API_VERSION = 1
ORIGINS = {'null', 'plugin://com.aieventeditor.panel', 'uxp://com.aieventeditor.panel'}

class Engine:
    def __init__(self, token=None):
        self.token = token or secrets.token_urlsafe(32)
        self.cache = tempfile.TemporaryDirectory(prefix='ai-event-premiere-')
        self.lock = threading.RLock()
        self.jobs = {}
        self.sessions = {}
        self.active = None
        self.worker = None

    def close(self):
        if self.worker:
            self.worker.join()
        self.cache.cleanup()

    def health(self):
        return {'api_version': API_VERSION, 'engine': 'AI Event Editor',
                'ffmpeg': bool(shutil.which('ffmpeg')), 'ffprobe': bool(shutil.which('ffprobe')),
                'busy': self.active is not None,
                'instructions': ['duration','pacing','style','include category','exclude category'],
                'native_host_verified': False}

    def submit(self, task):
        with self.lock:
            if self.active:
                raise RuntimeError('Engine is busy. Wait for the current operation to finish')
            # Keep completed jobs/sessions bounded; never remove source media.
            if len(self.jobs) >= 16:
                self.jobs.pop(next(iter(self.jobs)))
            identifier = secrets.token_hex(16)
            self.jobs[identifier] = {'id':identifier,'status':'running','progress':'Starting local operation'}
            self.active = identifier
        def progress(message):
            with self.lock:
                self.jobs[identifier]['progress'] = message
        def work():
            try:
                result = task(progress)
                json.dumps(result,allow_nan=False)  # Fail jobs cleanly if a model returns invalid numbers.
                with self.lock: self.jobs[identifier].update(status='completed',result=result)
            except Exception as error:
                with self.lock: self.jobs[identifier].update(status='failed',error=str(error))
            finally:
                with self.lock: self.active = None
        self.worker = threading.Thread(target=work,daemon=True)
        self.worker.start()
        return {'job_id':identifier}

    def job(self, identifier):
        with self.lock:
            if identifier not in self.jobs: raise KeyError('Job not found or expired')
            return deepcopy(self.jobs[identifier])

    def prepare(self, data):
        paths = data.get('paths')
        if not isinstance(paths,list) or not 1 <= len(paths) <= 2000 or any(not isinstance(p,str) or not Path(p).is_absolute() for p in paths):
            raise ValueError('Select 1–2000 local footage files with absolute paths')
        use_ai = data.get('use_ai',False)
        if not isinstance(use_ai,bool): raise ValueError('Invalid AI mode')
        def task(progress):
            session_id = secrets.token_hex(16)
            result = prepare_footage(paths,Path(self.cache.name)/session_id,use_ai,progress,thumbnail_format='png')
            if len(result['candidates']) > 20000:
                raise ValueError('Too many moments; prepare fewer clips at once (maximum 20000 moments)')
            candidates = result['candidates']
            with self.lock:
                if len(self.sessions)>=4: self.sessions.pop(next(iter(self.sessions)))
                self.sessions[session_id] = deepcopy(candidates)
            visible=[]
            for candidate in candidates:
                value = {k:v for k,v in candidate.items() if k!='thumbnail'}
                thumb=candidate.get('thumbnail')
                value['thumbnail_data'] = ('data:image/png;base64,'+base64.b64encode(Path(thumb).read_bytes()).decode('ascii')) if thumb else None
                visible.append(value)
            return {**result,'session_id':session_id,'candidates':visible}
        return self.submit(task)

    def request(self, data):
        identifier=data.get('session_id')
        with self.lock:
            if not isinstance(identifier,str) or identifier not in self.sessions:
                raise ValueError('Review session expired. Prepare your footage again')
            candidates=deepcopy(self.sessions[identifier])
        patches=data.get('review',[])
        if not isinstance(patches,list): raise ValueError('Invalid shot review')
        known={c['id']:c for c in candidates}
        seen=set()
        for patch in patches:
            if not isinstance(patch,dict) or patch.get('id') not in known or patch['id'] in seen:
                raise ValueError('Review contains unknown or duplicate moment IDs')
            if set(patch)-{'id','decision','category'}:
                raise ValueError('Review can change decisions and categories, not source paths or timing')
            seen.add(patch['id'])
            known[patch['id']].update({k:v for k,v in patch.items() if k!='id'})
        reviewed_shots(candidates)
        if not isinstance(data.get('setup',{}),dict): raise ValueError('Invalid setup')
        setup=Setup(**data.get('setup',{}))
        result=interpret(data.get('instruction',''),setup,candidates)
        return result

    def build(self,data):
        parsed=self.request(data)
        if parsed['unsupported']: raise ValueError('; '.join(parsed['unsupported']))
        def task(progress):
            progress('Analyzing selected music and building the reviewed edit locally…')
            plan=create_edit(parsed['candidates'],Setup(**parsed['setup']))
            return {'plan':plan,'instructions':{k:v for k,v in parsed.items() if k not in ('candidates',)}}
        return self.submit(task)


def handler(engine):
    class Handler(BaseHTTPRequestHandler):
        server_version='AIEventLocal/1'
        def log_message(self,*args): pass  # Do not log paths, tokens or request bodies.
        def origin_allowed(self):
            return self.headers.get('Origin') is None or self.headers.get('Origin') in ORIGINS
        def check_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
        def send_json(self,status,data):
            payload=json.dumps(data,allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            origin=self.headers.get('Origin')
            if origin in ORIGINS:
                self.send_header('Access-Control-Allow-Origin',origin)
                self.send_header('Vary','Origin')
            if self.command=='OPTIONS':
                self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type')
            self.end_headers()
            self.wfile.write(payload)
        def authorized(self):
            if not self.check_host() or not self.origin_allowed():
                self.send_json(403,{'error':'Only the paired local Premiere panel is allowed'});return False
            expected=('Bearer '+engine.token).encode()
            supplied=self.headers.get('Authorization','').encode()
            if not secrets.compare_digest(expected,supplied):
                self.send_json(401,{'error':'Pair with your local engine using its pairing code'});return False
            return True
        def do_OPTIONS(self):
            if not self.check_host() or not self.origin_allowed(): self.send_json(403,{'error':'Origin not allowed'})
            else: self.send_json(200,{'ok':True})
        def do_GET(self):
            if not self.authorized(): return
            path=urlsplit(self.path)
            if path.query: self.send_json(400,{'error':'Query parameters are not supported'});return
            try:
                if path.path=='/v1/health': self.send_json(200,engine.health())
                elif path.path.startswith('/v1/jobs/'): self.send_json(200,engine.job(path.path[len('/v1/jobs/'):]))
                else: self.send_json(404,{'error':'Endpoint not found'})
            except KeyError as error: self.send_json(404,{'error':str(error)})
        def do_POST(self):
            if not self.authorized(): return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0 < size <= 2*1024*1024: raise ValueError('Request body must be 1 byte to 2 MB')
                if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
                    raise ValueError('Use JSON request bodies')
                data=json.loads(self.rfile.read(size),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON number')))
                if not isinstance(data,dict): raise ValueError('Request must be an object')
                if self.path=='/v1/prepare': result=engine.prepare(data)
                elif self.path=='/v1/interpret':
                    parsed=engine.request(data)
                    result={**parsed,'candidates':[{k:c[k] for k in ('id','decision','category')} for c in parsed['candidates']]}
                elif self.path=='/v1/build': result=engine.build(data)
                else: self.send_json(404,{'error':'Endpoint not found'});return
                self.send_json(202 if 'job_id' in result else 200,result)
            except RuntimeError as error: self.send_json(409,{'error':str(error)})
            except (ValueError,TypeError,KeyError,OSError) as error: self.send_json(400,{'error':str(error)})
    return Handler


def create_server(engine,port=8765):
    server=ThreadingHTTPServer(('127.0.0.1',port),handler(engine))
    server.daemon_threads=True
    return server


def persistent_token():
    base=Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))/'AIEventEditor'
    base.mkdir(parents=True,exist_ok=True)
    path=base/'engine-token'
    if path.exists():
        token=path.read_text(encoding='utf-8').strip()
        if len(token)>=32: return token
    token=secrets.token_urlsafe(32)
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(descriptor,'w',encoding='utf-8') as file: file.write(token)
    return token


def main():
    parser=argparse.ArgumentParser(description='Local processing companion for the AI Event Editor Premiere panel')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 1 <= args.port <= 65535: parser.error('Port must be 1–65535')
    engine=Engine(persistent_token())
    try: server=create_server(engine,args.port)
    except OSError as error:
        engine.close(); parser.error(f'Could not start local engine: {error}')
    print(f'AI Event Editor local engine: http://127.0.0.1:{server.server_port}',flush=True)
    print('Pairing code (paste into the Premiere panel): '+engine.token,flush=True)
    print('Keep this helper running. Editing stays inside Premiere. Ctrl+C stops the helper.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        engine.close()

if __name__=='__main__': main()
