import json, html, shutil, shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/hls-benchmark'
r=json.loads((OUT/'results.json').read_text())
browser=json.loads((OUT/'browser-validation.json').read_text())
browser_map={(t['container'],t['kind']):t for t in browser['tests']}

def status(f,kind):
 d=f['outputs'].get(kind,{})
 v=d.get('validation',{})
 b=browser_map.get((f['key'],kind),{})
 return 'PASS' if v.get('passed') and b.get('passed') else 'FAIL'

def seconds(f,kind):
 d=f['outputs'].get(kind,{})
 return f"{d['median_seconds']:.3f}" if 'median_seconds' in d else '—'

rows=[]
for f in r['fixtures']:
 rows.append([f['container'],'H.264','1920×1080',seconds(f,'mpegts'),seconds(f,'fmp4'),status(f,'mpegts'),status(f,'fmp4')])
 for kind,d in f['outputs'].items():
  d['overall_passed']=status(f,kind)=='PASS'
  d['browser_test']=browser_map.get((f['key'],kind),{'passed':False,'reason':'No playable output produced'})
(OUT/'results.json').write_text(json.dumps(r,indent=2))
headers=['Original container / layout','Video codec','Resolution','HLS TS (s)','HLS fMP4 (s)','TS validation','fMP4 validation']
table='| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'
table+='\n'.join('| '+' | '.join(row)+' |' for row in rows)
passed=sum(status(f,k)=='PASS' for f in r['fixtures'] for k in ['mpegts','fmp4'])
intro=f'''# H.264 → HLS remuxing benchmark

Test date: 15 October 2026, Africa/Cairo. **{passed}/28 outputs passed both media validation and normal-speed browser playback.**

The table reports median wall-clock seconds from five measured runs, after one warm-up. Values marked FAIL are not approved working HLS outputs even if FFmpeg produced a file.

{table}

## Sample and controls

- Same H.264 High-profile, 1920×1080, 30 fps, yuv420p stream for every fixture; 900 decoded video frames, nominally 30 seconds. B-frames are present.
- Source: [Big Buck Bunny, Blender download](https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip). The MP4 contains MP3 and AC-3 audio; the first audio track was converted to AAC LC, 48 kHz stereo, 128 kb/s once during fixture preparation. Every measured operation uses `-c copy` for video and audio.
- A common TS intermediate normalizes source edit-list/priming behavior before preparing the input containers. Decoded frame hashes and PCM hashes are checked against `reference.mp4`.
- The requested segment target is six seconds. Keyframe-preserving remuxing produces five segments per passing output: approximately 8.333, 7.900, 3.867, 7.300, and 2.600 seconds. These are not exact six-second segments. The reference timestamps and AAC packet boundaries make player duration approximately 30.1 seconds.
- MP4 variants are actual different file layouts: standard, fast-start, and fragmented. Other ISO base media relatives (MOV, F4V, 3GP, 3G2) are listed separately; their file extensions do not represent different video codecs.

## Timing method and environment

{r.get('timing_method','Five repeated wall-clock measurements with a warm filesystem cache.')}

- CPU: AMD Ryzen 5 PRO 5650U, 6 cores / 12 logical CPUs.
- FFmpeg: `{r['ffmpeg']}`.
- OS: `{r['platform']}`.
- Browser: Chromium `{browser['browser']}` with `{browser['player']}` over localhost HTTP.
- Timings apply to this short sample and this machine. Startup and container probing contribute materially; these results should not be extrapolated linearly to large files. The test does not measure upload time, CDN/network behavior, cold storage, or durable disk flushes.

## What PASS means

1. Every playlist references existing, nonempty files, has VOD/end markers, and has a valid target duration. fMP4 outputs also reference an existing initialization segment.
2. The complete playlist decodes with strict FFmpeg error handling. All 900 decoded video frames match the reference, frame by frame, and decoded audio PCM matches the reference exactly.
3. Every individual TS segment, or fMP4 fragment combined with its initialization segment, decodes independently and begins with a video keyframe.
4. Decode timestamps increase. Presentation timestamps, including relative audio/video alignment, match the reference within 2 ms after allowing a shared container start-time shift.
5. The browser preloads the clip, seeks to 18 seconds and back to the beginning, and plays to the end at normal speed with no HLS.js or media errors. Playback starts at 0.1 seconds to avoid the reference's small leading audio-only interval. This is automated muted playback, not a human listening test.

This establishes correctness for the tested assets and browser. Safari/iOS native HLS, other hardware decoders, and variable network conditions were not tested. Browser dropped-frame counters are retained in the raw results; they describe rendering under the local test load, separately from the decoded-frame integrity check.

## Compatibility findings

- **Fragmented MP4 fixture:** `+frag_keyframe+delay_moov+default_base_moof` preserves the reference's initial relative audio/video alignment. The first `empty_moov` preparation shifted alignment by approximately 21 ms; the timestamp audit rejected it despite successful playback. The corrected fixture and both corrected HLS outputs were revalidated. The first attempt remains in the raw results.
- **TS/M2TS → fMP4:** requires `-bsf:a aac_adtstoasc` in this workflow. It adapts AAC packet headers without re-encoding. The initial unadapted attempts failed and remain recorded.
- **ASF:** fixture preparation requires `-bsf:v h264_mp4toannexb` to produce a decodable H.264 ASF file with this FFmpeg build. That bitstream adaptation does not re-encode video. The subsequent HLS TS mux still fails on missing timestamps, and the fMP4 output fails strict timing/decode validation. Both ASF paths are rejected.
- **AVI:** this H.264 B-frame fixture exposes timestamp limitations. `-fflags +genpts` was tested. Both resulting HLS variants reach the end in the browser, but strict validation catches non-monotonic presentation timestamps, so both are rejected. This is a finding for this fixture, not a claim that every H.264 AVI file must fail.
- WebM and Ogg are outside the H.264 container selection. MPEG-PS, DVD/VOB, and MXF are not claimed as tested here. File aliases alone are not counted as additional container coverage.
- An exploratory 8× browser stress run reached playback completion but logged buffering warnings. It is preserved separately as `browser-stress-8x.json`; the PASS statuses above require the subsequent normal-speed run with no HLS/media errors. No claim of clean 8× playback is made.

## Files and reproduction

- `inputs/`: the actual input fixtures; `reference.mp4`: the common reference.
- `hls/<input>/mpegts/playlist.m3u8`: TS HLS output.
- `hls/<input>/fmp4/playlist.m3u8`: fMP4 HLS output, `init.mp4`, and `.m4s` fragments.
- `results.json`: all measured runs, codec probes, validation results, and initial failures.
- `browser-validation.json`: normal-speed browser playback and seeking results.
- `logs/`: FFmpeg logs and per-frame MD5 records. `commands.json`, `adjustment-commands.json`, and `final-timing-commands.json` contain the exact executed command arguments.
- `scripts/`: benchmark, compatibility adjustments, timestamp audit, final timing, and browser harness scripts. They retain this workspace's tool paths; adjust them for another machine. For the Python scripts, `HLS_BENCHMARK_ROOT` can point to the workspace root containing `work/` and `outputs/`. The source download belongs in `work/` under its original MP4 filename.

To play the files, serve this output directory over HTTP and open `report.html`; local `file://` playback does not provide the same browser behavior. Serve only trusted test files.

## Attribution

Big Buck Bunny © 2008 Blender Foundation / www.bigbuckbunny.org. Source material licensed under Creative Commons Attribution 3.0: https://peach.blender.org/about/ . This test uses a shortened excerpt, remuxed video, and a prepared AAC audio track. The source MP4 SHA-256 is `{r['source_sha256']}`.
'''
(OUT/'report.md').write_text(intro)

