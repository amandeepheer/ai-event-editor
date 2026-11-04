"""Per-user media tools for the packaged Windows helper. Downloads run on the user's PC."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
import zipfile

MEDIA_URL='https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-31-12-59/ffmpeg-n8.1.3-27-g8dca1586f4-win64-lgpl-shared-8.1.zip'
MEDIA_SHA256='5cef7bc48e513f3cee7c881e8b2999d835541edb1846c3e89443a67f8f8556ab'
MEDIA_FOLDER='ffmpeg-8.1-'+MEDIA_SHA256[:8]


def data_directory():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))/'AIEventEditor'


def configure_tools_path(base=None):
    base=Path(base) if base is not None else data_directory()
    location=base/'tools-location.json'
    if not location.is_file():return None
    relative=json.loads(location.read_text(encoding='utf-8'))['bin']
    if not isinstance(relative,str):raise ValueError('Invalid media-tools location')
    tools=(base/'tools').resolve()
    folder=(tools/relative).resolve()
    if not folder.is_relative_to(tools):raise ValueError('Invalid local media-tools location')
    if not all((folder/name).is_file() for name in ('ffmpeg.exe','ffprobe.exe')):
        raise ValueError('Installed media tools are missing. Run Finish setup again')
    os.environ['PATH']=str(folder)+os.pathsep+os.environ.get('PATH','')
    return folder


def safe_extract(archive,destination):
    destination=Path(destination).resolve()
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            path=PurePosixPath(entry.filename)
            if ('\\' in entry.filename or path.is_absolute() or '..' in path.parts or ':' in entry.filename
                    or (entry.external_attr>>16)&0o170000==0o120000):
                raise ValueError('Unsafe path in media-tools archive')
            if not (destination/entry.filename).resolve().is_relative_to(destination):
                raise ValueError('Archive path escapes destination')
        bundle.extractall(destination)


def install_media_tools(base=None,progress=lambda message:None):
    base=Path(base) if base is not None else data_directory()
    base.mkdir(parents=True,exist_ok=True)
    try:
        if configure_tools_path(base):return configure_tools_path(base)
    except (ValueError,KeyError,FileNotFoundError):pass
    # An existing system install is also valid; nothing changes the system PATH.
    if not (base/'tools-location.json').exists() and os.environ.get('AI_EVENT_FORCE_MEDIA_DOWNLOAD')!='1' and shutil.which('ffmpeg') and shutil.which('ffprobe'):
        progress('Using FFmpeg already installed on this computer.')
        return Path(shutil.which('ffmpeg')).parent
    target=base/'tools'/MEDIA_FOLDER
    if not target.exists():
        progress('Downloading media tools (approximately 81 MB) from the upstream publisher…')
        with tempfile.TemporaryDirectory(prefix='event-media-') as temp:
            archive=Path(temp)/'media-tools.zip'
            digest=hashlib.sha256()
            request=urllib.request.Request(MEDIA_URL,headers={'User-Agent':'AIEventEditor/0.3'})
            with urllib.request.urlopen(request,timeout=90) as response,archive.open('wb') as output:
                total=int(response.headers.get('Content-Length',0));received=0;last=-1
                while chunk:=response.read(1024*1024):
                    output.write(chunk);digest.update(chunk);received+=len(chunk)
                    percent=int(received*100/total) if total else int(received/1024/1024)
                    if percent!=last:progress(f'Downloading media tools: {percent}{"%" if total else " MB"}');last=percent
            if digest.hexdigest()!=MEDIA_SHA256:raise ValueError('Media download checksum did not match. No tools were installed; retry setup')
            stage=Path(temp)/'extracted';safe_extract(archive,stage)
            progress('Installing verified media tools…')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(stage,target)
    matches=[p.parent for p in target.rglob('ffmpeg.exe') if (p.parent/'ffprobe.exe').is_file()]
    if len(matches)!=1:raise ValueError('Media tools were incomplete. Inspect the tools folder or retry with support')
    folder=matches[0]
    (base/'tools-location.json').write_text(json.dumps({'bin':str(folder.relative_to(base/'tools'))}),encoding='utf-8')
    return configure_tools_path(base)
