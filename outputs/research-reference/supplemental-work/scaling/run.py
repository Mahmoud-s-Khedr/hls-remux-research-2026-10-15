import sys,os,json,time,subprocess,hashlib,random,statistics,platform,shutil,re,math
from pathlib import Path
import psutil

ROOT=Path(os.environ.get('HLS_SCALING_ROOT',Path(__file__).resolve().parents[2]))
WORK=ROOT/'work/scaling';OUT=ROOT/'outputs/hls-scaling'
SPECS=[
 ('mp4','MP4 (standard)','mp4',['-f','mp4']),
 ('mp4_faststart','MP4 (fast-start)','mp4',['-f','mp4','-movflags','+faststart']),
 ('mp4_fragmented','MP4 (fragmented)','mp4',['-f','mp4','-movflags','+frag_keyframe+delay_moov+default_base_moof']),
 ('mov','QuickTime / MOV','mov',['-f','mov']),('mkv','Matroska / MKV','mkv',['-f','matroska']),
 ('ts','MPEG-TS','ts',['-f','mpegts']),('m2ts','MPEG-TS (M2TS mode)','m2ts',['-f','mpegts','-mpegts_m2ts_mode','1']),
 ('avi','AVI','avi',['-f','avi']),('flv','Flash Video / FLV','flv',['-f','flv']),('f4v','Adobe F4V','f4v',['-f','f4v']),
 ('3gp','3GPP / 3GP','3gp',['-f','3gp']),('3g2','3GPP2 / 3G2','3g2',['-f','3g2']),('nut','NUT','nut',['-f','nut']),
 ('asf','ASF','asf',['-f','asf','-bsf:v','h264_mp4toannexb'])]
BASE=['ffmpeg','-hide_banner','-nostdin','-y','-loglevel','warning']
SOURCE=ROOT/'work/bbb_sunflower_1080p_30fps_normal.mp4'
DURATIONS=[('30s',30),('1m',60),('2m',120),('5m',300),('10m',600),('full',None)]
for d in ['logs','measurements','durations','scripts']: (OUT/d).mkdir(parents=True,exist_ok=True)
STATE=OUT/'results.json'

def run(args,log):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (OUT/'logs'/log).write_bytes(p.stderr)
 return p

def probe(path,packets=False):
 args=['ffprobe','-v','error','-show_streams','-show_format']
 if packets: args+=['-show_packets','-show_entries','packet=stream_index,pts_time,dts_time,duration_time,flags']
 p=subprocess.run(args+['-of','json',str(path)],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode()[:2000])
 return json.loads(p.stdout)

def save(r):
 tmp=STATE.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2));tmp.replace(STATE)

def freeguard():
 if shutil.disk_usage(OUT).free<5*1024**3:raise RuntimeError('Less than 5 GiB free; stopping before exhausting disk')

def populate(path):
 with path.open('rb') as f:
  while f.read(8*1024*1024):pass

def evict(path):
 fd=os.open(path,os.O_RDONLY)
 try:os.fsync(fd);os.posix_fadvise(fd,0,0,os.POSIX_FADV_DONTNEED)
 finally:os.close(fd)

def command(path,folder,kind):
 args=BASE+(['-fflags','+genpts'] if path.suffix=='.avi' else [])
 args+=['-i',str(path),'-map','0:v:0','-map','0:a:0','-c','copy','-f','hls','-hls_time','6',
  '-hls_playlist_type','vod','-hls_list_size','0','-hls_flags','independent_segments','-hls_segment_type',kind]
 if kind=='fmp4':args+=['-hls_fmp4_init_filename','init.mp4','-bsf:a','aac_adtstoasc']
 return args+['-hls_segment_filename',str(folder/('segment_%04d.'+('ts' if kind=='mpegts' else 'm4s'))),str(folder/'playlist.m3u8')]

def measure(case,tag,cache):
 path=OUT/case['input'];folder=OUT/Path(case['playlist']).parent
 (populate if cache=='warm' else evict)(path)
 label=case['id']+'-'+tag
 result=OUT/'measurements'/(label+'.json')
 spec={'command':case['command'],'log':str(OUT/'logs'/(label+'.log')),'folder':str(folder),'result':str(result)}
 specpath=WORK/'measurement-spec.json';specpath.write_text(json.dumps(spec))
 p=subprocess.run([sys.executable,str(WORK/'measure.py'),str(specpath)],capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode())
 data=json.loads(result.read_text());data.update(cache=cache,tag=tag,log='logs/'+label+'.log')
 data['cache_eviction_requested']=cache!='warm'
 return data

