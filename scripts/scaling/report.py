import json,math,statistics,html,shutil,platform,os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import run as b

OUT=b.OUT;ROOT=b.ROOT
r=json.loads(b.STATE.read_text())
br=json.loads((OUT/'browser-validation.json').read_text())
bm={x['id']:x for x in br['tests']}
con=json.loads((OUT/'concurrency.json').read_text())
fresh=json.loads((OUT/'fresh-output.json').read_text())
fresh_map={(c['duration_key'],c['kind']):c for c in fresh['cases']}
chart=OUT/'charts';chart.mkdir(exist_ok=True)

def num(x,n=3):return f'{x:.{n}f}'
def mb(x):return x/1e6
def mib(x):return x/2**20
def table(headers,rows):
 return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows)+'\n'
def reason(c):
 if not c['summary']['all_runs_exit_ok']:return 'FFmpeg muxing failed'
 if c.get('validation_error'):return c['validation_error'].splitlines()[0][:220]
 v=c.get('validation',{})
 if not v.get('passed'):
  failures=[k for k in ['playlist_endlist','segments_exist','target_duration_valid','video_payload_matches','parameter_sets_match','audio_payload_matches','codec_resolution_correct'] if v.get(k) is False]
  if not v.get('timing',{}).get('passed',True):failures.append('timestamps / audio-video alignment')
  if any(not x.get('passed') for x in v.get('segments',[])):failures.append('independent segment decoding')
  return ', '.join(failures) or v.get('reason','Media validation failed')
 test=bm.get(c['id'],{})
 if not test.get('passed'):return 'Browser: '+test.get('error',str(test.get('errors','not tested')))
 return 'PASS'
def case(d,kind,key='mp4'):return next(c for c in d['cases'] if c['kind']==kind and c['container_key']==key)
def label(d):return {'30s':'30 seconds','1m':'1 minute','2m':'2 minutes','5m':'5 minutes','10m':'10 minutes','full':'Full: 10:34.6'}[d['key']]

all_cases=[c for d in r['durations'] for c in d['cases']]
for c in all_cases:
 c['overall_passed']=reason(c)=='PASS';c['failure_reason']=reason(c);c['browser_validation']=bm.get(c['id'])
r['status']='reporting';r['retained_dataset_bytes']=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
r['disk_free_after_bytes']=shutil.disk_usage(OUT).free
r['cpu_governor']=Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor').read_text().strip()
r['storage_model']=Path('/sys/class/block/nvme0n1/device/model').read_text().strip()
r['cpu_affinity']=sorted(os.sched_getaffinity(0))
b.save(r)
passed=sum(c['overall_passed'] for c in all_cases)
summary_rows=[];resource_rows=[];io_rows=[];matrix=[];models=[];data_rows=[]
for d in r['durations']:
 ts=case(d,'mpegts');fm=case(d,'fmp4');s=ts['summary'];f=fm['summary']
 summary_rows.append([label(d),num(mb(ts['input_bytes']),2),num(s['warm_median_seconds']),num(s['input_evicted']['wall_seconds']),
  num(f['warm_median_seconds']),num(f['input_evicted']['wall_seconds']),str(sum(c['overall_passed'] for c in d['cases']))+'/'+str(len(d['cases']))])
 for c in [ts,fm]:
  s=c['summary'];kind='TS' if c['kind']=='mpegts' else 'fMP4'
  resource_rows.append([label(d),kind,num(s['warm_median_cpu_seconds']),num(s['warm_median_cpu_percent'],1),num(s['warm_median_cpu_percent']/r['logical_cpus'],1),num(mib(s['peak_rss_bytes']),1),num(s['warm_median_flush_seconds']),num(s['warm_median_with_flush_seconds'])])
  io_rows.append([label(d),kind,num(mb(s['warm_median_logical_read_bytes']),1),num(mb(s['warm_median_logical_write_bytes']),1),num(mb(s['warm_median_storage_read_bytes']),1),num(mb(s['input_evicted']['io']['read_bytes']),1),num(mb(s['warm_median_storage_write_bytes']),1),s['output_file_count']])
 for c in d['cases']:
  s=c['summary'];why=c['failure_reason'];good=c['overall_passed']
  matrix.append([label(d),c['container'],'TS' if c['kind']=='mpegts' else 'fMP4',num(s['warm_median_seconds']),
   num(s['warm_min_seconds'])+'–'+num(s['warm_max_seconds']),num(s['input_evicted']['wall_seconds']),
   num(s['warm_median_cpu_seconds']),num(s['warm_median_cpu_percent'],1),num(mib(s['peak_rss_bytes']),1),
   num(mb(s['input_evicted']['io']['read_bytes']),1),num(mb(s['warm_median_storage_write_bytes']),1),
   'PASS' if good else 'FAIL',why])
  data_rows.append({'id':c['id'],'duration':label(d),'duration_key':d['key'],'container':c['container'],'kind':c['kind'],
   'seconds':s['warm_median_seconds'],'min':s['warm_min_seconds'],'max':s['warm_max_seconds'],
   'evicted':s['input_evicted']['wall_seconds'],'cpu_seconds':s['warm_median_cpu_seconds'],'cpu_percent':s['warm_median_cpu_percent'],
   'ram_mib':mib(s['peak_rss_bytes']),'physical_read_mb':mb(s['input_evicted']['io']['read_bytes']),
   'storage_write_mb':mb(s['warm_median_storage_write_bytes']),'flush_seconds':s['warm_median_flush_seconds'],
   'good':good,'reason':why,'playlist':c['playlist']})

