import json,statistics,hashlib,shutil
from pathlib import Path
import run as b

def fingerprint(folder):
 return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.suffix in ['.m3u8','.ts','.m4s','.mp4']}

def main():
 r=json.loads(b.STATE.read_text());results={'method':'Fresh destination directory for every run, standard MP4 input only; five pre-read runs and one input-evicted run; exact file hashes compared with retained matrix output','cases':[]}
 for d in r['durations']:
  for kind in ['mpegts','fmp4']:
   template=next(c for c in d['cases'] if c['container_key']=='mp4' and c['kind']==kind)
   expected=fingerprint((b.OUT/template['playlist']).parent)
   runs=[];matches=[];hashes=[];parent=b.WORK/'fresh'/d['key']/kind
   for i in range(6):
    folder=parent/str(i);folder.mkdir(parents=True,exist_ok=False)
    c={'id':'fresh-'+d['key']+'-'+kind+'-'+str(i),'input':template['input'],
      'playlist':str(folder/'playlist.m3u8'),'command':b.command(b.OUT/template['input'],folder,kind)}
    resource=b.measure(c,'run','warm' if i<5 else 'input-evicted')
    actual=fingerprint(folder);runs.append(resource);matches.append(actual==expected);hashes.append(actual)
   warm=runs[:5];cold=runs[5]
   summary={'warm_median_seconds':statistics.median(x['wall_seconds'] for x in warm),
    'warm_min_seconds':min(x['wall_seconds'] for x in warm),'warm_max_seconds':max(x['wall_seconds'] for x in warm),
    'warm_median_cpu_seconds':statistics.median(x['cpu_seconds'] for x in warm),
    'warm_median_cpu_percent':statistics.median(x['average_cpu_percent_one_core'] for x in warm),
    'peak_rss_bytes':max(x['peak_rss_bytes'] for x in runs),
    'warm_median_storage_read_bytes':statistics.median(x['io']['read_bytes'] for x in warm),
    'warm_median_storage_write_bytes':statistics.median(x['io']['write_bytes'] for x in warm),
    'warm_median_flush_seconds':statistics.median(x['post_exit_fsync_seconds'] for x in warm),
    'warm_median_with_flush_seconds':statistics.median(x['completion_with_fsync_seconds'] for x in warm),
    'output_bytes':warm[-1]['output_bytes'],'input_evicted':cold}
   results['cases'].append({'duration_key':d['key'],'kind':kind,'input':template['input'],
    'runs':runs,'summary':summary,'all_byte_identical_to_retained_output':all(matches),
    'per_run_hash_match':matches,'output_sha256_by_run':hashes,'expected_sha256':expected,
    'all_exit_ok':all(x['returncode']==0 for x in runs)})
   (b.OUT/'fresh-output.json').write_text(json.dumps(results,indent=2))
   print('FRESH',d['key'],kind,'median',round(summary['warm_median_seconds'],3),'hash match',all(matches),flush=True)
   shutil.rmtree(parent)
 print('FRESH OUTPUT COMPLETE',flush=True)

if __name__=='__main__':main()