# Build a compact local report with a playable selector for validated assets.
table_html='<table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'
for row in rows:
 table_html+='<tr>'+''.join('<td class="'+('pass' if x=='PASS' else 'fail' if x=='FAIL' else '')+'">'+html.escape(x)+'</td>' for x in row)+'</tr>'
table_html+='</tbody></table>'
options=[]
for f in r['fixtures']:
 for k in ['mpegts','fmp4']:
  if status(f,k)=='PASS':
   options.append('<option value="'+html.escape(f['outputs'][k]['playlist'],quote=True)+'">'+html.escape(f['container']+' — '+('TS segments' if k=='mpegts' else 'fMP4 segments'))+'</option>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>H.264 to HLS benchmark</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:1180px;margin:36px auto;padding:0 20px;color:#18232d;background:#f6f8fa}h1{font-size:30px;margin-bottom:6px}table{border-collapse:collapse;width:100%;background:white;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #dae1e7}th{background:#e8edf2}td.pass{color:#067143;font-weight:700}td.fail{color:#b22e2e;font-weight:700}video{display:block;width:min(900px,100%);background:#111;margin-top:16px}select,button{font:inherit;padding:8px}a{color:#175ba8}.note{max-width:950px}.scroll{overflow:auto}#status{white-space:pre-wrap}</style>
<h1>H.264 → HLS benchmark</h1><p>15 October 2026 · 1920×1080 · 30 fps · 900 frames · median of five runs</p>
<p class="note">TIMING seconds include FFmpeg startup and complete packaging. PASS requires exact decoded video/audio, independent segment decoding, timestamp integrity, and error-free normal-speed browser playback. Failed rows are retained as compatibility findings.</p>
<div class="scroll">'''+table_html+'''</div><p><a href="report.md">Full methodology and findings</a> · <a href="results.json">Raw benchmark results</a> · <a href="browser-validation.json">Browser validation</a></p>
<h2>Play a validated output</h2><p>Serve this folder over HTTP. Only outputs that passed all checks are listed.</p>
<select id="choice">'''+''.join(options)+'''</select> <button id="load">Load video</button><video id="video" controls playsinline preload="auto"></video><p id="status">Choose an output and click Load video.</p>
<p>Big Buck Bunny © 2008 Blender Foundation / www.bigbuckbunny.org · CC BY 3.0. Prepared test excerpt.</p>
<script src="assets/hls.min.js"></script><script>
let hls;const v=document.querySelector('video'),status=document.querySelector('#status');document.querySelector('#load').onclick=()=>{if(hls)hls.destroy();const url=document.querySelector('#choice').value;status.textContent=url;if(Hls.isSupported()){hls=new Hls();hls.on(Hls.Events.ERROR,(_,d)=>status.textContent+='\\n'+d.type+': '+d.details);hls.loadSource(url);hls.attachMedia(v);}else if(v.canPlayType('application/vnd.apple.mpegurl'))v.src=url;else status.textContent='This browser has no supported HLS playback path.';};
</script></html>'''
(OUT/'report.html').write_text(page)
(OUT/'assets').mkdir(exist_ok=True)
shutil.copy(ROOT/'work/hls.min.js',OUT/'assets/hls.min.js')
shutil.copy(ROOT/'work/hls-LICENSE.txt',OUT/'assets/hls-LICENSE.txt')
(OUT/'scripts').mkdir(exist_ok=True)
for name in ['benchmark.py','repair.py','fix-fragmented.py','final-timings.py','timing-audit.py','browser-test.cjs','player-test.html']:
 shutil.copy(ROOT/'work'/name,OUT/'scripts'/name)
(OUT/'final-table.md').write_text(table+'\n')
print(table)
print('PASSED',passed,'OF 28')
