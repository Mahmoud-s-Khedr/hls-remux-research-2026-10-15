"""Paired rerun: full-length standard MP4 -> HLS TS/fMP4, new output folder vs overwritten folder.

Reuses scripts/scaling/measure.py unchanged; command(), populate() and the
reference/input preparation are copied from scripts/scaling/run.py.
Usage: python3 rerun.py prepare | run
"""
import sys,os,json,time,subprocess,hashlib,random,shutil,platform,threading
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
OUT=REPO/'data/overwrite-rerun'
LOGS=REPO/'logs/overwrite-rerun'
MEASURE=REPO/'scripts/scaling/measure.py'
FRESH=REPO/'data/scaling/fresh-output.json'
MEDIA=Path(os.environ.get('HLS_RERUN_MEDIA',Path.home()/'Research/hls-rerun-media'))
SOURCE_SHA='ae51005850b0ff757fe60c3dd7a12d754d3cd2397d87d939b55235e457f97658'
BASE=['ffmpeg','-hide_banner','-nostdin','-y','-loglevel','warning']
KINDS=['mpegts','fmp4']
REPEATS=10
SEED=20261016
SETTLE_SECONDS=2
for d in [LOGS,OUT/'traces',MEDIA/'measurements']:d.mkdir(parents=True,exist_ok=True)
INPUT=MEDIA/'inputs/mp4.mp4'

def run(args,log):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (LOGS/log).write_bytes(p.stderr)
 if p.returncode:raise RuntimeError(p.stderr.decode()[-2000:])
 return p

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()

def populate(path):
 with path.open('rb') as f:
  while f.read(8*1024*1024):pass

def command(path,folder,kind):
 args=BASE+['-i',str(path),'-map','0:v:0','-map','0:a:0','-c','copy','-f','hls','-hls_time','6',
  '-hls_playlist_type','vod','-hls_list_size','0','-hls_flags','independent_segments','-hls_segment_type',kind]
 if kind=='fmp4':args+=['-hls_fmp4_init_filename','init.mp4','-bsf:a','aac_adtstoasc']
 return args+['-hls_segment_filename',str(folder/('segment_%04d.'+('ts' if kind=='mpegts' else 'm4s'))),str(folder/'playlist.m3u8')]

def expected(kind):
 cases=json.loads(FRESH.read_text())['cases']
 return next(c for c in cases if c['duration_key']=='full' and c['kind']==kind)['expected_sha256']

def hashes(folder):
 return {p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file()}

def environment():
 def cmd(a):
  try:return subprocess.run(a,capture_output=True,text=True,timeout=30).stdout
  except Exception as e:return 'unavailable: '+str(e)
 du=shutil.disk_usage(MEDIA)
 return {'time_local':time.strftime('%Y-%m-%d %H:%M:%S %Z'),'platform':platform.platform(),
  'ffmpeg':cmd(['ffmpeg','-version']).splitlines()[0],
  'governor':Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor').read_text().strip(),
  'disk_total_bytes':du.total,'disk_free_bytes':du.free,
  'fstype':cmd(['findmnt','-no','FSTYPE','--target',str(MEDIA)]).strip(),
  'lsblk':cmd(['lsblk','-o','NAME,TYPE,SIZE,ROTA,FSTYPE,MOUNTPOINTS']),
  'btrfs_usage':cmd(['btrfs','filesystem','usage','-b',str(MEDIA)]),
  'loadavg':os.getloadavg()}

class Sampler(threading.Thread):
 """Samples Dirty/Writeback from /proc/meminfo every 50 ms (same clock as measure.py)."""
 def __init__(s):super().__init__(daemon=True);s.samples=[];s.stop=threading.Event()
 def run(s):
  while not s.stop.is_set():
   m={k:int(v.split()[0]) for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines()) if k in ('Dirty','Writeback')}
   s.samples.append((time.perf_counter(),m['Dirty'],m['Writeback']));s.stop.wait(0.05)

