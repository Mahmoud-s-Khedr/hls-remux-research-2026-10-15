import benchmark as b
import json, random, statistics
file=b.OUT/'results.json'
r=json.loads(file.read_text())
cases=[]
for f in r['fixtures']:
 for kind,d in f['outputs'].items():
  if not d['warmup_ok']:continue
  p,_=b.run(d['command'],f['key']+'-'+kind+'-final-warmup.log')
  assert p.returncode==0,p.stderr.decode()
  d['exploratory_times_seconds']=d['times_seconds']
  d['times_seconds']=[]
  cases.append((f,kind,d))
rng=random.Random(20261015)
for repeat in range(5):
 rng.shuffle(cases)
 for f,kind,d in cases:
  p,t=b.run(d['command'],f['key']+'-'+kind+f'-final-run{repeat+1}.log')
  assert p.returncode==0,p.stderr.decode()
  d['times_seconds'].append(t)
 print('FINAL TIMING ROUND',repeat+1,flush=True)
for f,kind,d in cases:
 d['median_seconds']=statistics.median(d['times_seconds'])
 d['min_seconds']=min(d['times_seconds'])
 d['max_seconds']=max(d['times_seconds'])
r['timing_method']='One untimed warm-up per case, five sequential timed runs in seeded shuffled order per round, after all browser/decode tests finished. perf_counter wall time includes process startup, input probing, stream copying, writing all segments and final playlist, and process exit. Warm filesystem cache; no fsync/durability timing; no concurrent benchmark jobs. Download, fixture preparation, audio encoding, and validation excluded.'
file.write_text(json.dumps(r,indent=2))
(b.OUT/'final-timing-commands.json').write_text(json.dumps(b.COMMANDS,indent=2))