def main():
 r={'created_local':'2026-10-15 Africa/Cairo','ffmpeg':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
  'platform':platform.platform(),'cpu':subprocess.check_output(['lscpu'],text=True),
  'storage':subprocess.check_output(['lsblk','-o','NAME,TYPE,SIZE,ROTA,FSTYPE,MOUNTPOINTS'],text=True),
  'memory':psutil.virtual_memory()._asdict(),'swap':psutil.swap_memory()._asdict(),
  'logical_cpus':os.cpu_count(),'physical_cores':psutil.cpu_count(logical=False),
  'source_url':'https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip',
  'source_probe':probe(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
  'warm_repeats':5,'input_evicted_repeats':1,'durations':[],'status':'preparing'}
 save(r)
 for key,seconds in DURATIONS:
  freeguard();folder=OUT/'durations'/key
  for name in ['inputs','hls']:(folder/name).mkdir(parents=True,exist_ok=True)
  ts=WORK/(key+'-reference.ts');reference=folder/'reference.mp4'
  args=BASE+['-i',str(SOURCE)]+(['-t',str(seconds)] if seconds else [])
  args+=['-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-avoid_negative_ts','make_zero','-f','mpegts',str(ts)]
  p=run(args,key+'-reference-aac.log');assert p.returncode==0,p.stderr.decode()
  p=run(BASE+['-i',str(ts),'-map','0:v:0','-map','0:a:0','-c','copy',str(reference)],key+'-reference-mp4.log')
  assert p.returncode==0,p.stderr.decode();ts.unlink()
  duration={'key':key,'requested_seconds':seconds,'reference':str(reference.relative_to(OUT)),
   'probe':probe(reference),'cases':[]}
  duration['video_seconds']=float(duration['probe']['streams'][0]['duration'])
  r['durations'].append(duration);save(r)
  for name,label,ext,options in SPECS:
   freeguard();path=folder/'inputs'/(name+'.'+ext)
   p=run(BASE+['-i',str(reference),'-map','0:v:0','-map','0:a:0','-c','copy']+options+[str(path)],key+'-'+name+'-prepare.log')
   fi={'key':name,'container':label,'file':str(path.relative_to(OUT)),'prepare_ok':p.returncode==0,
    'prepare_log':'logs/'+key+'-'+name+'-prepare.log'}
   if p.returncode:fi['error']=p.stderr.decode();duration.setdefault('prepare_failures',[]).append(fi);continue
   fi['probe']=probe(path);fi['bytes']=path.stat().st_size
   for kind in ['mpegts','fmp4']:
    target=folder/'hls'/name/kind;target.mkdir(parents=True,exist_ok=True)
    case={'id':key+'-'+name+'-'+kind,'duration_key':key,'container_key':name,'container':label,'kind':kind,
     'input':fi['file'],'input_bytes':fi['bytes'],'input_probe':fi['probe'],
     'playlist':str((target/'playlist.m3u8').relative_to(OUT)),'command':command(path,target,kind),'runs':[]}
    case['warmup']=measure(case,'warmup','warm')
    case['mux_ok']=case['warmup']['returncode']==0
    duration['cases'].append(case)
   save(r)
   print('PREPARED',key,name,'free GiB',round(shutil.disk_usage(OUT).free/1024**3,1),flush=True)
 r['status']='timing';save(r)
 cases=[c for d in r['durations'] for c in d['cases']]
 rng=random.Random(20261015)
 # All remux measurements are serial and run before decoder/browser validation.
 for repeat in range(5):
  rng.shuffle(cases)
  for idx,c in enumerate(cases):
   c['runs'].append(measure(c,'warm-'+str(repeat+1),'warm'))
   if idx%28==27:print('WARM ROUND',repeat+1,'CASES',idx+1,'/',len(cases),flush=True);save(r)
  save(r)
 rng.shuffle(cases)
 for idx,c in enumerate(cases):
  c['runs'].append(measure(c,'input-evicted','input-evicted'))
  if idx%14==13:print('EVICTED CASES',idx+1,'/',len(cases),flush=True);save(r)
 for d in r['durations']:
  for c in d['cases']:
   warm=[x for x in c['runs'] if x['cache']=='warm'];cold=[x for x in c['runs'] if x['cache']!='warm']
   c['summary']={'all_runs_exit_ok':all(x['returncode']==0 for x in c['runs']),
    'warm_median_seconds':statistics.median(x['wall_seconds'] for x in warm),
    'warm_min_seconds':min(x['wall_seconds'] for x in warm),'warm_max_seconds':max(x['wall_seconds'] for x in warm),
    'warm_median_cpu_seconds':statistics.median(x['cpu_seconds'] for x in warm),
    'warm_median_cpu_percent':statistics.median(x['average_cpu_percent_one_core'] for x in warm),
    'peak_rss_bytes':max(x['peak_rss_bytes'] for x in c['runs']),
    'warm_median_logical_read_bytes':statistics.median(x['io']['rchar'] for x in warm),
    'warm_median_logical_write_bytes':statistics.median(x['io']['wchar'] for x in warm),
    'warm_median_storage_read_bytes':statistics.median(x['io']['read_bytes'] for x in warm),
    'warm_median_storage_write_bytes':statistics.median(x['io']['write_bytes'] for x in warm),
    'warm_median_flush_seconds':statistics.median(x['post_exit_fsync_seconds'] for x in warm),
    'warm_median_with_flush_seconds':statistics.median(x['completion_with_fsync_seconds'] for x in warm),
    'output_bytes':warm[-1]['output_bytes'],'output_file_count':warm[-1]['output_file_count'],
    'input_evicted':cold[0]}
 r['status']='timing_complete';r['memory_after_timing']=psutil.virtual_memory()._asdict();save(r)
 print('TIMING COMPLETE',flush=True)

if __name__=='__main__':main()