for kind in ['mpegts','fmp4']:
 x=np.array([d['video_seconds'] for d in r['durations']]);y=np.array([case(d,kind)['summary']['warm_median_seconds'] for d in r['durations']])
 coef=np.polyfit(x,y,1);pred=np.polyval(coef,x);ss=float(np.sum((y-y.mean())**2));r2=1-float(np.sum((y-pred)**2))/ss if ss else 1
 xs=np.array([mb(case(d,kind)['input_bytes']) for d in r['durations']]);bc=np.polyfit(xs,y,1)
 cy=np.array([case(d,kind)['summary']['warm_median_cpu_seconds'] for d in r['durations']]);cc=np.polyfit(xs,cy,1)
 cden=float(np.sum((cy-cy.mean())**2));cr2=1-float(np.sum((cy-np.polyval(cc,xs))**2))/cden if cden else 1
 small=case(r['durations'][0],kind)['summary'];large=case(r['durations'][-1],kind)['summary']
 models.append({'kind':kind,'intercept_seconds':float(coef[1]),'seconds_per_video_second':float(coef[0]),'r_squared':r2,
  'seconds_per_input_mb':float(bc[0]),'bytes_model_intercept_seconds':float(bc[1]),'sample_points':len(x),
  'cpu_seconds_per_input_mb':float(cc[0]),'cpu_model_intercept_seconds':float(cc[1]),'cpu_model_r_squared':cr2,
  'duration_ratio_full_vs_30':float(x[-1]/x[0]),'latency_ratio_full_vs_30':large['warm_median_seconds']/small['warm_median_seconds'],
  'ram_ratio_full_vs_30':large['peak_rss_bytes']/small['peak_rss_bytes'],
  'cpu_ratio_full_vs_30':large['warm_median_cpu_seconds']/small['warm_median_cpu_seconds']})
fresh_comparison=[]
for kind in ['mpegts','fmp4']:
 small=fresh_map[(r['durations'][0]['key'],kind)]['summary'];large=fresh_map[(r['durations'][-1]['key'],kind)]['summary']
 fresh_comparison.append({'kind':kind,'exit_time_ratio':large['warm_median_seconds']/small['warm_median_seconds'],
  'cpu_time_ratio':large['warm_median_cpu_seconds']/small['warm_median_cpu_seconds'],
  'rss_ratio':large['peak_rss_bytes']/small['peak_rss_bytes'],
  'exit_plus_flush_ratio':large['warm_median_with_flush_seconds']/small['warm_median_with_flush_seconds']})
(OUT/'analysis.json').write_text(json.dumps({'models':models,'fresh_comparison':fresh_comparison,'rows':data_rows},indent=2))

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
colors={'mpegts':'#155e75','fmp4':'#c66b13'}
x=[d['video_seconds']/60 for d in r['durations']]
fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
for kind in ['mpegts','fmp4']:
 name='TS' if kind=='mpegts' else 'fMP4';ss=[case(d,kind)['summary'] for d in r['durations']]
 axs[0,0].plot(x,[s['warm_median_seconds'] for s in ss],'o-',color=colors[kind],label=name+' warm / overwrite')
 axs[0,0].plot(x,[s['input_evicted']['wall_seconds'] for s in ss],'x--',color=colors[kind],alpha=.65,label=name+' evicted / overwrite (n=1)')
 axs[0,0].plot(x,[fresh_map[(d['key'],kind)]['summary']['warm_median_seconds'] for d in r['durations']],'^:',color=colors[kind],label=name+' fresh output / warm input')
 axs[0,1].plot(x,[mib(s['peak_rss_bytes']) for s in ss],'o-',color=colors[kind],label=name+' / MP4 input')
 axs[1,0].plot(x,[s['warm_median_cpu_seconds'] for s in ss],'o-',color=colors[kind],label=name)
 axs[1,1].plot(x,[mb(s['warm_median_storage_write_bytes']) for s in ss],'o-',color=colors[kind],label=name+' storage writes')
axs[0,1].plot(x,[mib(case(d,'fmp4','asf')['summary']['peak_rss_bytes']) for d in r['durations']],'s--',color='#b42318',label='ASF → fMP4 (FAILED path)')
axs[1,1].plot(x,[mb(case(d,'mpegts')['summary']['input_evicted']['io']['read_bytes']) for d in r['durations']],'k:',label='MP4 input-evicted storage reads')
titles=['Remux latency: standard MP4 input','Peak process RSS: valid vs failed path','CPU work per job','Kernel-attributed storage I/O per job']
ylabels=['Seconds (FFmpeg exit)','MiB','CPU seconds','MB (decimal)']
for ax,title,yl in zip(axs.flat,titles,ylabels):
 ax.set_title(title);ax.set_xlabel('Video length (minutes)');ax.set_ylabel(yl);ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.suptitle('H.264 1080p30 → HLS: length and resource scaling',fontsize=16)
fig.savefig(chart/'scaling.png',dpi=160);plt.close(fig)

fig,ax=plt.subplots(figsize=(12,5.5),layout='constrained')
for kind in ['mpegts','fmp4']:
 ss=[fresh_map[(d['key'],kind)]['summary'] for d in r['durations']];name='TS' if kind=='mpegts' else 'fMP4'
 ax.plot(x,[s['warm_median_seconds'] for s in ss],'o--',color=colors[kind],label=name+' / FFmpeg exit')
 ax.plot(x,[s['warm_median_with_flush_seconds'] for s in ss],'s-',color=colors[kind],label=name+' / exit + serial file fsync')
ax.set_title('Fresh outputs: FFmpeg exit versus file/directory fsync',fontsize=15)
ax.set_xlabel('Video length (minutes)');ax.set_ylabel('Median seconds, five warm runs');ax.grid(alpha=.2);ax.legend()
fig.savefig(chart/'completion-policy.png',dpi=160);plt.close(fig)

groups=[]
for kind in ['mpegts','fmp4']:
 for workers in [1,2,4]:
  gs=[g for g in con['groups'] if g['kind']==kind and g['workers']==workers]
  groups.append({'kind':kind,'workers':workers,'jobs_per_second':statistics.median(g['jobs_per_second'] for g in gs),
   'flush_jobs_per_second':statistics.median(g['workers']/g['batch_with_flush_seconds'] for g in gs),
   'batch_seconds':statistics.median(g['remux_batch_seconds'] for g in gs),
   'flush_batch_seconds':statistics.median(g['batch_with_flush_seconds'] for g in gs),
   'job_seconds':statistics.median(g['average_job_seconds'] for g in gs),
   'cpu_percent':statistics.median(g['aggregate_average_cpu_percent'] for g in gs),
   'peak_rss_mib':max(mib(g['sampled_peak_aggregate_rss_bytes']) for g in gs)})
fig,axs=plt.subplots(2,3,figsize=(14,9),layout='constrained')
for kind in ['mpegts','fmp4']:
 gs=[g for g in groups if g['kind']==kind];xx=[g['workers'] for g in gs]
 for ax,field in zip(axs.flat,['jobs_per_second','flush_jobs_per_second','job_seconds','cpu_percent','peak_rss_mib','flush_batch_seconds']):
  ax.plot(xx,[g[field] for g in gs],'o-',color=colors[kind],label='TS' if kind=='mpegts' else 'fMP4')
