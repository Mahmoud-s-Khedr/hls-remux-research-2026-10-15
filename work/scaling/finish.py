import json,time,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];work=root/'work/scaling';out=root/'outputs/hls-scaling'
def state(name):
 (out/'workflow.json').write_text(json.dumps({'phase':name,'updated_unix':time.time()},indent=2));print(name,flush=True)
state('media_validation')
while json.loads((out/'results.json').read_text()).get('status')!='media_validation_complete':time.sleep(2)
for name,args in [('packet_order_audit',[sys.executable,'-u',str(work/'order_audit.py')]),('browser_validation',['node',str(work/'browser.cjs')]),('report',[sys.executable,str(work/'report.py')])]:
 state(name)
 with (work/(name+'.log')).open('w') as log:
  p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:state(name+'_failed');raise SystemExit(p.returncode)
state('complete')
