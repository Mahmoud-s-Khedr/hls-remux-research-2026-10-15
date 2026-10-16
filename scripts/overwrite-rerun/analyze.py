"""Print the overwrite-rerun summary tables from data/overwrite-rerun/ (results.json and traces/)."""
import json,statistics as st
from pathlib import Path

OUT=Path(__file__).resolve().parents[2]/'data/overwrite-rerun'
R=json.loads((OUT/'results.json').read_text())
runs=R['runs']
METRICS=[('wall_seconds','FFmpeg exit s'),('cpu_seconds','CPU s'),('post_exit_fsync_seconds','fsync s'),('completion_with_fsync_seconds','Exit + fsync s')]
KIND={'mpegts':'TS','fmp4':'fMP4'}

def q(v):
 v=sorted(v);qs=st.quantiles(v,n=4,method='inclusive')
 return {'median':st.median(v),'min':v[0],'max':v[-1],'q1':qs[0],'q3':qs[2],'n':len(v)}

analysis={'conditions':{},'paired':{},'traces':{}}
lines=['| Output | Folder | n | '+' | '.join(f'{label} median (IQR)' for _,label in METRICS)+' | Byte-identical |','|'+'---|'*(4+len(METRICS))]
for kind in ['mpegts','fmp4']:
 for cond in ['new','overwrite']:
  rs=[r for r in runs if r['kind']==kind and r['condition']==cond]
  s={m:q([r[m] for r in rs]) for m,_ in METRICS}
  s['all_exit_ok']=all(r['returncode']==0 for r in rs);s['all_byte_identical']=all(r['byte_identical'] for r in rs)
  analysis['conditions'][f'{kind}-{cond}']=s
  cells=' | '.join(f"{s[m]['median']:.2f} ({s[m]['q1']:.2f}–{s[m]['q3']:.2f})" for m,_ in METRICS)
  lines.append(f"| {KIND[kind]} | {cond} | {len(rs)} | {cells} | {'all' if s['all_byte_identical'] else 'NO'} |")

lines+=['','| Output | Metric | Median paired difference, overwrite − new (s) | Overwrite slower in |','|---|---|---|---|']
for kind in ['mpegts','fmp4']:
 by={(r['repeat'],r['condition']):r for r in runs if r['kind']==kind}
 reps=sorted({r for r,_ in by})
 for m,label in METRICS:
  d=[by[(i,'overwrite')][m]-by[(i,'new')][m] for i in reps]
  analysis['paired'][f'{kind}-{m}']={'differences':d,'median':st.median(d),'overwrite_slower':sum(x>0 for x in d),'n':len(d)}
  lines.append(f"| {KIND[kind]} | {label} | {st.median(d):+.2f} | {sum(x>0 for x in d)}/{len(d)} |")

lines+=['','Kernel writeback during repeat 1 (`/proc/meminfo`, sampled every 50 ms; MiB):','','| Output | Folder | Peak Writeback while FFmpeg runs | Peak Dirty while FFmpeg runs | Peak Writeback during fsync |','|---|---|---|---|---|']
for p in sorted((OUT/'traces').glob('*.json')):
 t=json.loads(p.read_text());s=t['samples']
 during=[x for x in s if t['started']<=x[0]<=t['exited']];after=[x for x in s if t['exited']<x[0]<=t['flushed']]
 wb_run=max((x[2] for x in during),default=0)/1024;dirty_run=max((x[1] for x in during),default=0)/1024
 wb_sync=max((x[2] for x in after),default=0)/1024
 name=p.stem;kind='fmp4' if '-fmp4-' in name else 'mpegts';cond='overwrite' if '-overwrite-' in name else 'new'
 analysis['traces'][name]={'samples_during_ffmpeg':len(during),'peak_writeback_mib_during_ffmpeg':wb_run,
  'peak_dirty_mib_during_ffmpeg':dirty_run,'peak_writeback_mib_during_fsync':wb_sync}
 lines.append(f"| {KIND[kind]} | {cond} | {wb_run:.1f} | {dirty_run:.1f} | {wb_sync:.1f} |")

e0,e1=R['environment_start'],R['environment_end']
analysis['environment']={'governor':e0['governor'],'fstype':e0['fstype'],'free_gib_start':e0['disk_free_bytes']/2**30,
 'free_gib_end':e1['disk_free_bytes']/2**30,'used_pct_start':100*(1-e0['disk_free_bytes']/e0['disk_total_bytes']),'ffmpeg':e0['ffmpeg']}
print('\n'.join(lines));print(json.dumps(analysis['environment'],indent=1))
