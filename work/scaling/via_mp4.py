import json,time,sys,shutil
from pathlib import Path
import run as b
import validate as v
ROOT=b.ROOT; ORIGINAL=b.OUT; OUT=ROOT/'outputs/hls-via-mp4';b.OUT=OUT;v.OUT=OUT
(OUT/'logs').mkdir(parents=True,exist_ok=True)
state=json.loads((ORIGINAL/'results.json').read_text())
result={'purpose':'Exploratory stream-copy AVI/ASF -> MP4 -> HLS TS; no re-encoding or timestamp repair beyond optional genpts','method':'One untimed-cache-controlled attempt per case; wall times are diagnostic, not comparable benchmark medians','cases':[]}
for key in ['30s','full']:
 d=next(d for d in state['durations'] if d['key']==key)
 ref=ORIGINAL/d['reference']; ident=v.canonical(ref,key+'-reference');pack=b.probe(ref,True)
 for container in ['avi','asf']:
  source=ORIGINAL/next(c['input'] for c in d['cases'] if c['container_key']==container)
  for mode in ['default','genpts']:
   label=f'{key}-{container}-{mode}';folder=OUT/label;folder.mkdir(exist_ok=True)
   middle=folder/'intermediate.mp4';hls=folder/'hls';hls.mkdir(exist_ok=True)
   cmd=b.BASE+(['-fflags','+genpts'] if mode=='genpts' else [])+['-i',str(source),'-map','0:v:0','-map','0:a:0','-c','copy',str(middle)]
   started=time.perf_counter();p=b.run(cmd,label+'-to-mp4.log')
   c={'id':label,'source':str(source),'mp4_command':cmd,'mp4_returncode':p.returncode,'mp4_wall_seconds':time.perf_counter()-started,'mp4_log':'logs/'+label+'-to-mp4.log'}
   if p.returncode==0:
    cmd=b.command(middle,hls,'mpegts');started=time.perf_counter();p=b.run(cmd,label+'-to-hls.log')
    c.update(hls_command=cmd,hls_returncode=p.returncode,hls_wall_seconds=time.perf_counter()-started,hls_log='logs/'+label+'-to-hls.log')
    if p.returncode==0:
     try:c['validation']=v.validate({'id':label,'playlist':str((hls/'playlist.m3u8').relative_to(OUT)),'kind':'mpegts'},ident,pack)
     except Exception as e:c['validation_error']=str(e)
   c['passed']=c.get('validation',{}).get('passed',False)
   result['cases'].append(c);(OUT/'results.json').write_text(json.dumps(result,indent=2))
   print(label,'MP4',c['mp4_returncode'],'HLS',c.get('hls_returncode'),'PASS',c['passed'],'timing',c.get('validation',{}).get('timing',{}),flush=True)
shutil.copy2(__file__,OUT/'scripts/via_mp4.py')
for name in ['run.py','validate.py']:shutil.copy2(Path(__file__).parent/name,OUT/'scripts'/name)
