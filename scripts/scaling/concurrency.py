import json,time,subprocess,statistics,shutil,os,sys
from pathlib import Path
import psutil
import run as b

def main():
 r=json.loads(b.STATE.read_text());full=next(d for d in r['durations'] if d['key']=='full')
 results={'input':'full-source standard MP4, warm/pre-read','groups':[],'sampling_interval_seconds':.01}
 for kind in ['mpegts','fmp4']:
  template=next(c for c in full['cases'] if c['container_key']=='mp4' and c['kind']==kind)
  for workers in [1,2,4]:
   for repeat in range(3):
    b.populate(b.OUT/template['input'])
    group=b.WORK/'concurrency'/kind/str(workers)/str(repeat)
    processes=[];paths=[]
    for i in range(workers):
     folder=group/str(i);folder.mkdir(parents=True,exist_ok=True)
     result=folder/'resource.json';spec=folder/'spec.json'
     spec.write_text(json.dumps({'command':b.command(b.OUT/template['input'],folder,kind),
      'folder':str(folder),'result':str(result),'log':str(folder/'ffmpeg.log')}))
     paths.append(result)
     processes.append(subprocess.Popen([sys.executable,str(b.WORK/'measure.py'),str(spec)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE))
    samples=[]
    while any(p.poll() is None for p in processes):
     rss=0;cpu=0;active=0
     for p in processes:
      try:
       for child in psutil.Process(p.pid).children(recursive=True):
        if child.name()=='ffmpeg':
         rss+=child.memory_info().rss;ct=child.cpu_times();cpu+=ct.user+ct.system;active+=1
      except (psutil.NoSuchProcess,psutil.AccessDenied):pass
     samples.append({'monotonic':time.perf_counter(),'aggregate_rss_bytes':rss,'live_ffmpeg_processes':active,'live_process_cpu_seconds':cpu})
     time.sleep(.01)
    for p in processes:
     if p.returncode:raise RuntimeError(p.stderr.read().decode())
    jobs=[json.loads(p.read_text()) for p in paths]
    start=min(x['started_monotonic'] for x in jobs);end=max(x['exited_monotonic'] for x in jobs)
    flushed=max(x['flushed_monotonic'] for x in jobs)
    data={'kind':kind,'workers':workers,'repeat':repeat+1,'jobs':jobs,'remux_batch_seconds':end-start,
     'batch_with_flush_seconds':flushed-start,'jobs_per_second':workers/(end-start),
     'average_job_seconds':statistics.mean(x['wall_seconds'] for x in jobs),
     'aggregate_cpu_seconds':sum(x['cpu_seconds'] for x in jobs),
     'aggregate_average_cpu_percent':100*sum(x['cpu_seconds'] for x in jobs)/(end-start),
     'sampled_peak_aggregate_rss_bytes':max(x['aggregate_rss_bytes'] for x in samples),
     'sum_of_individual_peak_rss_bytes':sum(x['peak_rss_bytes'] for x in jobs),
     'all_exit_ok':all(x['returncode']==0 for x in jobs),'samples':samples}
    results['groups'].append(data)
    (b.OUT/'concurrency.json').write_text(json.dumps(results,indent=2))
    print('CONCURRENCY',kind,'workers',workers,'run',repeat+1,'seconds',round(end-start,3),flush=True)
    shutil.rmtree(group)
 print('CONCURRENCY COMPLETE',flush=True)

if __name__=='__main__':main()