for ax,title,unit in zip(axs.flat,['Throughput at FFmpeg exit','Throughput after fsync','Average per-job exit latency','Aggregate average CPU','Sampled peak aggregate RSS','Batch completion after fsync'],['Jobs / second','Jobs / second','Seconds','% (100 = one core)','MiB; shared pages counted per process','Seconds']):
 ax.set_title(title);ax.set_xlabel('Concurrent jobs');ax.set_xticks([1,2,4]);ax.set_ylabel(unit);ax.grid(alpha=.2);ax.legend()
fig.suptitle('Full 10:34 source: 1, 2, and 4 concurrent standard-MP4 jobs',fontsize=14)
fig.savefig(chart/'concurrency.png',dpi=160);plt.close(fig)

conrows=[[('TS' if g['kind']=='mpegts' else 'fMP4'),g['workers'],num(g['batch_seconds']),num(g['job_seconds']),num(g['jobs_per_second']),num(g['flush_jobs_per_second']),num(g['cpu_percent'],1),num(g['peak_rss_mib'],1),num(g['flush_batch_seconds'])] for g in groups]
conclusions=[]
for kind in ['mpegts','fmp4']:
 one=next(g for g in groups if g['kind']==kind and g['workers']==1)
 four=next(g for g in groups if g['kind']==kind and g['workers']==4)
 conclusions.append(f"- {'TS' if kind=='mpegts' else 'fMP4'}: four workers changed throughput from **{one['jobs_per_second']:.3f} to {four['jobs_per_second']:.3f} jobs/s** ({(four['jobs_per_second']/one['jobs_per_second']-1)*100:+.1f}%), while average per-job latency changed from **{one['job_seconds']:.3f} to {four['job_seconds']:.3f} s**. Sampled aggregate peak RSS reached **{four['peak_rss_mib']:.1f} MiB**.")
 conclusions.append(f"  After including fsync, the corresponding throughput was **{one['flush_jobs_per_second']:.3f} versus {four['flush_jobs_per_second']:.3f} completed jobs/s**. Choose the completion policy before using a throughput figure for capacity planning.")
conclusiontext='\n'.join(conclusions)
roundrows=[]
for k in range(1,6):
 runs=[x for c in all_cases if c['overall_passed'] for x in c['runs'] if x['tag']=='warm-'+str(k)]
 roundrows.append([k,num(statistics.median(x['wall_seconds'] for x in runs)),num(statistics.mean(x['wall_seconds'] for x in runs)),num(statistics.median(x['post_exit_fsync_seconds'] for x in runs))])
failrows=[]
for key in sorted(set(c['container_key'] for c in all_cases if not c['overall_passed'])):
 cs=[c for c in all_cases if c['container_key']==key and not c['overall_passed']]
 failrows.append([cs[0]['container'],len(cs),'; '.join(sorted(set(c['failure_reason'] for c in cs)))])
full=r['durations'][-1];fullts=case(full,'mpegts');fullfm=case(full,'fmp4');first=r['durations'][0]
failure_evidence=[]
for c in full['cases']:
 if c['overall_passed']:continue
 v=c.get('validation',{});t=v.get('timing',{});errors=[s['max_error_seconds']*1000 for s in t.get('streams',{}).values() if 'max_error_seconds' in s]
 payload=('video '+str(v['video_payload_matches'])+', audio '+str(v['audio_payload_matches'])) if 'video_payload_matches' in v else 'not checked / mux failed'
 failure_evidence.append([c['container'],'TS' if c['kind']=='mpegts' else 'fMP4',str(c['summary']['all_runs_exit_ok']),payload,
  num(v.get('playlist_seconds',0),3) if 'playlist_seconds' in v else '—',num(max(errors),2) if errors else 'not comparable',c['failure_reason']])
# Keep the failure explanation identical in both report formats.
failure_details=[
 ("AVI → TS and fMP4: media preserved, timing changed",
  "The tested H.264 stream contains B-frames: decode order and presentation order differ, so correct PTS/DTS and the audio/video start offset matter. The AVI fixture and this stream-copy pipeline do not preserve the reference timing. Even with -fflags +genpts, the full-source video starts 55 ms after audio instead of the reference 88 ms, and individual video PTS differ by up to 64.667 ms (acceptance tolerance: 2 ms). All 19,036 video packets and 29,730 audio packets survive with matching compressed payloads. Decode timestamps remain increasing and presentation timestamps unique; those checks alone do not establish correct presentation timing. Both commands exit successfully, but both outputs fail timing/alignment acceptance. Generating missing timestamps cannot recover the original timing merely from packet order."),
 ("ASF → TS: muxer rejects missing initial timestamps",
  'FFmpeg reports unset timestamps for video stream 0, then "first pts and dts value must be set" and an error submitting a packet to the muxer. The TS path therefore fails during packaging, before it can produce an acceptable HLS asset. Preparing ASF with h264_mp4toannexb adapts H.264 packet framing; it does not reconstruct missing presentation/decode timestamps.'),
 ("ASF → fMP4: successful process exit, invalid HLS timeline",
  'FFmpeg reports "pts has no value" for all 19,036 full-source video packets. It returns zero, but creates one segment with a playlist total of 0.000 seconds and EXT-X-TARGETDURATION:0 for the approximately 634.5-second video. Video/audio payload identity still passes, while video PTS differ by up to 67 ms and the video/audio start offset becomes 21 ms instead of 88 ms. The manifest and timing failures reject this asset. Full-source peak RSS reaches 543.7 MiB; growth with clip length is consistent with buffering on the broken timeline, but the measurements do not prove the internal allocation cause or a memory leak.'),
 ("Scope and remediation",
  'These findings apply to the generated AVI/ASF fixtures, this B-frame H.264/AAC source, and the recorded FFmpeg build and commands. They do not establish that every AVI/ASF file or every H.264 stream in those containers fails. Timestamp repair would require a separately verified strategy that restores presentation order and audio/video alignment; re-encoding would change the stream-copy requirement. Neither repair nor re-encoding was benchmarked. Failed long-video assets were excluded from browser acceptance and the report player; matching payloads or a player starting is not sufficient proof of correctness.')
]
failure_details_md='\n\n'.join('### '+title+'\n\n'+body for title,body in failure_details)
failure_details_html=''.join('<h3>'+html.escape(title)+'</h3><p class="note">'+html.escape(body)+'</p>' for title,body in failure_details)
failure_logs_md='Evidence: [AVI TS log](logs/full-avi-mpegts-warm-1.log), [AVI fMP4 log](logs/full-avi-fmp4-warm-1.log), [ASF TS log](logs/full-asf-mpegts-warm-1.log), [ASF fMP4 log](logs/full-asf-fmp4-warm-1.log), and the full-source validation records in [results.json](results.json). AVI logs are empty because FFmpeg reports no warning at the configured log level; the failure is detected by packet comparison.'
failure_logs_html='<p>Evidence: <a href="logs/full-avi-mpegts-warm-1.log">AVI TS log</a> · <a href="logs/full-avi-fmp4-warm-1.log">AVI fMP4 log</a> · <a href="logs/full-asf-mpegts-warm-1.log">ASF TS log</a> · <a href="logs/full-asf-fmp4-warm-1.log">ASF fMP4 log</a> · <a href="results.json">Packet/timing validation records</a>. AVI logs are empty at the configured log level; packet comparison detects the failure.</p>'
hostrows=[]
for c in [fullts,fullfm]:
 wr=[x for x in c['runs'] if x['cache']=='warm']
 hostrows.append(['TS' if c['kind']=='mpegts' else 'fMP4',num(statistics.median(x['host_busy_cpu_percent'] for x in wr),1),num(statistics.median(x['host_iowait_percent'] for x in wr),1),num(statistics.median(x['host_before']['available_memory_bytes'] for x in wr)/2**30,1)])
