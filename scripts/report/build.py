"""Build every chart in charts/ and every generated table in REPORT.md from data/.

Usage: python3 -I scripts/report/build.py
REPORT.md keeps its prose; text between <!-- gen:NAME --> and <!-- /gen --> is regenerated.
"""
import json,re,statistics as st
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data';CHARTS=ROOT/'charts';REPORT=ROOT/'REPORT.md'
CHARTS.mkdir(exist_ok=True)

# ---------- palette (dataviz reference palette, light surface; validated) ----------
SURFACE='#fcfcfb';INK='#0b0b0b';INK2='#52514e';MUTED='#898781';GRID='#e1e0d9';AXIS='#c3c2b7'
S1,S2,S3='#2a78d6','#eb6834','#1baf7a'          # categorical slots 1-3 (TS, fMP4, third)
KC={'mpegts':S1,'fmp4':S2};KL={'mpegts':'TS','fmp4':'fMP4'}
plt.rcParams.update({'figure.facecolor':SURFACE,'axes.facecolor':SURFACE,'savefig.facecolor':SURFACE,
 'font.size':10,'font.family':'DejaVu Sans','axes.edgecolor':AXIS,'axes.labelcolor':INK2,'text.color':INK,
 'xtick.color':MUTED,'ytick.color':MUTED,'axes.grid':True,'grid.color':GRID,'grid.linewidth':0.6,
 'axes.spines.top':False,'axes.spines.right':False,'axes.titlesize':11,'axes.titleweight':'bold',
 'axes.titlecolor':INK,'axes.titlelocation':'left','lines.linewidth':2,'lines.markersize':6,'legend.frameon':False})

def save(fig,name,source):
 fig.text(0.01,0.005,'Source: '+source,fontsize=7.5,color=MUTED,ha='left',va='bottom')
 fig.savefig(CHARTS/name,dpi=150,bbox_inches='tight');plt.close(fig)

def endlabel(ax,x,y,text,color,dy=0):
 ax.annotate(text,(x,y),xytext=(6,dy),textcoords='offset points',va='center',fontsize=9,color=INK2,
  bbox=dict(boxstyle='square,pad=0.1',fc=SURFACE,ec='none'))

# ---------- load ----------
R=json.loads((DATA/'scaling/results.json').read_text())
FRESH=json.loads((DATA/'scaling/fresh-output.json').read_text())
CONC=json.loads((DATA/'scaling/concurrency.json').read_text())
RERUN=json.loads((DATA/'overwrite-rerun/results.json').read_text())
VIA=json.loads((DATA/'via-mp4/results.json').read_text())
BASE=json.loads((DATA/'baseline-30s/results.json').read_text())
BROWSER=json.loads((DATA/'scaling/browser-validation.json').read_text())
LEN=['30s','1m','2m','5m','10m','full']
LENL={'30s':'30 s','1m':'1 min','2m':'2 min','5m':'5 min','10m':'10 min','full':'Full (10:34.6)'}
VSEC={d['key']:d['video_seconds'] for d in R['durations']}
CASES={c['id']:c for d in R['durations'] for c in d['cases']}
CONTAINERS=[(c['container_key'],c['container']) for c in R['durations'][0]['cases'] if c['kind']=='mpegts']
def case(L,ck,kind):return CASES[f'{L}-{ck}-{kind}']
def med(v):return st.median(v)
MB=1e6;MiB=2**20
fresh={(c['duration_key'],c['kind']):c for c in FRESH['cases']}
T={}  # generated markdown blocks

def table(head,rows):
 return '\n'.join(['| '+' | '.join(head)+' |','|'+'---|'*len(head)]+['| '+' | '.join(str(x) for x in r)+' |' for r in rows])

