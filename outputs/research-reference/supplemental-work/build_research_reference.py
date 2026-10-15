import json,os,shutil,hashlib,zipfile,html
from pathlib import Path
from collections import Counter
ROOT=Path.cwd(); OUT=ROOT/'outputs'; DEST=OUT/'research-reference'; DEST.mkdir(exist_ok=True)
# Preserve working evidence without duplicating large immutable media files.
for src in (ROOT/'work').rglob('*'):
 if not src.is_file() or '__pycache__' in src.parts or src.name=='http-server.log': continue
 dst=DEST/'supplemental-work'/src.relative_to(ROOT/'work');dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():
  if src.suffix.lower() in {'.mp4','.ts','.m4s','.asf','.zip'}:os.link(src,dst)
  else:shutil.copy2(src,dst)
r=json.loads((OUT/'hls-scaling/results.json').read_text());cases=[c for d in r['durations'] for c in d['cases']]
assert len(cases)==168 and sum(c['overall_passed'] for c in cases)==144
flat=[]
for d in r['durations']:
 for c in d['cases']:
  for run in c['runs']:
   flat.append(dict(case_id=c['id'],duration_key=d['key'],requested_seconds=d['requested_seconds'],video_seconds=d['video_seconds'],container_key=c['container_key'],container=c['container'],output_kind=c['kind'],video_codec='h264',width=1920,height=1080,input_bytes=c['input_bytes'],accepted=c['overall_passed'],failure_reason=c['failure_reason'],**run))