network=[]
for title,size in [('TS output',fullts['summary']['output_bytes']),('fMP4 output',fullfm['summary']['output_bytes']),('Both outputs',fullts['summary']['output_bytes']+fullfm['summary']['output_bytes'])]:
 network.append([title,num(mb(size),1),num(size*8/100e6,1),num(size*8/1e9,1)])
total_runs=sum(len(c['runs']) for c in all_cases)
freshrows=[]
for d in r['durations']:
 for kind in ['mpegts','fmp4']:
  f=fresh_map[(d['key'],kind)];s=f['summary'];old=case(d,kind)['summary']
  freshrows.append([label(d),'TS' if kind=='mpegts' else 'fMP4',num(old['warm_median_seconds']),num(s['warm_median_seconds']),
   num(s['input_evicted']['wall_seconds']),num(s['warm_median_with_flush_seconds']),
   num(s['warm_median_cpu_seconds']),num(s['warm_median_cpu_percent'],1),num(mib(s['peak_rss_bytes']),1),'YES' if f['all_byte_identical_to_retained_output'] else 'NO'])
all_runs=[x for c in all_cases for x in c['runs']]
measured_write_gib=sum(x['io']['write_bytes'] for x in all_runs)/2**30
measured_cpu_seconds=sum(x['cpu_seconds'] for x in all_runs)
modeltext='\n'.join(f"- {'TS' if m['kind']=='mpegts' else 'fMP4'}: full/30-second duration ratio **{m['duration_ratio_full_vs_30']:.2f}×**, remux-time ratio **{m['latency_ratio_full_vs_30']:.2f}×**, peak-RSS ratio **{m['ram_ratio_full_vs_30']:.2f}×**. A six-point descriptive fit is `time_seconds = {m['intercept_seconds']:.4f} + {m['seconds_per_video_second']:.6f} × video_seconds` (R² = {m['r_squared']:.3f})." for m in models)
cpumodeltext='\n'.join(f"- {'TS' if m['kind']=='mpegts' else 'fMP4'} CPU work grows **{m['cpu_ratio_full_vs_30']:.2f}×** from 30 seconds to the complete source. A descriptive byte-based fit is `CPU_seconds = {m['cpu_model_intercept_seconds']:.4f} + {m['cpu_seconds_per_input_mb']:.6f} × input_MB` (R² = {m['cpu_model_r_squared']:.3f})." for m in models)
fresh_comparison_text='\n'.join(f"- Fresh {'TS' if m['kind']=='mpegts' else 'fMP4'} outputs: full versus 30-second exit time **{m['exit_time_ratio']:.2f}×**, CPU work **{m['cpu_time_ratio']:.2f}×**, peak RSS **{m['rss_ratio']:.2f}×**, and exit-plus-fsync time **{m['exit_plus_flush_ratio']:.2f}×**; video length grows **{r['durations'][-1]['video_seconds']/r['durations'][0]['video_seconds']:.2f}×**." for m in fresh_comparison)
summarytable=table(['Video length','MP4 input MB','TS warm s','TS input-evicted s','fMP4 warm s','fMP4 input-evicted s','Validated paths'],summary_rows)
resourcetable=table(['Video length','Output','CPU seconds','CPU % of one core','CPU % of 12-thread host','Peak RSS MiB','Extra fsync s','Exit + fsync s'],resource_rows)
iotable=table(['Video length','Output','Logical read MB','Logical write MB','Warm storage read MB','Input-evicted storage read MB','Storage write MB','Output files'],io_rows)
matrixheaders=['Length','Input container','Output','Warm median s','Warm min–max s','Input-evicted s','CPU s','CPU %','Peak RSS MiB','Evicted disk read MB','Disk write MB','Result','Finding']
matrixmd=table(matrixheaders,matrix)

