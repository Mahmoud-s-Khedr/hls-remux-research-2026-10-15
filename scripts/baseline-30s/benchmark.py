import subprocess, json, time, hashlib, statistics, random, platform, os, re
from pathlib import Path

ROOT = Path(os.environ.get('HLS_BENCHMARK_ROOT', Path(__file__).resolve().parents[1]))
OUT = ROOT / 'outputs/hls-benchmark'
WORK = ROOT / 'work'
OUT.mkdir(parents=True, exist_ok=True)
for name in ['inputs', 'hls', 'logs']:
    (OUT/name).mkdir(exist_ok=True)
BASE = ['ffmpeg', '-hide_banner', '-nostdin', '-y', '-loglevel', 'warning']
COMMANDS = []

def run(args, log=None):
    COMMANDS.append(args)
    start = time.perf_counter()
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elapsed = time.perf_counter() - start
    if log:
        (OUT/'logs'/log).write_bytes(p.stderr)
    return p, elapsed

def probe(path, packets=False):
    args = ['ffprobe', '-v', 'error', '-show_streams', '-show_format']
    if packets:
        args += ['-show_packets', '-show_entries', 'packet=stream_index,pts_time,dts_time,duration_time,flags']
    p, _ = run(args+['-of', 'json', str(path)])
    if p.returncode:
        raise RuntimeError(p.stderr.decode())
    return json.loads(p.stdout)

def identity(path, label):
    p, _ = run(BASE+['-xerror', '-err_detect', 'explode', '-threads', '2', '-i', str(path),
        '-map', '0:v:0', '-an', '-fps_mode', 'passthrough', '-c:v', 'rawvideo',
        '-threads:v', '2', '-f', 'framemd5', '-'], label+'-video.log')
    if p.returncode:
        raise RuntimeError(p.stderr.decode())
    lines = [x for x in p.stdout.decode().splitlines() if x and not x.startswith('#')]
    hashes = [x.split(',')[-1].strip() for x in lines]
    (OUT/'logs'/(label+'-framemd5.txt')).write_bytes(p.stdout)
    a, _ = run(BASE+['-xerror', '-err_detect', 'explode', '-threads', '2', '-i', str(path),
        '-map', '0:a:0', '-vn', '-c:a', 'pcm_s16le', '-f', 's16le', '-'], label+'-audio.log')
    if a.returncode:
        raise RuntimeError(a.stderr.decode())
    return {'frames': len(hashes), 'video_hash': hashlib.sha256('\n'.join(hashes).encode()).hexdigest(),
        'audio_hash': hashlib.sha256(a.stdout).hexdigest(), 'audio_bytes': len(a.stdout)}

SPECS = [
    ('mp4', 'MP4 (standard)', 'mp4', ['-f','mp4']),
    ('mp4_faststart', 'MP4 (fast-start)', 'mp4', ['-f','mp4','-movflags','+faststart']),
    ('mp4_fragmented', 'MP4 (fragmented)', 'mp4', ['-f','mp4','-movflags','+frag_keyframe+delay_moov+default_base_moof']),
    ('mov', 'QuickTime / MOV', 'mov', ['-f','mov']),
    ('mkv', 'Matroska / MKV', 'mkv', ['-f','matroska']),
    ('ts', 'MPEG-TS', 'ts', ['-f','mpegts']),
    ('m2ts', 'MPEG-TS (M2TS mode)', 'm2ts', ['-f','mpegts','-mpegts_m2ts_mode','1']),
    ('avi', 'AVI', 'avi', ['-f','avi']),
    ('flv', 'Flash Video / FLV', 'flv', ['-f','flv']),
    ('f4v', 'Adobe F4V', 'f4v', ['-f','f4v']),
    ('3gp', '3GPP / 3GP', '3gp', ['-f','3gp']),
    ('3g2', '3GPP2 / 3G2', '3g2', ['-f','3g2']),
    ('nut', 'NUT', 'nut', ['-f','nut']),
    ('asf', 'ASF', 'asf', ['-f','asf','-bsf:v','h264_mp4toannexb']),
]