# ---------- compatibility ----------
rows=[]
for ck,label in CONTAINERS:
 p={k:sum(case(L,ck,k)['overall_passed'] for L in LEN) for k in KL}
 reasons=sorted({case(L,ck,k)['failure_reason'] for L in LEN for k in KL if not case(L,ck,k)['overall_passed']})
 mark=lambda n:('✅ ' if n==6 else '❌ ')+f'{n}/6'
 rows.append([label,mark(p['mpegts']),mark(p['fmp4']),'; '.join(reasons) or '—'])
npass=sum(c['overall_passed'] for c in CASES.values())
T['compat']=table(['Input container / layout','HLS TS (6 lengths)','HLS fMP4 (6 lengths)','Rejection reason'],rows)+\
 f'\n\n**{npass}/{len(CASES)} paths accepted.**'

rows=[]
for ck in ['avi','asf']:
 for k in KL:
  c=case('full',ck,k);v=c['validation'];t=v.get('timing',{})
  err=max((s['max_error_seconds'] for s in t.get('streams',{}).values()),default=None)
  rows.append([dict(CONTAINERS)[ck],KL[k],'yes' if c['summary']['all_runs_exit_ok'] else 'no',
   'video ✓ audio ✓' if v.get('video_payload_matches') and v.get('audio_payload_matches') else 'not produced',
   f"{v['playlist_seconds']:.1f}" if 'playlist_seconds' in v else '—',
   v.get('target_duration_seconds','—'),
   f'{err*1000:.1f}' if err is not None else '—',
   f"{t['actual_video_minus_audio_start']*1000:.0f} (ref 88)" if t else '—',c['failure_reason']])
T['failures']=table(['Input','Output','FFmpeg exit 0','Compressed payload identical','Playlist s','Target duration','Max video PTS error ms','Video−audio start ms','Rejected for'],rows)

rows=[]
for c in VIA['cases']:
 v=c['validation'];t=v.get('timing',{})
 err=max((s['max_error_seconds'] for s in t.get('streams',{}).values()),default=None)
 L,ck,mode=c['id'].split('-')
 rows.append([LENL[L],ck.upper(),mode,c['mp4_returncode'],c['hls_returncode'],f'{err*1000:.1f}' if err is not None else '—',
  f"{t['actual_video_minus_audio_start']*1000:.0f}" if t else '—',t.get('dts_strictly_increasing','—'),'yes' if c['passed'] else 'no'])
T['via_mp4']=table(['Length','Input','Timestamps','MP4 exit','HLS exit','Max PTS error ms','Video−audio start ms','DTS increasing','Accepted'],rows)

# baseline frame-level verification
ok=tot=0
for fx in BASE['fixtures']:
 for k,o in fx['outputs'].items():
  v=o.get('validation') or {};tot+=1
  ok+=bool(v.get('video_matches_source') and v.get('audio_matches_source'))
T['baseline']=f'{ok}/{tot} 30-second outputs decoded to frames and PCM audio identical to the reference (900/900 frames each), checked with per-frame MD5 (`data/baseline-30s/framemd5/`).'

tests=BROWSER['tests'];bp=sum(t['passed'] for t in tests)
T['browser']=f"{bp}/{len(tests)} accepted outputs passed the browser check (Chromium {BROWSER['browser']}, {BROWSER['player']}): startup, mid seek, near-end seek, play to end, no player/media errors."

# ---------- segments ----------
def extinf(L,ck,kind):
 p=DATA/f'scaling/playlists/{L}/hls/{ck}/{kind}/playlist.m3u8';txt=p.read_text()
 return [float(x) for x in re.findall(r'#EXTINF:([0-9.]+)',txt)],int(re.search(r'TARGETDURATION:(\d+)',txt).group(1))
rows=[]
for L in LEN:
 d,td=extinf(L,'mp4','mpegts')
 rows.append([LENL[L],len(d),f'{min(d):.2f}',f'{med(d):.2f}',f'{max(d):.2f}',td,sum(x>6.5 for x in d)])
T['segments']=table(['Length','Segments','Shortest s','Median s','Longest s','EXT-X-TARGETDURATION','Segments > 6.5 s'],rows)