report=f'''# H.264 to HLS: length, resource use, and production sizing

**{passed}/{len(all_cases)} conversion paths passed media integrity, timestamp, independent-segment decoding, and browser spot checks.** The matrix covers six lengths and 14 container/layout variants, each packaged as HLS TS and HLS fragmented MP4.

All timed jobs copy one H.264 High Level 4.1, 1920×1080, 30 fps video stream and one prepared AAC-LC audio track. Video/audio encoding, source download, validation, and remote upload are excluded from remux timings; local fsync is measured separately.

## Main results: repeated output paths

{summarytable}
These headline rows use standard MP4 input. Each warm value is the median of five serial runs; input-evicted is one additional observed run. All 168 container/output/length cases appear in the appendix and in the filterable HTML report. Invalid outputs remain visible but are excluded from successful-throughput conclusions.

The main matrix overwrites the same destination files on every repetition. That controls names and retained outputs, but can exercise Btrfs copy-on-write differently from a production job writing a new asset. The following control tests standard MP4 with a **fresh destination directory on every run**, using the same CPU/I/O/flush instrumentation and five warm plus one input-evicted observation per case. Its temporary output files are hashed against the retained matrix output, then removed after each group; exact identity transfers the retained output's correctness validation to that control.

## Production control: fresh output paths

{table(['Length','Output','Overwrite warm s','Fresh warm s','Fresh input-evicted s','Fresh exit + flush s','Fresh CPU s','Fresh CPU %','Fresh peak RSS MiB','Files byte-identical'],freshrows)}

Fresh and overwrite tests were performed in different phases of the same sustained-write workload; a difference cannot be assigned exclusively to copy-on-write without a randomized paired experiment. Use this control as an observed production-path comparison, not a causal filesystem claim. Fresh-target controls cover standard MP4 only; other input containers retain the repeated-path results in the full matrix. Raw observations are in `fresh-output.json`.

![Packaging versus local completion]({chart/'completion-policy.png'})

{fresh_comparison_text}

## Scaling in the repeated-path matrix

![Scaling charts]({chart/'scaling.png'})

{modeltext}

Fixed work such as process startup and probing contributes to total time, so a 20× increase in length need not produce a 20× increase in total time. Bytes, packet counts, segment counts, filesystem behavior, and cache state also change. The six-point line describes this one movie and hardware, not a universal service-level prediction; it may not recover the actual fixed cost, and a negative or noisy fitted intercept must not be interpreted as a physical startup cost.

## CPU and memory: repeated-output matrix

{resourcetable}
CPU % is `(user CPU seconds + system CPU seconds) / elapsed seconds × 100`; 100% means one fully occupied logical CPU. Divide by 12 to express share of this machine's logical CPU capacity. Values above 100% are possible. Peak RSS is the maximum resident memory observed by Linux `wait4/getrusage`, taking the largest value across measured runs. RSS includes shared library mappings and excludes the operating system's file/page cache, controller process, and browser. It is therefore not a complete container memory budget.

CPU seconds, CPU utilization, I/O byte volumes, and flush times in these tables are medians of the five warm runs; they need not all come from the same individual run. Peak RSS is the maximum across five warm and one input-evicted run.

The failed ASF-to-fMP4 path is plotted separately because its RAM growth is operationally significant even though the produced output is rejected. Do not use its apparent speed as successful throughput. Resource measurements refer to FFmpeg; the separate post-exit fsync operation is timed but its controller CPU is not included in FFmpeg CPU seconds.

{cpumodeltext}
CPU work and wall latency answer different questions. Relatively stable CPU seconds with varying elapsed/flush time is consistent with filesystem or scheduling waits; host iowait snapshots support diagnosis but do not prove exclusive causation or replace device-level telemetry.

For the complete standard-MP4 source, whole-host snapshots during the five warm runs were:

{table(['Output','Host busy CPU %','Host iowait %','Available host RAM GiB'],hostrows)}
These host percentages cover all logical CPUs and include unrelated activity; they are not attributed solely to FFmpeg. Available host RAM includes reclaimable cache and is not a cgroup memory limit.

## Disk reads, writes, cache, and completion

{iotable}
- **Logical reads/writes** are Linux `rchar/wchar` deltas attributable to FFmpeg, including probing, libraries, and log writes; they need not equal media file sizes exactly.
- **Storage reads/writes** are Linux `read_bytes/write_bytes` deltas, distinct from cached I/O. Per-run cancellation counters and filesystem block counters are retained in raw results. These are kernel-attributed bytes, not a device-level NAND-write or SSD-wear measurement.
- **Warm mode** pre-reads the input outside the timer. The actual storage-read counters show whether the timed process fetched data from storage.
- **Input-evicted mode** fsyncs the input and requests `POSIX_FADV_DONTNEED` for that specific file before the run. This is not a machine-wide cold-cache test: libraries, metadata, the controller, and device caches may remain warm. No global cache settings were changed.
- **FFmpeg exit time** includes opening/probing, stream copying, writing all segments/playlists, and exit. It does not guarantee durable storage. After exit, the harness fsyncs all output media files and their directory. Extra flush time and exit-plus-flush time are reported separately. Device/filesystem guarantees still apply.
- The harness fsyncs output files serially, then their directory. This is a tested local persistence policy, not a mandatory remuxing step. A production service using disposable local scratch files and a remote completion acknowledgement has a different completion policy and must measure that path separately.
- Fsync measurements cover the media files and their immediate containing directory. Ancestors of newly created directories are not individually fsynced by this harness, and no crash/power-loss test was performed; this is a measured flush policy, not proof of a crash-consistent end-to-end commit protocol.
- Each output uses VOD playlists and a six-second segment target, with cuts at existing keyframes. Exact six-second segments are not forced. Segment counts and file counts are recorded per case.

Linux definitions: [process I/O counters](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html), [CPU and peak RSS](https://man7.org/linux/man-pages/man2/getrusage.2.html), [fsync](https://man7.org/linux/man-pages/man2/fsync.2.html), and [cgroup memory accounting](https://docs.kernel.org/admin-guide/cgroup-v2.html).

## Compatibility and failures

{table(['Input family','Failed paths','Observed finding'],failrows)}
For the complete source, the failure evidence is:

{table(['Input','Output','All FFmpeg exits zero','Payload identity','Playlist seconds','Max PTS error ms','Rejection reason'],failure_evidence)}
Exact packet counts, relative audio/video starts, decode-timestamp ordering, and the log for every attempted run are retained in `results.json` and `logs/`. A zero exit code with matching compressed media still fails acceptance when its manifest/timestamps are wrong.
The known compatibility fixes are retained: `aac_adtstoasc` for fMP4 AAC packet adaptation, `delay_moov` when preparing fragmented MP4 to preserve initial audio/video timing, and Annex B H.264 adaptation when preparing ASF. AVI is tested with `-fflags +genpts`. These operations do not re-encode video. They do not waive validation failures.

{failure_details_md}

{failure_logs_md}

## Concurrent production jobs

The complete 10:34 source in standard MP4 was remuxed with 1, 2, and 4 simultaneous jobs, separately for TS and fMP4. Each group has three repetitions. Inputs were pre-read; outputs were fsynced. This short, bounded local contention test measures overlapping jobs, not a long steady-state arrival queue.

{table(['Output','Workers','Batch remux s','Mean job s','Exit jobs/s','With-flush jobs/s','Aggregate CPU %','Sampled peak RSS MiB','Batch + flush s'],conrows)}
{conclusiontext}
![Concurrency charts]({chart/'concurrency.png'})
Aggregate RSS is sampled every 10 ms and sums per-process RSS, including shared pages counted for each process; short peaks may be missed. Individual exact peaks and full sample traces are also retained. Batch remux time spans the earliest FFmpeg start to the latest FFmpeg exit. Flushes from an earlier-finishing job can overlap another running job, as in an actual shared-filesystem workload.

## Production interpretation

1. Size CPU from **CPU seconds per accepted job** and desired jobs/second, then reserve headroom and measure under the actual CPU limit. A sub-second local job is not necessarily cheap at a high arrival rate. Use the concurrency measurements to assess contention rather than multiplying a single-worker rate without evidence.
2. Budget memory for FFmpeg RSS **plus** application overhead and page cache. As a provisional starting point for this exact media profile, observed valid-job RSS plus 50% gives a process-memory allowance; it is not a tested cgroup/container limit. Measure `memory.current`, `memory.stat`, and memory-pressure/OOM events in the target runtime before setting limits.
3. Budget input reads and output writes separately. Producing both HLS styles in two independent jobs reads/processes the input twice and writes both packages. A multi-output packaging optimization was not benchmarked here. These are seekable local files; fast-start versus end-index MP4 behavior over HTTP/range requests is not measured.
4. Validate input timestamps early, retain source codec/profile restrictions, and reject or explicitly repair invalid inputs. The ASF/AVI cases show why exit code zero or a browser reaching the end is insufficient. Apply explicit time/memory limits and bounded worker queues; limits themselves were not tested in this run.
5. Network/object-storage latency can dominate this local packaging time. The following are mathematical upload floors for the complete source's measured output sizes, excluding request latency, TLS, retries, per-segment overhead, and storage persistence. They are not measured cloud timings:

{table(['Package','Output MB','At 100 Mb/s: minimum upload s','At 1 Gb/s: minimum upload s'],network)}

Input download may add work, and streaming transfers can overlap. Use real network conditions and object-store APIs for the next load test. Local SSD, disk occupancy, filesystem writeback, and CPU power policy all influence these numbers.

For a steady workload, a first planning calculation is `CPU cores ≈ arrival_jobs_per_second × mean_CPU_seconds_per_job / chosen_utilization_fraction`. Likewise, `output_MB_per_second ≈ arrival_jobs_per_second × output_MB_per_job`. Use the mix of accepted input types and the chosen completion policy, not the fastest row. These are demand calculations, not measured service capacities; memory/page cache, metadata I/O, queues, and network overhead still constrain the service.

The measured pipeline starts with AAC audio already available. If production uploads contain MP3, AC-3, or another audio codec requiring conversion, add that preparation cost; the current CPU/time figures cover stream copying, not audio encoding. Input/output validation, upload, orchestration, and queue wait also need their own production budgets. The final media-validation invocation took {r.get('media_validation_wall_seconds',0)/60:.1f} minutes using byte-identical-segment caching across cases; this excludes the interrupted diagnostic pass and is not a per-job or uncached production validation benchmark.

## Assumptions

- One downloaded movie: Big Buck Bunny, Sunflower version. Source MP4 is 276,134,947 bytes, 1920×1080 progressive 30 fps, H.264 High Level 4.1, 8-bit 4:2:0, with B-frames. Original tracks are MP3 stereo and AC-3 5.1.
- Excerpts begin at the beginning of the same source. Requested lengths are 30, 60, 120, 300, and 600 seconds, plus the complete source. Full video stream duration is 634.533 seconds; source container duration is 634.600 seconds. Actual reference/playlist durations and packet counts are retained.
- Audio is prepared once per reference as AAC-LC, stereo 48 kHz at a 128 kb/s target. A TS intermediate normalizes source priming/edit-list behavior. Preparation is excluded from remux timings; every timed operation copies both encoded streams. No video re-encoding occurs.
- Fourteen entries include distinct layouts of the MP4 family, not fourteen unrelated container specifications. WebM/Ogg are outside this H.264 test selection.
- Each HLS package has one 1080p video rendition and one AAC track. TS and fMP4 are two packaging styles of that same quality, not an adaptive-bitrate ladder. Creating additional resolutions/bitrates would require separate encoding work that is not measured here.
- This reruns the 30-second baseline using the new resource/flush/cache methodology. Earlier uninstrumented 30-second values are preserved in `../hls-benchmark/` and are not mixed into these scaling fits.

## Data Quality/Confidence

- **{total_runs} measured main-matrix serial runs**: five warm repetitions plus one input-evicted run for each of {len(all_cases)} cases, in seeded shuffled order per warm round; {len(all_cases)} additional warm-ups. There are also 72 measured fresh-target control runs and 42 concurrency jobs. Timing/resource measurement runs before decoding and browser workloads. Each timed child has its own logs and measurement JSON.
- Measured FFmpeg runs together consumed {measured_cpu_seconds:.1f} CPU-seconds and were charged approximately {measured_write_gib:.1f} GiB of storage writes; preparation, warm-ups, fsync-controller work, concurrency tests, and validation are additional. This is a sustained-write experiment, not a single isolated short copy. SSD controller/SLC-cache behavior was not measured, so changes cannot be attributed to that mechanism specifically.
- CPU user/system time and peak RSS are exact child process accounting; I/O counters are read after the wrapper waits for the child and subtract its own baseline. Filesystem-block counts cross-check byte counters. Fsync is measured separately. Wall time starts immediately before FFmpeg fork/exec, excluding Python measurement startup, cache preparation, and JSON output.
- Every accepted output has an entire-stream H.264 VCL payload/parameter-set identity match and an entire AAC ADTS payload match to its duration reference. Video/audio packet counts, presentation timing within 2 ms, increasing decode timestamps, codecs/resolution, manifests, and file existence are checked over the complete asset. A separate order-sensitive audit compares PTS for corresponding access units in decode/demux order, so a matching sorted timestamp set cannot conceal timestamps assigned to the wrong frames; that audit took {r.get('packet_order_audit_wall_seconds',0)/60:.1f} minutes.
- Every accepted segment decodes independently with strict FFmpeg error handling and starts with a keyframe. Byte-identical init+segment assets reuse an already completed decode result, keyed by SHA-256. **{r.get('unique_segment_decode_count','unknown')} unique segment assets** were decoded. All duration references and the complete standard-MP4 TS/fMP4 playlists are also decoded end to end.
- A diagnostic pass found coarse timestamp rounding in the temporary null-output validation sink for some independently opened fMP4 fragments. The sink was changed to a 90 kHz video time base and affected checks were rerun; no input/HLS media or measured timings changed. The original diagnostic results are retained in raw results where applicable. Media packet timestamps are audited separately from the validation sink.
- Browser tests use Chromium {br['browser']} and hls.js 1.6.13, at normal speed: startup, middle seek, near-end seek, and end completion. They do not watch every full long asset in real time. Full packet/segment validation covers the intervening data. Playback is muted; no human listening or subjective visual assessment is claimed. Render counters include seeking and local test load.
- Five warm observations support a median/range comparison, not a production p95/p99. Input-evicted has one observation per case; concurrency has three repetitions. One film and one laptop limit generalization. The full six-point regression is descriptive, with highly correlated length and byte count.
- CPU governor: `{r['cpu_governor']}`. The desktop was not isolated from unrelated activity; host CPU/iowait/load/available-memory snapshots are retained. The dataset itself changes disk occupancy and sustained-write conditions. Free disk at report time: {r['disk_free_after_bytes']/2**30:.1f} GiB. Compare round drift below before treating small differences between containers as meaningful.

{table(['Warm round','Median valid-job s','Mean valid-job s','Median extra fsync s'],roundrows)}

## What this does NOT prove

It does not establish an SLA or supported peak concurrency for cloud servers; cold object storage performance; network/CDN behavior; container/cgroup limits; long steady-state saturation; power-loss recovery; Safari/iOS/native HLS behavior; other resolutions, frame rates, bitrates, codecs, damaged files, encryption/DRM, multiple languages/subtitles, or live/low-latency HLS. It also does not show that all AVI/ASF inputs fail, only that these particular fixtures fail this tested pipeline.

## Environment and reproducibility

- CPU: AMD Ryzen 5 PRO 5650U, {r['physical_cores']} physical cores / {r['logical_cpus']} logical CPUs; affinity permits {len(r['cpu_affinity'])} logical CPUs.
- Memory: {r['memory']['total']/2**30:.1f} GiB physical RAM; initial available {r['memory']['available']/2**30:.1f} GiB.
- Storage: NVMe `{r['storage_model']}`, Btrfs filesystem. The test stays on the same local filesystem for inputs and outputs.
- Platform: `{r['platform']}`.
- `{r['ffmpeg']}`.
- The complete FFmpeg build configuration is saved in `ffmpeg-build.txt`; this desktop build loads many optional libraries, which can influence startup time and baseline RSS.
- Measured: 15 October 2026, Africa/Cairo. Dataset before report assets: approximately {r['retained_dataset_bytes']/2**30:.1f} GiB.
- `results.json`, `analysis.json`, `measurements/`, `logs/`, `segment-validation-cache.json`, `browser-validation.json`, and `concurrency.json` preserve the evidence. `scripts/` preserves the harness. Script paths refer to this workspace and its installed tools; adapt them for another machine.
- HLS assets are in `durations/<length>/hls/<container>/<mpegts|fmp4>/`. Input fixtures and references are retained alongside them. Only validated outputs are offered in the HTML player.

During this session the [local HTML viewer](http://127.0.0.1:8765/outputs/hls-scaling/report.html) is served by the existing localhost server. To serve the output folder independently, run `python3 -m http.server 8766 --bind 127.0.0.1 --directory "{OUT}"` and open [the standalone viewer](http://127.0.0.1:8766/report.html). The player requires HTTP rather than opening the HTML with `file://`.

Source: https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip . Big Buck Bunny © 2008 Blender Foundation / www.bigbuckbunny.org; Sunflower version credits Blender Foundation 2008 and Janus Bager Kristensen 2013. CC BY 3.0. Source SHA-256: `{r['source_sha256']}`.

## Complete results matrix

Times and resource costs of failed attempts are retained for diagnosis; FAIL rows are not usable-output timings.

{matrixmd}
'''
(OUT/'report.md').write_text(report)
(OUT/'ffmpeg-build.txt').write_text(b.subprocess.check_output(['ffmpeg','-version'],text=True))
(OUT/'summary-table.md').write_text(summarytable)
(OUT/'resource-table.md').write_text(resourcetable+'\n'+iotable)

