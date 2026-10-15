import benchmark as b
import json, statistics

file = b.OUT/'results.json'
results = json.loads(file.read_text())
for f in results['fixtures']:
    if f['key']=='asf':
        f['initial_identity_error'] = f.pop('identity_error',None)
        p,_ = b.run(b.BASE+['-i',str(b.OUT/'reference.mp4'),'-map','0:v:0','-map','0:a:0','-c','copy',
            '-bsf:v','h264_mp4toannexb','-f','asf',str(b.OUT/f['file'])], 'asf-adjusted-prepare.log')
        assert p.returncode==0,p.stderr.decode()
        f['prepare_adjustment']='H.264 MP4 to Annex B bitstream adaptation'
        f['probe']=b.probe(b.OUT/f['file'])
        f['identity']=b.identity(b.OUT/f['file'],'asf-adjusted-input')
        f['video_matches_reference']=f['identity']['video_hash']==results['reference']['video_hash']
    for kind,d in f['outputs'].items():
        if d['warmup_ok'] and f['key'] not in ['avi','asf']: continue
        folder = b.OUT / b.Path(d['playlist']).parent
        cmd = b.mux_command(b.OUT/f['file'],folder,kind)
        d['initial_attempt'] = {k:v for k,v in d.items() if k not in ['validation']}
        d['command'] = cmd
        d['adjustment'] = 'Generate missing video PTS' if f['key']=='avi' else ('Use corrected Annex B ASF input' if f['key']=='asf' else 'AAC ADTS to AudioSpecificConfig bitstream adaptation')
        p,_ = b.run(cmd,f['key']+'-'+kind+'-adjusted-warmup.log')
        d['warmup_ok'] = p.returncode==0
        d['warmup_warnings'] = p.stderr.decode()
        d['times_seconds'] = []
        if p.returncode==0:
            for i in range(5):
                p,t = b.run(cmd,f['key']+'-'+kind+f'-adjusted-run{i+1}.log')
                d['times_seconds'].append(t)
                assert p.returncode==0,p.stderr.decode()
            d['median_seconds'] = statistics.median(d['times_seconds'])
            d['min_seconds'] = min(d['times_seconds'])
            d['max_seconds'] = max(d['times_seconds'])
            try:
                d['validation'] = b.validate(b.OUT/f['file'],folder,kind,results['reference'],f['key']+'-'+kind+'-adjusted')
                print('ADJUSTED',f['key'],kind,d['validation']['passed'],flush=True)
            except Exception as e:
                d['validation_error'] = str(e)
                print('ADJUSTMENT VALIDATION ERROR',f['key'],kind,str(e),flush=True)
        else:
            print('ADJUSTMENT FAILED',f['key'],kind,d['warmup_warnings'],flush=True)
        file.write_text(json.dumps(results,indent=2))
(b.OUT/'adjustment-commands.json').write_text(json.dumps(b.COMMANDS,indent=2))