# ---------- fresh control (production-like: new folder per job) ----------
rows=[]
for L in LEN:
 for k in KL:
  c=fresh[(L,k)];s=c['summary'];ib=case(L,'mp4',k)['input_bytes']
  rows.append([LENL[L],KL[k],f'{ib/MB:.1f}',f"{s['warm_median_seconds']:.3f}",f"{s['warm_median_with_flush_seconds']:.3f}",
   f"{s['warm_median_cpu_seconds']:.3f}",f"{s['warm_median_cpu_percent']:.0f}",f"{s['peak_rss_bytes']/MiB:.1f}",
   f"{s['warm_median_storage_write_bytes']/MB:.1f}",'yes' if c['all_byte_identical_to_retained_output'] else 'NO'])
T['fresh']=table(['Length','Output','Input MB','FFmpeg exit s','Exit + fsync s','CPU s','CPU % of 1 core','Peak RSS MiB','Storage write MB','Output byte-identical'],rows)

# CPU fit (fresh control, CPU vs input MB)
def fit(x,y):
 mx,my=st.mean(x),st.mean(y);b=sum((a-mx)*(c-my) for a,c in zip(x,y))/sum((a-mx)**2 for a in x);a=my-b*mx
 ss=sum((c-(a+b*q))**2 for q,c in zip(x,y));tt=sum((c-my)**2 for c in y);return a,b,1-ss/tt
fits={}
for k in KL:
 x=[case(L,'mp4',k)['input_bytes']/MB for L in LEN];y=[fresh[(L,k)]['summary']['warm_median_cpu_seconds'] for L in LEN]
 fits[k]=fit(x,y)
T['cpu_fit']='\n'.join(f"- {KL[k]}: `CPU_seconds ≈ {a:.3f} + {b*1000:.2f} × input_GB` (six points, R² = {r2:.3f}): about **{a:.2f} s fixed** per job plus **{b*1000:.2f} CPU-s per GB** of input."
 for k,(a,b,r2) in fits.items())

# ---------- CPU / RSS by container, full length ----------
rows=[]
for ck,label in CONTAINERS:
 r=[label]
 for k in KL:
  c=case('full',ck,k);s=c['summary']
  r+=[f"{s['warm_median_cpu_seconds']:.2f}",f"{s['peak_rss_bytes']/MiB:.0f}"]
 r.append('accepted' if case('full',ck,'mpegts')['overall_passed'] and case('full',ck,'fmp4')['overall_passed'] else 'rejected')
 rows.append(r)
T['containers']=table(['Input (full length)','TS CPU s','TS peak RSS MiB','fMP4 CPU s','fMP4 peak RSS MiB','Status'],rows)

# matrix resources (standard MP4) — CPU/RSS/I-O are valid in the overwrite matrix; wall time is not
rows=[]
for L in LEN:
 for k in KL:
  s=case(L,'mp4',k)['summary']
  rows.append([LENL[L],KL[k],f"{s['warm_median_cpu_seconds']:.3f}",f"{s['peak_rss_bytes']/MiB:.1f}",
   f"{s['warm_median_logical_read_bytes']/MB:.1f}",f"{s['warm_median_logical_write_bytes']/MB:.1f}",
   f"{s['input_evicted']['io']['read_bytes']/MB:.1f}",f"{s['warm_median_storage_write_bytes']/MB:.1f}",s['output_file_count']])
T['matrix_resources']=table(['Length','Output','CPU s','Peak RSS MiB','Logical read MB','Logical write MB','Storage read MB (input evicted)','Storage write MB','Output files'],rows)

