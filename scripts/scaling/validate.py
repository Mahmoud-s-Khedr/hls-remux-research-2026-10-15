"""Full packet/timeline integrity plus independent decoding of every unique segment."""
import sys,json,re,hashlib,subprocess,math,time
from pathlib import Path
import run as b
OUT=b.OUT;WORK=b.WORK
CACHEFILE=OUT/'segment-validation-cache.json'
CACHE=json.loads(CACHEFILE.read_text()) if CACHEFILE.exists() else {}
SIGNATURES={}

def mp4_boxes(raw):
    names=[];pos=0
    while pos+8<=len(raw):
        size=int.from_bytes(raw[pos:pos+4],'big');name=raw[pos+4:pos+8].decode('ascii',errors='replace');header=8
        if size==1:
            if pos+16>len(raw):return []
            size=int.from_bytes(raw[pos+8:pos+16],'big');header=16
        if size==0:size=len(raw)-pos
        if size<header or pos+size>len(raw):return []
        names.append(name);pos+=size
    return names if pos==len(raw) else []

def canonical(path,label):
    """Hash ordered H.264 VCL NAL units and parameter sets; normalize Annex B framing."""
    log=OUT/'logs'/(label+'-elementary-video.log')
    args=b.BASE+['-i',str(path),'-map','0:v:0','-an','-c:v','copy','-bsf:v','h264_mp4toannexb','-f','h264','-']
    vhash=hashlib.sha256();params=set();count=0;pending=b''
    def consume(nal):
        nonlocal count
        nal=nal.rstrip(b'\0')
        if not nal:return
        typ=nal[0]&31
        if typ in [1,2,3,4,5]:
            vhash.update(len(nal).to_bytes(4,'big'));vhash.update(nal);count+=1
        elif typ in [7,8]:params.add(hashlib.sha256(nal).hexdigest())
    with log.open('wb') as err:
        p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=err)
        while True:
            chunk=p.stdout.read(1024*1024)
            if not chunk:break
            pieces=(pending+chunk).split(b'\x00\x00\x01')
            for piece in pieces[:-1]:consume(piece)
            pending=pieces[-1]
        consume(pending);code=p.wait()
    if code:raise RuntimeError(log.read_text()[:1200])
    ahash=hashlib.sha256();abytes=0
    alog=OUT/'logs'/(label+'-elementary-audio.log')
    with alog.open('wb') as err:
        p=subprocess.Popen(b.BASE+['-i',str(path),'-map','0:a:0','-vn','-c:a','copy','-f','adts','-'],stdout=subprocess.PIPE,stderr=err)
        while True:
            chunk=p.stdout.read(1024*1024)
            if not chunk:break
            ahash.update(chunk);abytes+=len(chunk)
        code=p.wait()
    if code:raise RuntimeError(alog.read_text()[:1200])
    return {'video_vcl_sha256':vhash.hexdigest(),'vcl_nal_count':count,'parameter_sets':sorted(params),
        'aac_adts_sha256':ahash.hexdigest(),'aac_adts_bytes':abytes}

