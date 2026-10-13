#!/usr/bin/env python3
"""Lab 1: synthetic cameras -> authenticated RTSP pulls -> software recording.

No physical device, DHCP, VLAN, NTP server or ONVIF service is emulated.
Only processes owned by this lab and identified by /proc start time are stopped.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
STATE = ROOT/'runtime/state.json'
CREDS = ROOT/'config/credentials.json'
FF = ROOT/'tools/ffmpeg'
MTX = ROOT/'tools/mediamtx'
NVR = '127.30.0.10'
CAMERAS = {'cam01': '127.20.0.11', 'cam02': '127.20.0.12'}
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def stamp():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

def private_json(path, value):
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(value, out, indent=2)
        out.write('\n')
    path.chmod(0o600)

def credentials():
    if not CREDS.exists():
        private_json(CREDS, {k: secrets.token_hex(16) for k in ('publisher01','publisher02','recorder','viewer','operator')})
    return json.loads(CREDS.read_text())

def sanitize(text):
    if CREDS.exists():
        for value in credentials().values():
            text = text.replace(value, '<redacted>')
    return text

def state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}

def proc_id(pid):
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return None if fields[0] in ('Z','X') else fields[19]
    except (OSError, IndexError):
        return None

def alive(item):
    return bool(item and proc_id(item['pid']) == item['starttime'])

def emit(message):
    print(message, flush=True)

def run(args, label, timeout=25):
    rendered = sanitize(' '.join(str(a) for a in args))
    with (ROOT/'logs/commands.jsonl').open('a') as log:
        log.write(json.dumps({'utc':utc(),'label':label,'argv':sanitize(json.dumps([str(a) for a in args]))})+'\n')
    try:
        result = subprocess.run([str(a) for a in args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        code, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as e:
        code = 124
        output = ((e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else e.stdout or '') + ((e.stderr or b'').decode(errors='replace') if isinstance(e.stderr,bytes) else e.stderr or '')
    filename = ROOT/'logs'/f'{stamp()}-{label}.log'
    filename.write_text(f'UTC: {utc()}\nCOMMAND: {rendered}\nEXIT: {code}\n'+sanitize(output))
    return code, sanitize(output), str(filename.relative_to(ROOT))

def spawn(name, args):
    s = state()
    if alive(s.get(name)):
        raise RuntimeError(f'{name} is already running')
    logpath = ROOT/'logs'/f'{stamp()}-{name}.log'
    with logpath.open('w') as out:
        # FFmpeg suppresses URL logging in routine operation; credentials are lab-only.
        p = subprocess.Popen([str(a) for a in args], cwd=ROOT, stdin=subprocess.DEVNULL,
                             stdout=out, stderr=subprocess.STDOUT, start_new_session=True,
                             env={**os.environ,'TZ':'UTC'})
    s[name] = {'pid':p.pid,'starttime':proc_id(p.pid),'log':str(logpath.relative_to(ROOT)),'started_utc':utc()}
    private_json(STATE,s)
    with (ROOT/'logs/commands.jsonl').open('a') as out:
        out.write(json.dumps({'utc':utc(),'label':name,'argv':sanitize(json.dumps([str(a) for a in args]))})+'\n')
    time.sleep(0.25)
    if p.poll() is not None:
        raise RuntimeError(f'{name} exited ({p.returncode}): '+sanitize(logpath.read_text()[-1800:]))

def stop_one(name):
    s = state()
    item = s.get(name)
    if alive(item):
        os.kill(item['pid'],signal.SIGINT)
        deadline = time.monotonic()+6
        while alive(item) and time.monotonic()<deadline:
            time.sleep(0.1)
        if alive(item):
            os.kill(item['pid'],signal.SIGTERM)
            time.sleep(0.5)
        if alive(item):
            os.kill(item['pid'],signal.SIGKILL)
    s.pop(name,None)
    private_json(STATE,s)

def stop_all():
    for name in ['publisher01','publisher02','nvr','camera01','camera02']:
        stop_one(name)
    emit('STOPPED: Lab 1 processes; recordings and evidence preserved.')

def account(user, password, actions):
    return {'user':user,'pass':password,'ips':['127.0.0.0/8'],
            'permissions':[{'action':action,'path':path} for action,path in actions]}

def setup():
    c=credentials()
    common={'logLevel':'info','logDestinations':['stdout'],'readTimeout':'10s','writeTimeout':'10s',
            'authMethod':'internal','rtsp':True,'rtspTransports':['tcp'],'rtspEncryption':'no',
            'rtmp':False,'hls':False,'webrtc':False,'srt':False,'moq':False,
            'api':False,'metrics':False,'pprof':False,'playback':False}
    for number,(cam,address) in enumerate(CAMERAS.items(),1):
        publisher=f'publisher0{number}'
        cfg={**common,'rtspAddress':address+':8554',
             'authInternalUsers':[account(publisher,c[publisher],[('publish','main')]),
                                  account('recorder',c['recorder'],[('read','main')])],
             'paths':{'main':{'source':'publisher','overridePublisher':False,'record':False}}}
        private_json(ROOT/'config'/f'camera0{number}.yml',cfg)
    paths={cam:{'source':f'rtsp://recorder:{c["recorder"]}@{address}:8554/main',
                'sourceOnDemand':False,'rtspTransport':'tcp'} for cam,address in CAMERAS.items()}
    cfg={**common,'rtspAddress':NVR+':8554','api':True,'apiAddress':NVR+':9997',
         'playback':True,'playbackAddress':NVR+':9996',
         'hls':True,'hlsAddress':NVR+':8888','hlsVariant':'mpegts',
         'hlsAlwaysRemux':False,'hlsAllowOrigins':['http://'+NVR+':8888'],
         'authInternalUsers':[account('viewer',c['viewer'],[('read','cam01'),('read','cam02'),('playback','cam01'),('playback','cam02')]),
                              account('operator',c['operator'],[('api','')])],
         'pathDefaults':{'record':True,'recordPath':'./recordings/%path/%Y-%m-%d_%H-%M-%S-%f',
                         'recordFormat':'fmp4','recordPartDuration':'1s','recordSegmentDuration':'20s',
                         'recordDeleteAfter':'0s'},'paths':paths}
    private_json(ROOT/'config/nvr.yml',cfg)
    settings={'mode':'software simulation, Linux loopback only','camera_codec':'H264',
              'resolution':'640x360','fps':10,'target_bitrate_bps_per_camera':512000,
              'gop_frames':20,'audio':False,'rtsp_transport':'TCP interleaved',
              'recording':'continuous while source available','segment_target_seconds':20,
              'automatic_deletion':False,'operational_disk_guard_free_bytes':1073741824,
              'runtime_addresses':CAMERAS|{'nvr':NVR},'timezone':'UTC',
              'field_design_subnet':'192.168.20.0/24',
              'field_design_addresses':{'cam01':'192.168.20.11','cam02':'192.168.20.12','nvr':'192.168.20.10','admin_pc':'192.168.20.50','gateway':'192.168.20.1'}}
    (ROOT/'config/lab-settings.json').write_text(json.dumps(settings,indent=2)+'\n')
    emit('SETUP: generated camera/NVR configuration and unique local credentials (0600).')

def publisher(number):
    c=credentials()
    name=f'publisher0{number}'
    cam=f'cam0{number}'
    # Built-in moving patterns are explicitly synthetic, not site footage.
    source='testsrc2=size=640x360:rate=10'
    filters='hflip,hue=h=90' if number==2 else 'null'
    args=[FF,'-hide_banner','-loglevel','warning','-nostdin','-re','-f','lavfi','-i',source,
          '-vf',filters,'-an','-c:v','libx264','-threads','1','-preset','ultrafast','-tune','zerolatency',
          '-pix_fmt','yuv420p','-profile:v','baseline','-b:v','512k','-minrate','512k','-maxrate','512k',
          '-bufsize','1024k','-x264-params','nal-hrd=cbr:force-cfr=1','-g','20','-keyint_min','20',
          '-sc_threshold','0','-f','rtsp','-rtsp_transport','tcp',
          f'rtsp://{name}:{c[name]}@{CAMERAS[cam]}:8554/main']
    spawn(name,args)

def server(name):
    spawn(name,[MTX,ROOT/'config'/f'{name}.yml'])

def http_json(port,path,user):
    c=credentials()
    req=urllib.request.Request(f'http://{NVR}:{port}{path}',headers={
        'Authorization':'Basic '+base64.b64encode(f'{user}:{c[user]}'.encode()).decode()})
    with HTTP.open(req,timeout=12) as r:
        return json.loads(r.read())

def paths_ready():
    return {item['name']:item.get('ready',False) for item in http_json(9997,'/v3/paths/list','operator')['items']}

def wait_ready(expected=None, seconds=35):
    expected=expected or {'cam01':True,'cam02':True}
    deadline=time.monotonic()+seconds
    last={}
    while time.monotonic()<deadline:
        try:
            last=paths_ready()
            if all(last.get(k,False)==v for k,v in expected.items()):
                return last
        except (OSError,ValueError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f'Readiness timeout: expected {expected}, observed {last}')

def start_all():
    if any(alive(i) for i in state().values()):
        raise RuntimeError('Some Lab 1 processes already run. Use status, or stop then start.')
    if not FF.exists() or not MTX.exists():
        raise RuntimeError('Run python3 bootstrap.py first.')
    if not (ROOT/'config/nvr.yml').exists():
        setup()
    if __import__('shutil').disk_usage(ROOT).free<1073741824:
        raise RuntimeError('Less than 1 GiB free: do not start recording.')
    try:
        server('camera01');server('camera02')
        publisher(1);publisher(2)
        server('nvr')
        ready=wait_ready()
        emit('STARTED: '+json.dumps(ready)+'; recording continuously in recordings/.')
        emit('Browser live view: http://127.30.0.10:8888/cam01 and /cam02')
        emit('Use the local viewer credentials in config/credentials.json.')
    except Exception:
        stop_all()
        raise

def rtsp_decode(cam,password=None,path=None,seconds=3,label=None):
    c=credentials()
    pw=password if password is not None else c['viewer']
    url=f'rtsp://viewer:{pw}@{NVR}:8554/{path or cam}'
    return run([FF,'-hide_banner','-loglevel','info','-nostdin','-rtsp_transport','tcp','-i',url,
                '-frames:v',str(int(seconds*10)),'-an','-progress','pipe:1','-f','null','-'],label or 'decode-'+cam)

def frames(output):
    numbers=re.findall(r'^frame=(\d+)\s*$',output,re.M)
    return max(map(int,numbers),default=0)

def report(name,checks):
    data={'utc':utc(),'lab':'01','mode':'actual software execution with synthetic sources',
          'checks':checks,'passed':all(x['pass'] for x in checks)}
    target=ROOT/'evidence'/f'{stamp()}-{name}.json'
    target.write_text(json.dumps(data,indent=2)+'\n')
    (ROOT/'evidence'/f'{name}.json').write_text(json.dumps(data,indent=2)+'\n')
    for check in checks:
        emit(('PASS' if check['pass'] else 'FAIL')+' '+check['name']+': '+str(check['detail']))
    emit('Report: '+str(target.relative_to(ROOT)))
    return data

def verify():
    checks=[]
    ready=wait_ready()
    checks.append({'name':'two NVR sources ready','pass':all(ready.get(c) for c in CAMERAS),'detail':ready})
    for cam in CAMERAS:
        code,out,log=rtsp_decode(cam)
        count=frames(out)
        checks.append({'name':cam+' live decode','pass':code==0 and count>=20,'detail':{'exit':code,'decoded_frames':count,'log':log}})
    code,out,log=rtsp_decode('cam01',password='intentionally-wrong-lab-password',label='bad-password')
    checks.append({'name':'wrong password rejected','pass':code!=0 and '401' in out,'detail':{'exit':code,'observed':'401' if '401' in out else out[-200:],'log':log}})
    code,out,log=rtsp_decode('cam01',path='nonexistent',label='wrong-path')
    checks.append({'name':'unknown channel rejected','pass':code!=0 and any(x in out for x in ('401','404','400')),'detail':{'exit':code,'log':log}})
    c=credentials()
    code,out,log=run([FF,'-hide_banner','-loglevel','info','-nostdin','-f','lavfi','-i','testsrc2=size=160x90:rate=2',
                     '-frames:v','2','-c:v','libx264','-threads','1','-f','rtsp','-rtsp_transport','tcp',
                     f'rtsp://viewer:{c["viewer"]}@{NVR}:8554/cam01'],'viewer-publish-denied')
    checks.append({'name':'viewer cannot publish','pass':code!=0 and any(x in out for x in ('401','403')),'detail':{'exit':code,'log':log}})
    try:
        http_json(9997,'/v3/paths/list','viewer')
        viewer_api_denied=False
    except urllib.error.HTTPError as e:
        viewer_api_denied=e.code in (401,403)
    checks.append({'name':'viewer cannot access control API','pass':viewer_api_denied,'detail':'expected HTTP 401/403'})
    req=urllib.request.Request(f'http://{NVR}:8888/cam01/index.m3u8',headers={
        'Authorization':'Basic '+base64.b64encode(f'viewer:{c["viewer"]}'.encode()).decode()})
    try:
        with HTTP.open(req,timeout=15) as response: playlist=response.read().decode()
        hls_ok=playlist.startswith('#EXTM3U')
    except OSError:
        hls_ok=False;playlist=''
    (ROOT/'evidence/hls-playlist.m3u8').write_text(playlist)
    checks.append({'name':'authenticated HLS live playlist','pass':hls_ok,'detail':'EXTM3U playlist retrieved' if hls_ok else 'playlist unavailable'})
    for cam in CAMERAS:
        deadline=time.monotonic()+40
        listing=[]
        while time.monotonic()<deadline:
            try:
                listing=http_json(9996,'/list?'+urllib.parse.urlencode({'path':cam}),'viewer')
                if listing and any(item['duration']>=5 for item in listing):
                    break
            except (OSError,ValueError):
                pass
            time.sleep(1)
        (ROOT/'evidence'/f'{cam}-playback-list.json').write_text(json.dumps(listing,indent=2)+'\n')
        eligible=[item for item in listing if item['duration']>=5]
        valid=bool(eligible)
        checks.append({'name':cam+' recorded timespan','pass':valid,'detail':listing[:1]})
        if valid:
            selected=eligible[-1]
            # Export recent recorded footage, leaving one second before the available end.
            offset=max(0,selected['duration']-6)
            selected_start=(dt.datetime.fromisoformat(selected['start'].replace('Z','+00:00'))+dt.timedelta(seconds=offset)).isoformat()
            q=urllib.parse.urlencode({'path':cam,'start':selected_start,'duration':5,'format':'mp4'})
            c=credentials()
            req=urllib.request.Request(f'http://{NVR}:9996/get?{q}',headers={'Authorization':'Basic '+base64.b64encode(f'viewer:{c["viewer"]}'.encode()).decode()})
            export=ROOT/'exports'/f'{cam}-verified.mp4'
            with HTTP.open(req,timeout=20) as response:
                export.write_bytes(response.read())
            code,out,log=run([FF,'-hide_banner','-loglevel','info','-nostdin','-i',export,'-progress','pipe:1','-f','null','-'],'playback-decode-'+cam)
            count=frames(out)
            checks.append({'name':cam+' exported playback decode','pass':code==0 and count>=40,'detail':{'exit':code,'decoded_frames':count,'bytes':export.stat().st_size,'sha256':hashlib.sha256(export.read_bytes()).hexdigest(),'log':log}})
            run([FF,'-hide_banner','-loglevel','error','-nostdin','-y','-i',export,'-frames:v','1',ROOT/'evidence'/f'{cam}-snapshot.png'],'snapshot-'+cam)
    checks.append({'name':'service bindings are loopback','pass':loopback_bindings()[0],'detail':loopback_bindings()[1]})
    data=report('verification',checks)
    return 0 if data['passed'] else 1

def loopback_bindings():
    # /proc is read-only and avoids requiring netlink permissions for ss.
    owned={str(item['pid']) for item in state().values() if alive(item)}
    inodes=set()
    for pid in owned:
        for fd in Path('/proc',pid,'fd').iterdir():
            try:
                dest=os.readlink(fd)
                if dest.startswith('socket:['): inodes.add(dest[8:-1])
            except OSError: pass
    listeners=[]
    for row in Path('/proc/net/tcp').read_text().splitlines()[1:]:
        parts=row.split()
        if parts[3]=='0A' and parts[9] in inodes:
            address,port=parts[1].split(':')
            ip=socket.inet_ntoa(bytes.fromhex(address)[::-1])
            listeners.append(f'{ip}:{int(port,16)}')
    return bool(listeners) and all(x.startswith('127.') for x in listeners),sorted(listeners)

def faults():
    checks=[]
    wait_ready()
    emit('FAULT: stopping only cam01 synthetic publisher; cam02 remains active.')
    start=utc();stop_one('publisher01')
    try:
        observed=wait_ready({'cam01':False,'cam02':True},seconds=25)
        code,out,log=rtsp_decode('cam02',label='cam02-during-cam01-outage')
        checks.append({'name':'camera outage isolated','pass':not observed['cam01'] and observed['cam02'] and code==0 and frames(out)>=20,'detail':{'fault_started_utc':start,'observed_utc':utc(),'ready':observed,'cam02_decode_log':log}})
    finally:
        publisher(1)
    observed=wait_ready(seconds=40)
    code,out,log=rtsp_decode('cam01',label='cam01-after-recovery')
    checks.append({'name':'camera recovery automatic at recorder','pass':observed['cam01'] and code==0 and frames(out)>=20,'detail':{'recovered_utc':utc(),'decode_log':log}})
    emit('RECOVERY: cam01 recording source restored. Testing recorder process restart.')
    before=set(str(p.relative_to(ROOT)) for p in (ROOT/'recordings').rglob('*.mp4'))
    start=utc();stop_one('nvr')
    # Graceful shutdown may finalise an additional old fragment. Capture the
    # settled baseline after stopping, before starting the new recorder.
    old_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (ROOT/'recordings').rglob('*.mp4')}
    server('nvr');wait_ready(seconds=40)
    deadline=time.monotonic()+35
    newer=[]
    while time.monotonic()<deadline:
        after=set(str(p.relative_to(ROOT)) for p in (ROOT/'recordings').rglob('*.mp4'))
        newer=sorted(after-set(old_hashes))
        if all(any(f'/recordings/{cam}/' in '/'+p for p in newer) for cam in CAMERAS): break
        time.sleep(1)
    old_preserved=all((ROOT/p).exists() for p in before)
    old_unchanged=all((ROOT/p).exists() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest
                      for p,digest in old_hashes.items())
    # Poll actual decodable new footage rather than assuming a fixed delay
    # commits enough frames. The deadline remains bounded.
    decoded={}
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        for cam in CAMERAS:
            if cam in decoded and decoded[cam]['exit']==0 and decoded[cam]['frames']>=30:continue
            candidates=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'recordings'/cam).glob('*.mp4')
                              if str(p.relative_to(ROOT)) not in old_hashes)
            if candidates:
                selected=candidates[-1]
                code,out,log=run([FF,'-hide_banner','-loglevel','info','-nostdin','-i',ROOT/selected,
                                 '-frames:v','30','-progress','pipe:1','-f','null','-'],'new-recording-after-restart-'+cam)
                decoded[cam]={'exit':code,'frames':frames(out),'log':log,'file':selected}
        if all(cam in decoded and decoded[cam]['exit']==0 and decoded[cam]['frames']>=30 for cam in CAMERAS):break
        time.sleep(.5)
    checks.append({'name':'NVR restart preserves old files and resumes decodable recordings','pass':old_preserved and old_unchanged and all(cam in decoded and decoded[cam]['exit']==0 and decoded[cam]['frames']>=30 for cam in CAMERAS),'detail':{'restart_started_utc':start,'observed_utc':utc(),'old_files_preserved':old_preserved,'settled_old_file_hashes_unchanged':old_unchanged,'settled_old_file_count':len(old_hashes),'new_recordings':decoded}})
    data=report('fault-recovery',checks)
    return 0 if data['passed'] else 1

def status():
    for name,item in state().items(): emit(f'{name}: '+('RUNNING' if alive(item) else 'STOPPED')+f' pid={item["pid"]}')
    try: emit('NVR sources: '+json.dumps(paths_ready()))
    except Exception as e: emit('NVR API unavailable: '+str(e))
    total=sum(p.stat().st_size for p in (ROOT/'recordings').rglob('*.mp4'))
    emit(f'Recorded file bytes: {total}')
    emit('Listeners: '+json.dumps(loopback_bindings()[1]))

def diagnostic():
    checks={}
    for name,item in state().items(): checks[name]={'running':alive(item),'log':item['log']}
    checks['utc']=utc();checks['bindings']=loopback_bindings()[1]
    checks['disk_free_bytes']=__import__('shutil').disk_usage(ROOT).free
    checks['config_permissions']={p.name:oct(p.stat().st_mode & 0o777) for p in (ROOT/'config').glob('*')}
    try: checks['paths']=http_json(9997,'/v3/paths/list','operator')
    except Exception as e: checks['api_error']=str(e)
    (ROOT/'evidence/diagnostics.json').write_text(sanitize(json.dumps(checks,indent=2))+'\n')
    emit(json.dumps({k:v for k,v in checks.items() if k!='paths'},indent=2))

def commission():
    """Run the full acceptance sequence with processes in one lifecycle."""
    stop_all()
    passed=False
    try:
        start_all()
        emit('ACCEPTANCE 1: live/record/export/authentication tests.')
        first=verify()
        emit('ACCEPTANCE 2: controlled camera outage and recorder restart.')
        second=faults()
        emit('ACCEPTANCE 3: repeat live/record/export checks after recovery.')
        third=verify()
        diagnostic()
        passed=first==second==third==0
    finally:
        stop_all()
        # Raw process logs are redacted for sharing after all writers close them.
        for log in (ROOT/'logs').glob('*.log'):
            log.write_text(sanitize(log.read_text(errors='replace')))
    (ROOT/'evidence/commissioning-result.json').write_text(json.dumps({
        'utc':utc(),'passed':passed,'mode':'software simulation',
        'services_stopped_after_test':True},indent=2)+'\n')
    emit('COMMISSIONING '+('PASS' if passed else 'FAIL'))
    return 0 if passed else 1

def serve():
    """Foreground lifecycle for two-terminal interview demonstrations."""
    start_all()
    emit('Foreground demo running. Ctrl+C stops this lab and preserves recordings.')
    try:
        while True:
            time.sleep(2)
            if __import__('shutil').disk_usage(ROOT).free<1073741824:
                raise RuntimeError('Disk guard reached: stopping before free space falls below 1 GiB.')
            if not all(alive(item) for item in state().values()):
                raise RuntimeError('A lab process exited. Run diagnostics and inspect logs.')
    except KeyboardInterrupt:
        pass
    finally:
        stop_all()

def show_command(cam):
    # Emits a redacted command and exact settings without exposing credentials.
    emit(f'Camera {cam}: RTSP/TCP at rtsp://127.30.0.10:8554/{cam}; viewer authentication required.')
    emit('Use VLC: Media -> Open Network Stream -> enter this URL -> supply viewer username/password.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['setup','start','serve','commission','stop','status','verify','faults','diagnostics','view'])
    parser.add_argument('--camera',default='cam01',choices=list(CAMERAS))
    args=parser.parse_args()
    for folder in ['config','runtime','logs','evidence','recordings','exports']: (ROOT/folder).mkdir(exist_ok=True)
    actions={'setup':setup,'start':start_all,'serve':serve,'commission':commission,'stop':stop_all,'status':status,'verify':verify,'faults':faults,'diagnostics':diagnostic,'view':lambda:show_command(args.camera)}
    try:
        result=actions[args.command]()
        return result if isinstance(result,int) else 0
    except Exception as e:
        emit('ERROR: '+sanitize(str(e)))
        return 1

if __name__=='__main__':
    sys.exit(main())