def mux_command(path, folder, kind):
    input_options = ['-fflags','+genpts'] if path.suffix == '.avi' else []
    args = BASE+input_options+['-i',str(path),'-map','0:v:0','-map','0:a:0','-c','copy',
        '-f','hls','-hls_time','6','-hls_playlist_type','vod','-hls_list_size','0',
        '-hls_flags','independent_segments','-hls_segment_type',kind]
    if kind == 'fmp4':
        args += ['-hls_fmp4_init_filename','init.mp4','-bsf:a','aac_adtstoasc']
    ext = 'ts' if kind == 'mpegts' else 'm4s'
    return args+['-hls_segment_filename',str(folder/('segment_%03d.'+ext)),str(folder/'playlist.m3u8')]

def validate(path, folder, kind, reference, label):
    playlist = folder/'playlist.m3u8'
    text = playlist.read_text()
    segments = [x for x in text.splitlines() if x and not x.startswith('#')]
    durations = [float(x.split(':')[1].rstrip(',')) for x in text.splitlines() if x.startswith('#EXTINF:')]
    target = int(re.search(r'#EXT-X-TARGETDURATION:(\d+)', text)[1])
    checks = {'endlist': '#EXT-X-ENDLIST' in text, 'vod': '#EXT-X-PLAYLIST-TYPE:VOD' in text,
        'files_exist': all((folder/s).is_file() and (folder/s).stat().st_size > 0 for s in segments),
        'targetduration_valid': all(int(d+0.5) <= target for d in durations),
        'segment_count': len(segments), 'segment_durations': durations, 'playlist_duration':sum(durations)}
    if kind == 'fmp4':
        checks['init_exists'] = (folder/'init.mp4').is_file() and '#EXT-X-MAP:' in text
    ident = identity(playlist, label)
    checks['decoded'] = ident
    checks['video_matches_source'] = ident['video_hash'] == reference['video_hash']
    checks['audio_matches_source'] = ident['audio_hash'] == reference['audio_hash']
    info = probe(playlist, True)
    checks['codecs'] = [s['codec_name'] for s in info['streams']]
    checks['codecs_correct'] = checks['codecs'] == ['h264','aac']
    dts = {}
    for packet in info.get('packets',[]):
        if 'dts_time' in packet:
            dts.setdefault(packet['stream_index'],[]).append(float(packet['dts_time']))
    checks['dts_monotonic'] = all(all(b>a for a,b in zip(t,t[1:])) for t in dts.values())
    pts = {}
    for p in info.get('packets',[]):
        if 'pts_time' in p:
            pts.setdefault(p['stream_index'],[]).append((float(p['pts_time']),float(p.get('duration_time',0))))
    checks['stream_spans'] = {str(k): {'start':min(x[0] for x in v),'end':max(x[0]+x[1] for x in v)} for k,v in pts.items()}
    checks['segment_checks'] = []
    for i, segment in enumerate(segments):
        segpath = folder/segment
        if kind == 'fmp4':
            temp = WORK/'validate-fragment.mp4'
            temp.write_bytes((folder/'init.mp4').read_bytes()+segpath.read_bytes())
            segpath = temp
        p, _ = run(BASE+['-xerror','-err_detect','explode','-threads','2','-i',str(segpath),
            '-map','0:v:0','-map','0:a:0','-f','null','-'],label+f'-segment-{i}.log')
        pi = probe(segpath, True)
        vp = [q for q in pi.get('packets',[]) if q['stream_index']==0]
        checks['segment_checks'].append({'file':segment,'decode_ok':p.returncode==0,
            'starts_keyframe':bool(vp and 'K' in vp[0].get('flags','')),
            'warnings':p.stderr.decode()})
    required = ['endlist','vod','files_exist','targetduration_valid','video_matches_source',
        'audio_matches_source','codecs_correct','dts_monotonic']
    if kind == 'fmp4': required += ['init_exists']
    checks['passed'] = all(checks[k] for k in required) and all(s['decode_ok'] and s['starts_keyframe'] for s in checks['segment_checks'])
    return checks