# A self-contained report UI, with local hls.js for the validated-output player.
payload=json.dumps(data_rows).replace('</','<\\/')
summaryhtml='<table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in ['Length','Input MB','TS warm s','TS evicted s','fMP4 warm s','fMP4 evicted s','Valid paths'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in summary_rows)+'</tbody></table>'
freshhtml='<table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in ['Length','Output','Overwrite warm s','Fresh warm s','Fresh evicted s','Fresh exit + flush s','CPU s','CPU %','RSS MiB','Byte-identical'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in freshrows)+'</tbody></table>'
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HLS scaling and resources</title>
<style>body{font:15px/1.55 system-ui,sans-serif;background:#f5f7fa;color:#172b3a;max-width:1400px;margin:35px auto;padding:0 24px}h1{font-size:32px;margin-bottom:5px}h2{margin-top:34px}table{border-collapse:collapse;background:white;width:100%;font-size:13px}th,td{border-bottom:1px solid #dbe2e8;text-align:left;padding:9px;white-space:nowrap}th{background:#e6edf3;position:sticky;top:0}img{display:block;max-width:100%;background:white;margin:20px 0}.scroll{overflow:auto;max-height:650px}select,button{font:inherit;padding:7px;margin:4px}a{color:#145c89}.pass{color:#087448;font-weight:700}.fail{color:#b42318;font-weight:700}video{width:min(960px,100%);display:block;background:#111;margin:15px 0}.note{max-width:1100px;color:#425969}#status{white-space:pre-wrap}</style>
<h1>H.264 → HLS: scaling and resource use</h1><p>1080p30 · 30 seconds through the complete 10:34 source · 14 container/layout variants · warm and input-evicted I/O</p>
<p class="note">Every measured job stream-copies H.264 video and prepared AAC-LC audio. Download, audio preparation, decoding/validation and remote upload are excluded. Local file/directory fsync is timed separately.</p>
<p><strong>'''+str(passed)+' / '+str(len(all_cases))+''' conversion paths passed all required checks.</strong> Failed outputs are excluded from the player.</p>
<p><a href="report.md">Detailed report, metric definitions, findings and production limits</a> · <a href="results.json">Raw measurements</a> · <a href="analysis.json">Analysis data</a> · <a href="concurrency.json">Concurrent jobs</a></p>
<h2>Standard MP4: repeated output paths</h2>'''+summaryhtml+'''
<p class="note">Warm values: median of five runs. Input-evicted values: one run with file-specific cache eviction requested, not a globally cold machine. FFmpeg completion excludes the separately measured fsync flush. Actual storage-read counters are in the detailed report.</p>
<h2>Production control: fresh output paths</h2>'''+freshhtml+'''
<p class="note">Standard MP4 only; each run writes a new directory. Five warm runs and one input-evicted trial per case. Outputs are compared byte for byte with retained, validated assets. These controls run in a later phase, so differences cannot be attributed exclusively to overwrite behavior. <a href="fresh-output.json">Raw fresh-output results</a>.</p>
<img src="charts/completion-policy.png" alt="Fresh-output packaging time compared with completion after local file fsync">
<img src="charts/scaling.png" alt="Length, latency, peak memory, CPU seconds and disk I/O charts">
<h2>Concurrent jobs on the complete source</h2><img src="charts/concurrency.png" alt="Concurrency throughput, latency, CPU and peak aggregate memory charts">
<h2>All container and duration results</h2><label>Length <select id="duration"><option value="">All lengths</option></select></label><label>Container <select id="container"><option value="">All containers</option></select></label><label>Output <select id="kind"><option value="">Both outputs</option><option value="mpegts">TS</option><option value="fmp4">fMP4</option></select></label><label>Status <select id="result"><option value="">All results</option><option value="pass">Pass</option><option value="fail">Fail</option></select></label><p id="count"></p>
<div class="scroll"><table><thead><tr><th>Length</th><th>Container</th><th>Output</th><th>Warm s</th><th>Min–max s</th><th>Evicted s</th><th>CPU s</th><th>CPU %</th><th>Peak RSS MiB</th><th>Evicted disk read MB</th><th>Disk write MB</th><th>Extra fsync s</th><th>Result</th><th>Finding</th></tr></thead><tbody id="matrix"></tbody></table></div>
<h2 id="avi-asf-failures">Why AVI and ASF fail</h2><p>AVI and ASF account for all 24 rejected paths: six durations × two output types × two input containers. A zero process exit code does not guarantee valid HLS.</p>'''+failure_details_html+failure_logs_html+'''
<h2>Play a validated output</h2><p class="note">Serve this folder over HTTP. Automated long-video browser checks cover startup, middle and near-end seeking; complete packet identity and independent segment decoding cover the whole asset. Native Safari/iOS playback was not tested.</p><select id="choice"></select><button id="load">Load video</button><video controls playsinline preload="auto"></video><p id="status"></p>
<h2>Scope</h2><p class="note">Local NVMe/Btrfs laptop benchmark, five warm repetitions and one input-evicted trial per case. RSS excludes filesystem page cache. CPU 100% = one logical CPU. Timings of failed attempts are diagnostic. See the full report for assumptions, quality checks, variability, cloud/network limits and production sizing guidance.</p><p>Big Buck Bunny © 2008 Blender Foundation / www.bigbuckbunny.org · Sunflower version · CC BY 3.0.</p>
<script src="assets/hls.min.js"></script><script>
const rows='''+payload+''';const $=id=>document.getElementById(id),fmt=(x,n=3)=>Number(x).toFixed(n),esc=x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
for(const field of ['duration','container'])for(const x of new Set(rows.map(r=>r[field])))$(field).add(new Option(x,x));
function render(){const list=rows.filter(r=>(!$('duration').value||r.duration===$('duration').value)&&(!$('container').value||r.container===$('container').value)&&(!$('kind').value||r.kind===$('kind').value)&&(!$('result').value||r.good===($('result').value==='pass')));$('count').textContent=list.length+' conversion paths';$('matrix').innerHTML=list.map(r=>'<tr>'+[r.duration,r.container,r.kind==='mpegts'?'TS':'fMP4',fmt(r.seconds),fmt(r.min)+'–'+fmt(r.max),fmt(r.evicted),fmt(r.cpu_seconds),fmt(r.cpu_percent,1),fmt(r.ram_mib,1),fmt(r.physical_read_mb,1),fmt(r.storage_write_mb,1),fmt(r.flush_seconds),r.good?'PASS':'FAIL',r.reason].map((x,i)=>'<td'+(i===12?' class="'+(r.good?'pass':'fail')+'"':'')+'>'+esc(x)+'</td>').join('')+'</tr>').join('');}
for(const field of ['duration','container','kind','result'])$(field).onchange=render;render();
for(const r of rows.filter(r=>r.good))$('choice').add(new Option(r.duration+' / '+r.container+' / '+(r.kind==='mpegts'?'TS':'fMP4'),r.playlist));
let hls;const v=document.querySelector('video');$('load').onclick=()=>{if(hls)hls.destroy();const url=$('choice').value;$('status').textContent=url;if(Hls.isSupported()){hls=new Hls();hls.on(Hls.Events.ERROR,(_,d)=>$('status').textContent+='\\n'+d.type+': '+d.details);hls.loadSource(url);hls.attachMedia(v);}else if(v.canPlayType('application/vnd.apple.mpegurl'))v.src=url;else $('status').textContent='HLS playback unsupported in this browser.';};
</script></html>'''
(OUT/'report.html').write_text(page)
(OUT/'assets').mkdir(exist_ok=True)
for name in ['hls.min.js','hls-LICENSE.txt']:shutil.copy(ROOT/'work'/name,OUT/'assets'/name)
for source in b.WORK.glob('*'):
 if source.suffix in ['.py','.cjs']:shutil.copy(source,OUT/'scripts'/source.name)
print(summarytable)
print('PASSED',passed,'/',len(all_cases),'MEASURED RUNS',total_runs)
print('MODELS',json.dumps(models,indent=2))
print('FULL RESOURCE',json.dumps({k:case(full,k)['summary'] for k in ['mpegts','fmp4']},indent=2))
r['status']='complete';b.save(r)