# ---------- overwrite vs new ----------
def big(runs):return [r for r in runs if r['io']['write_bytes']>2e8]
groups=[]
wu=big([c['warmup'] for c in CASES.values()]);rep=big([r for c in CASES.values() for r in c['runs'] if r['cache']=='warm'])
ev=big([r for c in CASES.values() for r in c['runs'] if r['cache']!='warm']);fr=big([r for c in FRESH['cases'] for r in c['runs']])
groups=[('Original: warm-up (new files)',wu),('Original: repeats (overwrite)',rep),('Original: input-evicted (overwrite)',ev),
 ('Original: fresh control (new files)',fr),
 ('Rerun: new folder',[r for r in RERUN['runs'] if r['condition']=='new']),('Rerun: overwrite',[r for r in RERUN['runs'] if r['condition']=='overwrite'])]
rows=[[g,len(v),f"{med([r['wall_seconds'] for r in v]):.2f}",f"{med([r['cpu_seconds'] for r in v]):.2f}",
 f"{med([r['post_exit_fsync_seconds'] for r in v]):.2f}",f"{med([r['completion_with_fsync_seconds'] for r in v]):.2f}"] for g,v in groups]
pairs=[(c['warmup']['wall_seconds'],med([r['wall_seconds'] for r in c['runs'] if r['cache']=='warm'])) for c in CASES.values() if c['warmup']['io']['write_bytes']>2e8]
T['overwrite']=table(['Runs (outputs ≥ 200 MB)','n','FFmpeg exit s','CPU s','fsync s','Exit + fsync s'],rows)+\
 f"\n\nOriginal session: the new-folder warm-up was faster than the same case's overwrite median in **{sum(a<b for a,b in pairs)}/{len(pairs)}** cases."
e0=RERUN['environment_start']
T['rerun_env']=f"Rerun: {e0['time_local']}, {e0['disk_free_bytes']/2**30:.0f} GiB free on the {e0['disk_total_bytes']/2**30:.0f} GiB {e0['fstype']} volume, governor `{e0['governor']}`, {e0['ffmpeg'].split(' Copyright')[0]}."

# paired rerun table
rows=[]
for k in KL:
 by={(r['repeat'],r['condition']):r for r in RERUN['runs'] if r['kind']==k}
 for m,lab in [('wall_seconds','FFmpeg exit s'),('cpu_seconds','CPU s'),('post_exit_fsync_seconds','fsync s'),('completion_with_fsync_seconds','Exit + fsync s')]:
  d=[by[(i,'overwrite')][m]-by[(i,'new')][m] for i in range(1,RERUN['repeats']+1)]
  rows.append([KL[k],lab,f"{med([by[(i,'new')][m] for i in range(1,11)]):.2f}",f"{med([by[(i,'overwrite')][m] for i in range(1,11)]):.2f}",f'{med(d):+.2f}',f'{sum(x>0 for x in d)}/{len(d)}'])
T['rerun']=table(['Output','Metric','New folder (median)','Overwrite (median)','Paired difference (median)','Overwrite higher in'],rows)
tr=[]
for p in sorted((DATA/'overwrite-rerun/traces').glob('*.json')):
 t=json.loads(p.read_text());s=t['samples'];dur=[x for x in s if t['started']<=x[0]<=t['exited']]
 tr.append([KL['fmp4' if '-fmp4-' in p.stem else 'mpegts'],'overwrite' if '-overwrite-' in p.stem else 'new',f"{max(x[1] for x in dur)/1024:.0f}"])
T['traces']=table(['Output','Folder','Peak dirty page cache while FFmpeg runs, MiB'],tr)

# ---------- concurrency ----------
rows=[];conc={}
for k in KL:
 for w in (1,2,4):
  g=[x for x in CONC['groups'] if x['kind']==k and x['workers']==w]
  m=lambda f:med([f(x) for x in g])
  c={'batch':m(lambda x:x['remux_batch_seconds']),'jps':m(lambda x:x['jobs_per_second']),'job':m(lambda x:x['average_job_seconds']),
   'cpu':m(lambda x:x['aggregate_average_cpu_percent']),'rss':m(lambda x:x['sampled_peak_aggregate_rss_bytes'])/MiB,
   'flush':m(lambda x:x['batch_with_flush_seconds']),'ok':all(x['all_exit_ok'] for x in g),'n':len(g)}
  c['fjps']=w/c['flush'];conc[(k,w)]=c
  rows.append([KL[k],w,c['n'],f"{c['batch']:.2f}",f"{c['job']:.2f}",f"{c['jps']:.2f}",f"{c['cpu']:.0f}",f"{c['rss']:.0f}",f"{c['flush']:.1f}",f"{c['fjps']:.2f}"])