(DEST/'serial-runs.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in flat))
(DEST/'case-summaries.json').write_text(json.dumps([dict(case_id=c['id'],duration_key=c['duration_key'],container=c['container'],output_kind=c['kind'],input_bytes=c['input_bytes'],accepted=c['overall_passed'],failure_reason=c['failure_reason'],summary=c['summary'],command=c['command'],playlist=c['playlist']) for c in cases],indent=2))
intro='''# H.264 to HLS research reference — complete test collection

Recorded experiment date: 15 October 2026, Africa/Cairo. This index consolidates the original short-clip experiment, the instrumented scaling experiment, all retained evidence, and findings discussed in this chat. No benchmark was rerun to assemble this collection.

## How to cite and navigate this collection

Use stable case IDs such as `full-mp4-mpegts` and `full-asf-fmp4`. For a measurement, identify the experiment, case ID, run tag, metric, unit, cache policy, and completion policy. Example: “Scaling experiment, full-mp4-mpegts, fresh-target control, five-run warm median FFmpeg exit 0.771 s; exit plus measured flush 7.904 s.” Medians of different metrics need not belong to the same run. These are locally generated experimental results, not externally peer-reviewed findings.

| Reference | Contents |
|---|---|
| [Complete scaling report](../hls-scaling/report.md) | All 168 case rows; timing, resource use, disk I/O, correctness, failure explanations, concurrency, methodology and limits |
| [Interactive scaling report](../hls-scaling/report.html) | Filterable case table, charts, accepted-output player; use HTTP for playback |
| [Original 30-second report](../hls-benchmark/report.md) | Earlier 28-path experiment, decoded frame/audio comparisons, fixes and initial findings |
| [Combined narrative](complete-research-record.md) | Both reports verbatim, plus this index, definitions and bottleneck interpretation |
| [Evidence archive](evidence.zip) | Reports, JSON, per-run measurements/logs, scripts, charts, playlists, diagnostic history and inventory; excludes large binary media |
| [All-file inventory](inventory.html) | Links to every retained file, including actual inputs and segments excluded from the archive |
| [Machine-readable inventory](inventory.json) | Relative paths, byte sizes and SHA-256 for non-media evidence; large media marked unhashed |
| [Flattened serial runs](serial-runs.jsonl) | 1,008 measured scaling runs, one JSON object per line, with case identifiers and complete original run fields |
| [Case summaries](case-summaries.json) | 168 cases, summaries, exact FFmpeg argv, input sizes, output paths and acceptance status |

The media collection remains in its original directories. The archive is an evidence-only package, not a standalone playable copy. Preserve the whole outputs directory to retain every video, segment and init file. Large supplemental media use hard links to preserve bytes without consuming a second copy of disk space; do not edit those files in place.

## Experiment register

| ID | Experiment | Coverage and evidence |
|---|---|---|
| E1 | Original 30-second baseline | 14 containers/layouts × 2 outputs = 28 paths; one warm-up and five final timed observations per path; 24 accepted. Warm cache; no resource/fsync instrumentation. See original report and final-timing-commands.json. |
| E2 | Scaling serial matrix | Six lengths × 14 variants × 2 outputs = 168 paths; 1,008 measured runs and 168 warm-ups; 144 accepted. Five warm and one input-evicted run per case. |
| E3 | Fresh-output control | Standard MP4, six lengths, two outputs; 72 measured jobs. A new directory per job; output identity checked against retained assets. |
| E4 | Concurrent jobs | Full source, standard MP4; 1/2/4 workers × 3 repetitions × 2 output types = 42 measured jobs. Packaging and flush completion reported separately. |
| V1 | Scaling media correctness | Full encoded payload/parameter sets and packet timing; 1,337 unique segment assets independently decoded; reference decodes and full standard-MP4 playlist decodes. |
| V2 | Scaling browser correctness | 144 accepted outputs: normal-speed startup, mid seek, tail seek and end checks. No claim that every long asset was watched continuously. |
| V3 | Baseline browser tests | Normal-speed playback/seek results determine acceptance; exploratory 8× stress evidence retained separately, with buffering warnings. |
| V4 | Report QA | 168 table rows, 144 playable choices, three charts, filters and player seeking checked; no page errors. |

E1 and E2 use different measurement methods. Use E2's 30-second rerun for scaling comparisons; do not pool E1 timings into E2 regressions. Exploratory command logs contain retries and diagnostics, so their command count is not the final measured-run count.

## Source, preparation, and boundaries

One film: Big Buck Bunny, Sunflower version. H.264 High Level 4.1, 1920×1080, 30 fps, progressive 8-bit 4:2:0, B-frames. Original source is 276,134,947 bytes, container duration 634.600 s, video duration approximately 634.533 s. Original audio is MP3 stereo and AC-3 5.1. AAC-LC stereo 48 kHz, target 128 kb/s, is prepared before timing. All timed jobs copy the prepared video and audio; no encoding is included.

Source URL and full ffprobe metadata are in scaling/results.json. Source SHA-256: `ae51005850b0ff757fe60c3dd7a12d754d3cd2397d87d939b55235e457f97658`. Original downloaded MP4 and ZIP, fetched source pages, and scratch diagnostics are preserved under supplemental-work. Big Buck Bunny © Blender Foundation; CC BY 3.0 attribution and source links are retained in both reports.

Inputs: standard MP4, fast-start MP4, fragmented MP4, MOV, MKV, TS, M2TS, AVI, FLV, F4V, 3GP, 3G2, NUT, ASF. Fourteen variants include related container specifications and layouts. This is not coverage of every container. DASH was discussed but not benchmarked. No WebM/Ogg, MPEG-PS/VOB or MXF result is claimed. Outputs are single-rendition VOD HLS with TS segments or fMP4 init + fragments; six-second requested target, actual cuts at existing keyframes.

## Evidence map

Paths in this table are relative to outputs/.

| Evidence | Path and interpretation |
|---|---|
| All serial cases, input probes, exact commands, runs, acceptance | hls-scaling/results.json — primary final data source |
| Individual measurement records | hls-scaling/measurements/ — measured process/resource records |
| FFmpeg logs | hls-scaling/logs/ — retain even empty logs; zero warnings is not correctness |
| Fresh-output control | hls-scaling/fresh-output.json |
| Concurrency and sampled aggregate RSS | hls-scaling/concurrency.json |
| Descriptive fits and table data | hls-scaling/analysis.json |
| Segment SHA/decode cache | hls-scaling/segment-validation-cache.json |
| Browser evidence | hls-scaling/browser-validation.json |
| Report UI QA | hls-scaling/report-qa.json |
| FFmpeg build | hls-scaling/ffmpeg-build.txt |
| Scripts | hls-scaling/scripts/ and hls-benchmark/scripts/ |
| Actual scaling inputs and references | hls-scaling/durations/{30s,1m,2m,5m,10m,full}/inputs/ and reference.mp4 |
| Actual scaling HLS | hls-scaling/durations/<length>/hls/<container>/{mpegts,fmp4}/ |
| Original baseline evidence | hls-benchmark/results.json, commands.json, adjustment-commands.json, fragmented-fix-commands.json, final-timing-commands.json, browser-validation.json, browser-stress-8x.json, logs/ |
| Additional historical notes and diagnostic logs | research-reference/supplemental-work/ — intermediate notes may describe then-running jobs; final results.json/report override stale status text |

Scripts retain local tool paths and require adaptation for another machine. Inspect scripts before running: some stages overwrite retained outputs or rerun the full workload. Fresh/concurrent temporary packages were intentionally removed after measurement; their measurements remain. No lost temporary assets are claimed to be present. Live server logs and Python bytecode caches are excluded from supplemental preservation.

## Column and metric dictionary

- Length: requested clip duration, with complete-source entry shown separately. Actual durations are in probes and validation.
- Input MB: prepared input bytes / 1,000,000; input varies with container overhead. Headline timings use standard MP4 only.
- TS / fMP4 warm s: five-run median elapsed FFmpeg process time with input pre-read outside the timer.
- TS / fMP4 evicted s: one run after file-specific fsync + POSIX_FADV_DONTNEED request; not a globally cold system.
- Valid paths: accepted container/output combinations; 24/28 at each length, 144/168 overall.
- CPU seconds: user + system CPU consumed by FFmpeg, summed over its threads; not elapsed seconds.
- CPU %: CPU seconds / elapsed × 100. 100% means one logical CPU; host has 12. Not percentage of all host capacity unless explicitly labelled host share.
- Peak RSS MiB: peak resident process memory / 1,048,576. Excludes OS page cache and application/browser overhead.
- Logical I/O: rchar/wchar, including cached accesses and some non-media I/O. Storage I/O: kernel read_bytes/write_bytes, not device NAND traffic.
- Extra fsync s: post-exit serial flush of output files then immediate directory. Exit + flush s: measured completion under that policy; not proof of crash-safe ancestor-directory persistence.
- Warm range: minimum and maximum of five warm observations; not a confidence interval or p95/p99.
- Exit jobs/s versus with-flush jobs/s: throughput under two different completion policies.
- PASS: all required acceptance gates pass; a zero exit code or playable beginning alone does not qualify.

## Resource interpretation from the chat

Storage persistence was the largest observed contributor to full-job completion under the measured flush policy. Fresh full-source standard-MP4 jobs exited in 0.771 s (TS) / 0.698 s (fMP4), versus 7.904 / 7.909 s including flush. They used 1.029 / 0.919 CPU-seconds and peaked at 91.5 / 88.6 MiB RSS. CPU performed packaging work; RAM pressure was not observed. Evicted-input timing stayed relatively close in fresh-output controls on this NVMe device.

These observations support filesystem/storage waiting as a major latency factor, not proof that every job or deployment is exclusively disk-bound. No device-level attribution, CPU-frequency sweep, controlled memory-bandwidth test, or isolated-storage experiment was performed. Fresh and repeated-target runs happened in different phases. Do not assign their difference exclusively to Btrfs. OS buffering explains why process exit can precede output persistence. Failed ASF fMP4 memory growth is diagnostic and must not represent a valid-job memory budget.

## Principal findings and limits

144/168 paths passed. AVI preserves compressed media but changes timing/alignment; ASF TS fails on unset initial PTS/DTS; ASF fMP4 exits zero with an invalid zero-duration playlist and changed timing. Exact logs and measured offsets are in the scaling report. This does not mean all AVI/ASF files fail.

Compatibility adaptations: aac_adtstoasc for relevant fMP4 AAC inputs; delay_moov for fragmented-MP4 preparation; H.264 Annex B adaptation for ASF; genpts tested for AVI. Initial failed attempts remain evidence. A null-validation-sink time-base issue was corrected without changing benchmark media or timings; actual packet timing was audited independently.

One film, one laptop, limited repetitions, non-isolated desktop, powersave governor, sustained writes and changing disk occupancy limit generalization. No production SLA, p95/p99, cloud/network/object-store throughput, cgroup limit, live HLS, DASH, ABR ladder, DRM, native Safari/iOS or subjective audiovisual quality conclusion is established. Full methods, assumptions, confidence and unsupported claims follow in the complete reports.
'''
(DEST/'README.md').write_text(intro)
combined=intro+'\n\n---\n\n# Scaling experiment: complete report\n\n'+(OUT/'hls-scaling/report.md').read_text()+'\n\n---\n\n# Original baseline: complete report\n\n'+(OUT/'hls-benchmark/report.md').read_text()
# Rebase relative Markdown links from the combined report to their original report folders.
import re
start=combined.index('# Scaling experiment: complete report')
a=combined[:start];tail=combined[start:];pivot=tail.index('# Original baseline: complete report')
def rebase(txt,base):
 return re.sub(r'\]\(([^)]+)\)',lambda m:']('+str(base/m.group(1))+')' if not (m.group(1).startswith(('/', 'http:', 'https:', '#'))) else m.group(0),txt)
combined=a+rebase(tail[:pivot],OUT/'hls-scaling')+rebase(tail[pivot:],OUT/'hls-benchmark')
(DEST/'complete-research-record.md').write_text(combined)
media={'.mp4','.ts','.m2ts','.m4s','.mov','.mkv','.avi','.asf','.flv','.f4v','.3gp','.3g2','.nut','.zip'}
files=[]
for base in [OUT/'hls-benchmark',OUT/'hls-scaling',DEST]:
 for p in sorted(base.rglob('*')):
  if not p.is_file() or p.name in ('inventory.json','inventory.html','evidence.zip','SHA256SUMS.txt'):continue
  ismedia=p.suffix.lower() in media
  files.append(dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,category='binary-media-or-source-archive' if ismedia else 'evidence',sha256=None if ismedia else hashlib.sha256(p.read_bytes()).hexdigest()))
