import subprocess,sys,time,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];work=root/'work/scaling';out=root/'outputs/hls-scaling'
phase=out/'workflow.json'
def status(name):
 phase.write_text(json.dumps({'phase':name,'updated_unix':time.time()},indent=2));print('PHASE',name,flush=True)
status('waiting_for_serial_benchmarks')
while True:
 try:
  if json.loads((out/'results.json').read_text()).get('status')=='timing_complete':break
 except (FileNotFoundError,json.JSONDecodeError):pass
 time.sleep(2)
for name,args in [
 ('fresh_outputs',[sys.executable,'-u',str(work/'fresh.py')]),
 ('concurrency',[sys.executable,'-u',str(work/'concurrency.py')]),
 ('media_validation',[sys.executable,'-u',str(work/'validate.py')]),
 ('packet_order_audit',[sys.executable,'-u',str(work/'order_audit.py')]),
 ('browser_validation',['node',str(work/'browser.cjs')]),
 ('report',[sys.executable,str(work/'report.py')])]:
 status(name)
 with (work/(name+'.log')).open('w') as log:
  p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:
  status(name+'_failed');raise SystemExit(p.returncode)
status('complete')