def measure(kind,condition,repeat,folder,trace=False):
 populate(INPUT);os.sync();time.sleep(SETTLE_SECONDS)
 label=f'full-mp4-{kind}-{condition}-{repeat}'
 result=MEDIA/'measurements'/(label+'.json')
 spec={'command':command(INPUT,folder,kind),'log':str(LOGS/(label+'.log')),'folder':str(folder),'result':str(result)}
 specpath=MEDIA/'measurement-spec.json';specpath.write_text(json.dumps(spec))
 s=Sampler() if trace else None
 if s:s.start()
 p=subprocess.run([sys.executable,str(MEASURE),str(specpath)],capture_output=True)
 if s:
  s.stop.set();s.join()
 if p.returncode:raise RuntimeError(p.stderr.decode())
 data=json.loads(result.read_text())
 data.update(kind=kind,condition=condition,repeat=repeat,free_bytes_after=shutil.disk_usage(MEDIA).free)
 data['byte_identical']=hashes(folder)==expected(kind)
 result.write_text(json.dumps(data,indent=2))
 if s:(OUT/'traces'/(label+'.json')).write_text(json.dumps({'columns':['perf_counter','dirty_kB','writeback_kB'],
  'started':data['started_monotonic'],'exited':data['exited_monotonic'],'flushed':data['flushed_monotonic'],'samples':s.samples}))
 print(label,'wall %.2f cpu %.2f fsync %.2f total %.2f identical %s'%(data['wall_seconds'],data['cpu_seconds'],
  data['post_exit_fsync_seconds'],data['completion_with_fsync_seconds'],data['byte_identical']),flush=True)
 return data

def prepare():
 src=next((MEDIA/'download').glob('*.mp4'))
 assert sha(src)==SOURCE_SHA,'source SHA-256 mismatch'
 (MEDIA/'inputs').mkdir(exist_ok=True)
 ts=MEDIA/'full-reference.ts';reference=MEDIA/'reference.mp4'
 run(BASE+['-i',str(src),'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','128k',
  '-avoid_negative_ts','make_zero','-f','mpegts',str(ts)],'prepare-reference-aac.log')
 run(BASE+['-i',str(ts),'-map','0:v:0','-map','0:a:0','-c','copy',str(reference)],'prepare-reference-mp4.log');ts.unlink()
 run(BASE+['-i',str(reference),'-map','0:v:0','-map','0:a:0','-c','copy','-f','mp4',str(INPUT)],'prepare-input-mp4.log')
 out={'source':src.name,'source_sha256':SOURCE_SHA,'input_bytes':INPUT.stat().st_size,'input_sha256':sha(INPUT),'outputs':{}}
 for kind in KINDS:
  # Untimed warm-up: creates the persistent overwrite target and proves byte identity with the original study.
  folder=MEDIA/'overwrite'/kind
  if folder.exists():shutil.rmtree(folder)
  folder.mkdir(parents=True)
  run(command(INPUT,folder,kind),f'prepare-warmup-{kind}.log')
  got=hashes(folder);exp=expected(kind)
  out['outputs'][kind]={'files':len(got),'byte_identical_to_original':got==exp,
   'mismatched':sorted(k for k in set(got)|set(exp) if got.get(k)!=exp.get(k))[:20]}
 (OUT/'prepare.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

def experiment():
 rng=random.Random(SEED);results={'seed':SEED,'repeats':REPEATS,'settle_seconds':SETTLE_SECONDS,
  'environment_start':environment(),'order':[],'runs':[]}
 for repeat in range(1,REPEATS+1):
  kinds=KINDS[:];rng.shuffle(kinds)
  for kind in kinds:
   conds=['new','overwrite'];rng.shuffle(conds)
   for cond in conds:
    results['order'].append(f'{repeat}-{kind}-{cond}')
    if cond=='new':
     folder=MEDIA/'new'/f'{kind}-{repeat}';folder.mkdir(parents=True,exist_ok=False)
    else:folder=MEDIA/'overwrite'/kind
    results['runs'].append(measure(kind,cond,repeat,folder,trace=repeat==1))
    if cond=='new':shutil.rmtree(folder)
 results['environment_end']=environment()
 (OUT/'results.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__':
 {'prepare':prepare,'run':experiment}[sys.argv[1]]()
