import benchmark as b
import json
file=b.OUT/'results.json'
r=json.loads(file.read_text())
f=next(f for f in r['fixtures'] if f['key']=='mp4_fragmented')
cmd=b.BASE+['-i',str(b.OUT/'reference.mp4'),'-map','0:v:0','-map','0:a:0','-c','copy',
    '-f','mp4','-movflags','+frag_keyframe+delay_moov+default_base_moof',str(b.OUT/f['file'])]
p,_=b.run(cmd,'mp4_fragmented-adjusted-prepare.log')
assert p.returncode==0,p.stderr.decode()
f['initial_probe']=f['probe']
f['prepare_adjustment']='Use delay_moov to preserve initial relative audio/video timestamps in the fragmented MP4 fixture'
f['probe']=b.probe(b.OUT/f['file'])
f['identity']=b.identity(b.OUT/f['file'],'mp4_fragmented-adjusted-input')
f['video_matches_reference']=f['identity']['video_hash']==r['reference']['video_hash']
for kind,d in f['outputs'].items():
    d['initial_attempt_before_timing_fix']={k:v for k,v in d.items() if k not in ['browser_test']}
    folder=b.OUT/b.Path(d['playlist']).parent
    d['command']=b.mux_command(b.OUT/f['file'],folder,kind)
    p,_=b.run(d['command'],'mp4_fragmented-'+kind+'-adjusted-warmup.log')
    assert p.returncode==0,p.stderr.decode()
    d['validation']=b.validate(b.OUT/f['file'],folder,kind,r['reference'],'mp4_fragmented-'+kind+'-adjusted')
    print('FRAGMENTED FIX',kind,d['validation']['passed'],flush=True)
file.write_text(json.dumps(r,indent=2))
(b.OUT/'fragmented-fix-commands.json').write_text(json.dumps(b.COMMANDS,indent=2))