def main():
    source = WORK/'bbb_sunflower_1080p_30fps_normal.mp4'
    # Prepare common AAC audio once; every measured job copies both video and audio.
    # TS intermediate removes MP4-specific priming/edit-list behavior equally for every fixture.
    cmd = BASE+['-i',str(source),'-t','30','-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','128k',
        '-avoid_negative_ts','make_zero','-f','mpegts',str(WORK/'reference.ts')]
    p,_ = run(cmd,'prepare-reference.log')
    assert p.returncode == 0, p.stderr.decode()
    p,_ = run(BASE+['-i',str(WORK/'reference.ts'),'-map','0:v:0','-map','0:a:0','-c','copy',str(OUT/'reference.mp4')], 'prepare-reference-mp4.log')
    assert p.returncode == 0, p.stderr.decode()
    reference = identity(OUT/'reference.mp4','reference')
    print('REFERENCE',reference,flush=True)
    results = {'source_url':'https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip',
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'ffmpeg':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
        'platform':platform.platform(),'cpu':subprocess.check_output(['lscpu'],text=True),
        'date_local':'2026-10-15','reference':reference,'reference_probe':probe(OUT/'reference.mp4'),
        'repeats':5,'warmups':1,'fixtures':[]}
    def save():
        (OUT/'results.json').write_text(json.dumps(results,indent=2))
        (OUT/'commands.json').write_text(json.dumps(COMMANDS,indent=2))
    for key,label,ext,options in SPECS:
        path = OUT/'inputs'/f'{key}.{ext}'
        fixture = {'key':key,'container':label,'file':str(path.relative_to(OUT)),'outputs':{}}
        results['fixtures'].append(fixture)
        p,_ = run(BASE+['-i',str(OUT/'reference.mp4'),'-map','0:v:0','-map','0:a:0','-c','copy']+options+[str(path)],key+'-prepare.log')
        fixture['prepare_ok'] = p.returncode==0
        fixture['prepare_warnings'] = p.stderr.decode()
        if p.returncode:
            print('PREPARE FAILED',key,p.stderr.decode(),flush=True); save(); continue
        fixture['probe'] = probe(path)
        try:
            fixture['identity'] = identity(path,key+'-input')
            fixture['video_matches_reference'] = fixture['identity']['video_hash']==reference['video_hash']
        except Exception as e:
            fixture['identity_error'] = str(e)
        for kind in ['mpegts','fmp4']:
            folder = OUT/'hls'/key/kind
            folder.mkdir(parents=True,exist_ok=True)
            cmd = mux_command(path,folder,kind)
            p,_ = run(cmd,key+'-'+kind+'-warmup.log')
            data = {'command':cmd,'warmup_ok':p.returncode==0,'warmup_warnings':p.stderr.decode(),
                'playlist':str((folder/'playlist.m3u8').relative_to(OUT)),'times_seconds':[]}
            fixture['outputs'][kind] = data
        save()
        print('PREPARED',key,flush=True)
    # Randomize the complete case order each round; never run timed jobs concurrently.
    cases = [(f,k,d) for f in results['fixtures'] for k,d in f['outputs'].items() if d['warmup_ok']]
    rng = random.Random(42)
    for repeat in range(5):
        rng.shuffle(cases)
        for fixture,kind,data in cases:
            p,elapsed = run(data['command'],fixture['key']+'-'+kind+f'-run{repeat+1}.log')
            data['times_seconds'].append(elapsed)
            if p.returncode:
                data['timing_error'] = p.stderr.decode()
        save(); print('TIMING ROUND',repeat+1,flush=True)
    for fixture in results['fixtures']:
        for kind,data in fixture['outputs'].items():
            if not data['warmup_ok']:
                print('MUX FAILED',fixture['key'],kind,data['warmup_warnings'],flush=True); continue
            data['median_seconds'] = statistics.median(data['times_seconds'])
            data['min_seconds'] = min(data['times_seconds'])
            data['max_seconds'] = max(data['times_seconds'])
            try:
                data['validation'] = validate(OUT/fixture['file'], OUT/Path(data['playlist']).parent,kind,reference,fixture['key']+'-'+kind)
                print('VALIDATED',fixture['key'],kind,data['validation']['passed'],
                    'video',data['validation']['video_matches_source'],'audio',data['validation']['audio_matches_source'],flush=True)
            except Exception as e:
                data['validation_error'] = str(e)
                print('VALIDATION ERROR',fixture['key'],kind,str(e)[:500],flush=True)
            save()
    save()

if __name__ == '__main__': main()