def timing(info,reference):
    def extract(x):
        tracks={}
        for p in x.get('packets',[]):
            if 'pts_time' in p:tracks.setdefault(p['stream_index'],[]).append(float(p['pts_time']))
        return {k:sorted(v) for k,v in tracks.items()}
    src=extract(reference);dst=extract(info)
    if not all(k in src and k in dst for k in [0,1]):return {'passed':False,'error':'Missing packet timestamps'}
    origin=src[1][0];other=dst[1][0];checks={}
    for k in [0,1]:
        checks[str(k)]={'reference_packets':len(src[k]),'output_packets':len(dst[k])}
        if len(src[k])==len(dst[k]):checks[str(k)]['max_error_seconds']=max(abs((a-other)-(e-origin)) for a,e in zip(dst[k],src[k]))
        sd=sorted((float(p['pts_time']),float(p['duration_time'])) for p in reference.get('packets',[]) if p['stream_index']==k and 'pts_time' in p and 'duration_time' in p)
        dd=sorted((float(p['pts_time']),float(p['duration_time'])) for p in info.get('packets',[]) if p['stream_index']==k and 'pts_time' in p and 'duration_time' in p)
        if sd and len(sd)==len(dd):
            checks[str(k)]['max_packet_duration_error_seconds']=max(abs(a[1]-e[1]) for a,e in zip(dd,sd))
            checks[str(k)]['end_time_error_seconds']=abs((dd[-1][0]+dd[-1][1]-other)-(sd[-1][0]+sd[-1][1]-origin))
    dts={}
    for p in info.get('packets',[]):
        if 'dts_time' in p:dts.setdefault(p['stream_index'],[]).append(float(p['dts_time']))
    monotonic=all(all(y>x for x,y in zip(v,v[1:])) for v in dts.values())
    pts_monotonic_when_presented=all(len(set(v))==len(v) for v in dst.values())
    passed=all(x.get('max_error_seconds',999)<=.002 and x.get('max_packet_duration_error_seconds',0)<=.002 and x.get('end_time_error_seconds',0)<=.002 for x in checks.values()) and monotonic and pts_monotonic_when_presented
    return {'passed':passed,'tolerance_seconds':.002,'streams':checks,'dts_strictly_increasing':monotonic,
        'unique_presentation_timestamps':pts_monotonic_when_presented,
        'reference_video_minus_audio_start':src[0][0]-src[1][0],
        'actual_video_minus_audio_start':dst[0][0]-dst[1][0]}

def strict_decode(path,label):
    started=time.perf_counter()
    p=b.run(b.BASE+['-xerror','-err_detect','explode','-threads','4','-i',str(path),
        '-map','0:v:0','-map','0:a:0','-fps_mode','passthrough','-enc_time_base:v','1:90000','-f','null','-'],label+'.log')
    msg=p.stderr.decode()
    return {'passed':p.returncode==0 and not re.search(r'non.monoton|invalid|corrupt|decod.*error',msg,re.I),
        'wall_seconds':time.perf_counter()-started,
        'returncode':p.returncode,'log':'logs/'+label+'.log','messages':msg[:2500]}

def segment(folder,name,init):
    raw=(folder/name).read_bytes();prefix=init or b''
    signature=hashlib.sha256(prefix+raw).hexdigest()
    if signature in CACHE:return {'sha256':signature,'cache_hit':True,**CACHE[signature]}
    path=folder/name
    if init:
        path=WORK/'validate-fragment.mp4';path.write_bytes(prefix+raw)
    structure=('moof' in mp4_boxes(raw) and 'mdat' in mp4_boxes(raw) and 'moov' in mp4_boxes(init)) if init else (len(raw)%188==0 and raw[::188].count(0x47)==len(raw[::188]))
    decoded=strict_decode(path,'segment-'+signature)
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-read_intervals','%+0.2',
        '-show_packets','-show_entries','packet=flags','-of','json',str(path)],capture_output=True)
    packets=json.loads(p.stdout).get('packets',[]) if p.returncode==0 else []
    check={'decode':decoded,'container_structure_ok':structure,'starts_with_keyframe':bool(packets and 'K' in packets[0].get('flags',''))}
    check['passed']=decoded['passed'] and check['starts_with_keyframe'] and structure
    CACHE[signature]=check
    if len(CACHE)%10==0:CACHEFILE.write_text(json.dumps(CACHE,indent=2))
    return {'sha256':signature,'cache_hit':False,**check}