(DEST/'inventory.json').write_text(json.dumps(dict(base_directory=str(OUT),note='Media sizes inventoried; media bytes not rehashed. Evidence SHA-256 hashes are integrity checks, not external authentication.',files=files),indent=2))
from urllib.parse import quote
rows=''.join('<tr><td><a href="../'+quote(x['path'])+'">'+html.escape(x['path'])+'</a></td><td>'+str(x['bytes'])+'</td><td>'+x['category']+'</td></tr>' for x in files)
(DEST/'inventory.html').write_text('<!doctype html><meta charset="utf-8"><title>Research evidence inventory</title><style>body{font:14px system-ui;margin:30px}td,th{padding:5px;text-align:left;border-bottom:1px solid #ddd}input{padding:9px;width:50%}</style><h1>Research file inventory</h1><p>'+str(len(files))+' retained files. Filter by path, container, duration or extension. Media remains in its original directories.</p><input placeholder="Filter files" oninput="for(const r of document.querySelectorAll(\'tbody tr\'))r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase())"><table><thead><tr><th>File</th><th>Bytes</th><th>Category</th></tr></thead><tbody>'+rows+'</tbody></table>')
(DEST/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in files if x['sha256']))
with zipfile.ZipFile(DEST/'evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for x in files:
  if x['category']=='evidence':z.write(OUT/x['path'],x['path'])
 for name in ['inventory.json','inventory.html','SHA256SUMS.txt']:z.write(DEST/name,'research-reference/'+name)
print(json.dumps(dict(inventoried_files=len(files),logical_bytes=sum(x['bytes']for x in files),evidence_files=sum(x['category']=='evidence'for x in files),measured_serial_runs=len(flat),archive_bytes=(DEST/'evidence.zip').stat().st_size),indent=2))