T['concurrency']=table(['Output','Parallel jobs','Repeats','Batch exit s','Mean job exit s','Exit jobs/s','Aggregate CPU %','Sampled peak RSS MiB (sum)','Batch + fsync s','Jobs/s incl. fsync'],rows)

# ---------- warm-round drift ----------
rows=[]
for i in range(1,6):
 rr=[c['runs'][i-1] for c in CASES.values() if c['overall_passed']]
 rows.append([i,f"{med([r['wall_seconds'] for r in rr]):.3f}",f"{med([r['cpu_seconds'] for r in rr]):.3f}",f"{med([r['post_exit_fsync_seconds'] for r in rr]):.3f}"])
T['drift']=table(['Warm round','Median FFmpeg exit s (accepted cases)','Median CPU s','Median fsync s'],rows)

# ---------- full matrix appendix ----------
rows=[]
for L in LEN:
 for ck,label in CONTAINERS:
  for k in KL:
   c=case(L,ck,k);s=c['summary']
   rows.append([LENL[L],label,KL[k],f"{c['input_bytes']/MB:.1f}",f"{s['warm_median_cpu_seconds']:.3f}",f"{s['peak_rss_bytes']/MiB:.1f}",
    f"{s['warm_median_storage_write_bytes']/MB:.1f}",f"{s['warm_median_seconds']:.3f}",f"{s['warm_min_seconds']:.2f}–{s['warm_max_seconds']:.2f}",
    'PASS' if c['overall_passed'] else 'FAIL',c['failure_reason'] or ''])
T['matrix']=table(['Length','Input','Output','Input MB','CPU s','Peak RSS MiB','Storage write MB','Exit s (overwrite, see §7)','Exit range s','Result','Finding'],rows)

# ================= charts =================
mins=[VSEC[L]/60 for L in LEN]
# 1. resource scaling (fresh control)
fig,axs=plt.subplots(1,3,figsize=(12,3.6))
specs=[('CPU seconds per job',lambda L,k:fresh[(L,k)]['summary']['warm_median_cpu_seconds'],'{:.2f}'),
 ('Peak memory (RSS), MiB',lambda L,k:fresh[(L,k)]['summary']['peak_rss_bytes']/MiB,'{:.0f}'),
 ('Data written, MB',lambda L,k:fresh[(L,k)]['summary']['warm_median_storage_write_bytes']/MB,'{:.0f}')]
for ax,(title,f,fmt) in zip(axs,specs):
 ys={k:[f(L,k) for L in LEN] for k in KL};top=max(KL,key=lambda k:ys[k][-1])
 for k in KL:
  y=ys[k];ax.plot(mins,y,'-o',color=KC[k],markeredgecolor=SURFACE,markeredgewidth=1.5)
  endlabel(ax,mins[-1],y[-1],f'{KL[k]} {fmt.format(y[-1])}',KC[k],dy=(8 if k==top else -8))
 ax.set_title(title);ax.set_xlabel('Video length, minutes');ax.set_ylim(bottom=0);ax.set_xlim(0,13.5)
fig.suptitle('Remux cost grows with file size; memory stays near 90 MiB',x=0.01,ha='left',fontsize=12.5,fontweight='bold')
fig.tight_layout(rect=(0,0.03,1,1));save(fig,'resources.png','data/scaling/fresh-output.json (standard MP4, new output folder per job, median of 5)')