def validate(c,reference_identity,reference_packets):
    playlist=OUT/c['playlist'];folder=playlist.parent
    text=playlist.read_text();names=[x for x in text.splitlines() if x and not x.startswith('#')]
    durations=[float(x.split(':')[1].rstrip(',')) for x in text.splitlines() if x.startswith('#EXTINF:')]
    target=int(re.search(r'#EXT-X-TARGETDURATION:(\d+)',text)[1])
    checks={'playlist_header':text.startswith('#EXTM3U'),'playlist_endlist':'#EXT-X-ENDLIST' in text,'playlist_vod':'#EXT-X-PLAYLIST-TYPE:VOD' in text,
        'segments_exist':all((folder/n).is_file() and (folder/n).stat().st_size for n in names),
        'target_duration_valid':bool(target>=1 and len(names)==len(durations) and names and all(x>0 and int(x+.5)<=target for x in durations)),
        'segment_count':len(names),'playlist_seconds':sum(durations),'target_duration_seconds':target}
    init=None
    if c['kind']=='fmp4':
        checks['init_exists']=(folder/'init.mp4').exists() and '#EXT-X-MAP:' in text
        init=(folder/'init.mp4').read_bytes()
    ident=canonical(playlist,c['id'])
    checks['encoded_media_identity']=ident
    checks['video_payload_matches']=ident['video_vcl_sha256']==reference_identity['video_vcl_sha256']
    checks['parameter_sets_match']=ident['parameter_sets']==reference_identity['parameter_sets']
    checks['audio_payload_matches']=ident['aac_adts_sha256']==reference_identity['aac_adts_sha256']
    info=b.probe(playlist,True)
    checks['codec_resolution_correct']=len(info['streams'])==2 and info['streams'][0]['codec_name']=='h264' and info['streams'][0]['width']==1920 and info['streams'][0]['height']==1080 and info['streams'][1]['codec_name']=='aac'
    checks['timing']=timing(info,reference_packets)
    # Fail early for known corrupt timelines; retain evidence without redundant decode work.
    mandatory=['playlist_header','playlist_endlist','playlist_vod','segments_exist','target_duration_valid','video_payload_matches','parameter_sets_match','audio_payload_matches','codec_resolution_correct']
    if c['kind']=='fmp4':mandatory+=['init_exists']
    preliminary=all(checks[k] for k in mandatory) and checks['timing']['passed']
    checks['segments']=[]
    if preliminary:
        for n in names:
            checks['segments'].append({'file':n,**segment(folder,n,init)})
    checks['passed']=bool(preliminary and checks['segments'] and all(s['passed'] for s in checks['segments']))
    if not preliminary:checks['segment_decode_skipped_reason']='Already failed payload/codec/manifest/timestamp checks'
    return checks

def main():
    started=time.perf_counter()
    r=json.loads(b.STATE.read_text());r['status']='validating';b.save(r)
    for d in r['durations']:
        reference=OUT/d['reference']
        refident=canonical(reference,d['key']+'-reference')
        refpackets=b.probe(reference,True)
        if 'reference_validation' not in d:
            d['reference_validation']={'encoded_media_identity':refident,
                'strict_decode':strict_decode(reference,d['key']+'-reference-decode')}
            b.save(r)
        for c in d['cases']:
            if 'validation' in c or 'validation_error' in c:continue
            if not c['summary']['all_runs_exit_ok']:
                c['validation']={'passed':False,'reason':'FFmpeg muxing failed'}
            else:
                try:c['validation']=validate(c,refident,refpackets)
                except Exception as e:c['validation_error']=str(e)
            v=c.get('validation',{})
            print('VALIDATED',c['id'],v.get('passed',False),'segments',v.get('segment_count'),'cache',len(CACHE),flush=True)
            b.save(r);CACHEFILE.write_text(json.dumps(CACHE,indent=2))
    # Decode a complete long TS and fMP4 playlist in addition to all individual segments.
    full=next(d for d in r['durations'] if d['key']=='full')
    for c in full['cases']:
        if c['container_key']=='mp4' and c.get('validation',{}).get('passed'):
            c['full_playlist_decode']=strict_decode(OUT/c['playlist'],c['id']+'-whole-playlist-decode')
            c['validation']['passed'] &= c['full_playlist_decode']['passed'];b.save(r)
    r['status']='media_validation_complete';r['unique_segment_decode_count']=len(CACHE)
    r['media_validation_wall_seconds']=time.perf_counter()-started;b.save(r)
    print('MEDIA VALIDATION COMPLETE',len(CACHE),'unique segment assets',flush=True)

if __name__=='__main__':main()
