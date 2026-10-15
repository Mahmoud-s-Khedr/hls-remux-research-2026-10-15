import benchmark as b
import json
file=b.OUT/'results.json'
r=json.loads(file.read_text())
def pts(path):
    info=b.probe(path,True)
    tracks={}
    for p in info['packets']:
        if 'pts_time' in p:
            tracks.setdefault(p['stream_index'],[]).append(float(p['pts_time']))
    return {k:sorted(v) for k,v in tracks.items()}
reference=pts(b.OUT/'reference.mp4')
origin=min(reference[1])
for f in r['fixtures']:
    for kind,d in f['outputs'].items():
        if not d['warmup_ok'] or 'validation' not in d:continue
        try:
            actual=pts(b.OUT/d['playlist'])
            actual_origin=min(actual[1])
            deviations={}
            for idx in [0,1]:
                if len(actual[idx])!=len(reference[idx]):deviations[str(idx)]={'count_match':False};continue
                deviations[str(idx)]={'count_match':True,'max_error_seconds':max(abs((a-actual_origin)-(e-origin)) for a,e in zip(actual[idx],reference[idx]))}
            passed=all(x['count_match'] and x['max_error_seconds']<=0.002 for x in deviations.values())
            d['validation']['presentation_timing']={'passed':passed,'tolerance_seconds':0.002,'streams':deviations,
                'reference_video_minus_audio_start':reference[0][0]-reference[1][0],
                'actual_video_minus_audio_start':actual[0][0]-actual[1][0]}
            d['validation']['passed'] &= passed
            print(f['key'],kind,'TIMING',passed,deviations,flush=True)
        except Exception as e:
            d['timing_audit_error']=str(e)
file.write_text(json.dumps(r,indent=2))