# 2. completion: exit vs exit+fsync
fig,axs=plt.subplots(1,2,figsize=(10,3.6),sharey=True)
for ax,k in zip(axs,KL):
 e=[fresh[(L,k)]['summary']['warm_median_seconds'] for L in LEN];t=[fresh[(L,k)]['summary']['warm_median_with_flush_seconds'] for L in LEN]
 ax.plot(mins,t,'-o',color=KC[k],markeredgecolor=SURFACE,markeredgewidth=1.5);ax.plot(mins,e,'--o',color=KC[k],alpha=.55,markeredgecolor=SURFACE,markeredgewidth=1.5)
 endlabel(ax,mins[-1],t[-1],f'exit + fsync {t[-1]:.1f} s',KC[k]);endlabel(ax,mins[-1],e[-1],f'FFmpeg exit {e[-1]:.1f} s',KC[k])
 ax.set_title(f'HLS {KL[k]}');ax.set_xlabel('Video length, minutes');ax.set_xlim(0,16)
axs[0].set_ylabel('Seconds');axs[0].set_ylim(bottom=0)
fig.suptitle('FFmpeg finishes in under 1 s; getting the data onto this (degraded) disk took up to 8 s',x=0.01,ha='left',fontsize=12.5,fontweight='bold')
fig.tight_layout(rect=(0,0.03,1,1));save(fig,'completion.png','data/scaling/fresh-output.json (original session, ~93% full disk)')

# 3. overwrite vs new — dot plot
fig,axs=plt.subplots(1,2,figsize=(11,3.8),sharey=True)
names=[g for g,_ in groups][::-1];vals=[v for _,v in groups][::-1]
cols=[S3 if n.startswith('Rerun') else S1 for n in names]
for ax,m,title in [(axs[0],'wall_seconds','FFmpeg exit, seconds'),(axs[1],'completion_with_fsync_seconds','Exit + fsync, seconds')]:
 for i,(v,c) in enumerate(zip(vals,cols)):
  y=[r[m] for r in v];jit=[i+((j%7)-3)*0.045 for j in range(len(y))]
  ax.scatter(y,jit,s=14,color=c,alpha=.45,edgecolors='none');mm=med(y)
  ax.plot([mm,mm],[i-.3,i+.3],color=INK,lw=2);ax.annotate(f'{mm:.2f}',(mm,i+.32),fontsize=8.5,color=INK2,ha='center',va='bottom')
 ax.set_title(title);ax.set_xlim(left=0);ax.grid(axis='y',visible=False)
axs[0].set_yticks(range(len(names)));axs[0].set_yticklabels(names,color=INK2)
fig.suptitle('Overwriting only looked slow on the degraded disk; on healthy storage both paths finish in ~1.2 s',x=0.01,ha='left',fontsize=12.5,fontweight='bold')
fig.text(0.01,0.885,'Full-length and 10-minute outputs (≥200 MB). Blue = original session (disk ~93% full), aqua = rerun (58% full). Black tick = median.',fontsize=8.5,color=INK2)
fig.tight_layout(rect=(0,0.03,1,0.87));save(fig,'overwrite-vs-new.png','data/scaling/results.json, fresh-output.json, data/overwrite-rerun/results.json')

# 4. concurrency
fig,axs=plt.subplots(1,2,figsize=(10,3.6))
W=[1,2,4]
for ax,key,fmt in [(axs[0],'jps','{:.1f}/s'),(axs[1],'job','{:.2f} s')]:
 top=max(KL,key=lambda k:conc[(k,4)][key])
 for k in KL:
  y=[conc[(k,w)][key] for w in W];ax.plot(W,y,'-o',color=KC[k],markeredgecolor=SURFACE,markeredgewidth=1.5)
  endlabel(ax,4,y[-1],f'{KL[k]} '+fmt.format(y[-1]),KC[k],dy=(8 if k==top else -8))
