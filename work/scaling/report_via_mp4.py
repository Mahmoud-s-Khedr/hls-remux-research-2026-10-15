import json,html,hashlib,zipfile
from pathlib import Path
from urllib.parse import quote
OUT=Path.cwd()/'outputs';folder=OUT/'hls-via-mp4';r=json.loads((folder/'results.json').read_text());assert len(r['cases'])==8
lines=['# AVI/ASF → MP4 → HLS TS: follow-up experiment','','Tested 30-second and full-length fixtures from the scaling experiment, with both default timestamp handling and `-fflags +genpts` before reading AVI/ASF. Every stage used `-c copy`; no re-encoding. These eight exploratory attempts are separate from the original benchmark. One attempt per case, no controlled cache or repeated performance measurements.','','**All eight routes produced MP4 and HLS files, but none preserved the reference timing within the required 2 ms tolerance.** Encoded video/audio payload identity passed for all eight. The intermediate MP4 gets past the direct ASF-to-TS mux error; it does not prove correct restoration of timestamps.','','| Source length | Input | Timestamp mode | MP4 exit | HLS exit | Max PTS error ms | A/V start offset ms | DTS increasing | Accepted |','|---|---|---|---|---|---|---|---|---|']
for c in r['cases']:
 t=c['validation']['timing'];err=max(s.get('max_error_seconds',0) for s in t['streams'].values())*1000
 lines.append('| '+' | '.join([c['id'].split('-')[0],c['id'].split('-')[1].upper(),c['id'].split('-')[2],str(c['mp4_returncode']),str(c['hls_returncode']),f'{err:.3f}',f"{t['actual_video_minus_audio_start']*1000:.3f}",str(t['dts_strictly_increasing']),str(c['passed'])])+' |')
lines+=['','The reference video starts 88 ms after audio. A shared container start-time shift is allowed by comparison; errors above are remaining relative timing differences, not simply a different starting timestamp. Default routes also contain non-increasing decode timestamps. `+genpts` improves that check but does not restore the original timeline.','','The failure is established by full-stream compressed-media identity and packet-timing comparison. Independent segment decoding and browser acceptance were not run for these already rejected assets. No claim of correct playback, duration or independent-segment safety is made.','','This does not rule out a separate source-specific timestamp repair strategy. Repair and re-encoding were not tested here. Container changes alone are insufficient for these fixtures.','','Evidence: [results.json](results.json), exact commands and per-stage logs linked below. Prepared MP4 and HLS files remain in the case subdirectories. Diagnostic wall times are retained but must not be compared as formal benchmark medians.','']
for c in r['cases']:lines.append(f"- {c['id']}: [MP4 log]({c['mp4_log']}), [HLS log]({c['hls_log']}).")
text='\n'.join(lines)+'\n';(folder/'report.md').write_text(text)
ref=OUT/'research-reference';p=ref/'README.md';p.write_text(p.read_text()+'\n## Follow-up: AVI/ASF through MP4\n\n[Follow-up report](../hls-via-mp4/report.md): eight new stream-copy routes (30 seconds/full source, AVI/ASF, default/genpts). All produce HLS TS files, but all fail reference timing. These attempts are additional to the original 168-case matrix. [Raw data](../hls-via-mp4/results.json).\n')
p=ref/'complete-research-record.md';p.write_text(p.read_text()+'\n\n---\n\n'+text.replace('](results.json)',']('+str(folder/'results.json')+')').replace('](logs/',']('+str(folder/'logs')+'/'))
# Refresh the evidence inventory and archive so the research collection includes this follow-up.
media={'.mp4','.ts','.m2ts','.m4s','.mov','.mkv','.avi','.asf','.flv','.f4v','.3gp','.3g2','.nut','.zip'}
files=[]
for base in [OUT/'hls-benchmark',OUT/'hls-scaling',OUT/'hls-via-mp4',ref]:
 for p in sorted(base.rglob('*')):
  if not p.is_file() or p.name in ('inventory.json','inventory.html','evidence.zip','SHA256SUMS.txt'):continue
  binary=p.suffix.lower() in media
  files.append(dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,category='binary-media-or-source-archive' if binary else 'evidence',sha256=None if binary else hashlib.sha256(p.read_bytes()).hexdigest()))
(ref/'inventory.json').write_text(json.dumps({'base_directory':str(OUT),'note':'Includes eight MP4-intermediate follow-up attempts. Large media sizes inventoried without rehashing.','files':files},indent=2))
rows=''.join('<tr><td><a href="../'+quote(x['path'])+'">'+html.escape(x['path'])+'</a></td><td>'+str(x['bytes'])+'</td></tr>'for x in files)
(ref/'inventory.html').write_text('<!doctype html><meta charset="utf-8"><title>Research inventory</title><style>body{font:14px system-ui;margin:30px}td{padding:5px;border-bottom:1px solid #ddd}</style><h1>Research inventory</h1><p>Includes MP4-intermediate follow-up. '+str(len(files))+' files.</p><input placeholder="Filter paths" oninput="for(const r of document.querySelectorAll(\'tr\'))r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase())"><table>'+rows+'</table>')
(ref/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files if x['sha256']))
with zipfile.ZipFile(ref/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for x in files:
  if x['category']=='evidence':z.write(OUT/x['path'],x['path'])
 for name in ['inventory.json','inventory.html','SHA256SUMS.txt']:z.write(ref/name,'research-reference/'+name)
with zipfile.ZipFile(ref/'evidence.zip') as z:assert z.testzip() is None
assert all(not c['passed'] and c['mp4_returncode']==0 and c['hls_returncode']==0 for c in r['cases'])
print('Follow-up report saved; research index, record, inventory and archive updated; integrity check passed.')