axs[0].set_title('Throughput, jobs/s (to FFmpeg exit)');axs[1].set_title('Mean time per job, seconds')
for ax in axs:ax.set_xticks(W);ax.set_xlabel('Parallel jobs (full-length file)');ax.set_ylim(0,ax.get_ylim()[1]*1.12);ax.set_xlim(0.7,5.2)
fig.suptitle('Four parallel jobs: 2.1–2.2× the throughput, each job 1.6–1.9× slower',x=0.01,ha='left',fontsize=12.5,fontweight='bold')
fig.tight_layout(rect=(0,0.03,1,1));save(fig,'concurrency.png','data/scaling/concurrency.json (median of 3 repeats; excludes fsync)')

# 5. CPU by container (full length)
fig,ax=plt.subplots(figsize=(9,5.2))
labels=[l for _,l in CONTAINERS][::-1];keys=[c for c,_ in CONTAINERS][::-1];h=0.38
for j,k in enumerate(KL):
 y=[case('full',ck,k)['summary']['warm_median_cpu_seconds'] for ck in keys]
 pos=[i+(h/2 if j==0 else -h/2) for i in range(len(keys))]
 ax.barh(pos,y,height=h-0.04,color=KC[k],label=f'HLS {KL[k]}')
 for p,v,ck in zip(pos,y,keys):
  ok=case('full',ck,k)['overall_passed'];ax.annotate(f'{v:.2f}'+('' if ok else '  rejected'),(v,p),xytext=(4,0),textcoords='offset points',va='center',fontsize=8,color=INK2)
ax.set_yticks(range(len(keys)));ax.set_yticklabels(labels,color=INK2);ax.grid(axis='y',visible=False);ax.set_xlim(0,1.55)
ax.set_xlabel('CPU seconds per job (full 10:34 file, median of 5)');ax.legend(loc='upper right')
ax.set_title('Accepted containers cost 0.76–1.02 CPU-seconds to remux a 250 MB file')
fig.tight_layout(rect=(0,0.03,1,1));save(fig,'cpu-by-container.png','data/scaling/results.json')

# 6. memory: accepted vs rejected ASF->fMP4
fig,ax=plt.subplots(figsize=(8,3.8))
series=[('Standard MP4 → TS',lambda L:case(L,'mp4','mpegts'),S1),('Standard MP4 → fMP4',lambda L:case(L,'mp4','fmp4'),S2),('ASF → fMP4 (rejected output)',lambda L:case(L,'asf','fmp4'),S3)]
for i,(lab,f,c) in enumerate(series):
 y=[f(L)['summary']['peak_rss_bytes']/MiB for L in LEN];ax.plot(mins,y,'-o',color=c,markeredgecolor=SURFACE,markeredgewidth=1.5)
 endlabel(ax,mins[-1],y[-1],f'{lab}: {y[-1]:.0f} MiB',c,dy=[6,-6,0][i])
ax.set_xlim(0,17);ax.set_ylim(0,600);ax.set_xlabel('Video length, minutes');ax.set_ylabel('Peak RSS, MiB')
ax.set_title('Valid remuxes stay under 100 MiB; a broken ASF input grows memory with length')
fig.tight_layout(rect=(0,0.03,1,1));save(fig,'memory.png','data/scaling/results.json (max over 6 runs)')

# ---------- write generated blocks into REPORT.md ----------
if REPORT.exists():
 txt=REPORT.read_text();missing=[]
 for name,block in T.items():
  # body may be empty or a previous block, but never another marker
  pat=re.compile(r'<!-- gen:'+name+r' -->\n(?:(?!<!-- gen:|<!-- /gen -->).)*<!-- /gen -->',re.S)
  if len(pat.findall(txt))!=1:missing.append(name);continue
  txt=pat.sub(lambda m:'<!-- gen:'+name+' -->\n'+block+'\n<!-- /gen -->',txt)
 REPORT.write_text(txt)
 if missing:print('markers missing in REPORT.md:',missing)
print('charts:',sorted(p.name for p in CHARTS.glob('*.png')));print('tables:',len(T))
