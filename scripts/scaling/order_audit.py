"""Verify PTS belongs to the corresponding copied access unit, not just a sorted timeline."""
import json,time
import run as b

def vectors(path):
 data=b.probe(path,True);tracks={}
 for p in data.get('packets',[]):
  if 'pts_time' in p:tracks.setdefault(p['stream_index'],[]).append(float(p['pts_time']))
 return tracks

def main():
 started=time.perf_counter();r=json.loads(b.STATE.read_text());r['status']='packet_order_audit';b.save(r)
 for d in r['durations']:
  src=vectors(b.OUT/d['reference']);src_origin=min(src[1])
  for c in d['cases']:
   if not c.get('validation',{}).get('passed'):continue
   dst=vectors(b.OUT/c['playlist']);origin=min(dst[1]);checks={}
   for stream in [0,1]:
    if len(src[stream])!=len(dst.get(stream,[])):
     checks[str(stream)]={'passed':False,'reason':'Access-unit count differs'};continue
    errors=[abs((a-origin)-(e-src_origin)) for a,e in zip(dst[stream],src[stream])]
    checks[str(stream)]={'passed':max(errors)<=.002,'max_error_seconds':max(errors),
     'access_units':len(errors),'first_out_of_tolerance_indices':[i for i,x in enumerate(errors)if x>.002][:5]}
   check={'passed':all(x['passed']for x in checks.values()),'streams':checks,'tolerance_seconds':.002}
   c['validation']['ordered_access_unit_pts']=check;c['validation']['passed'] &= check['passed']
   print('ORDER',c['id'],check['passed'],flush=True)
  b.save(r)
 r['packet_order_audit_wall_seconds']=time.perf_counter()-started;r['status']='packet_order_audit_complete';b.save(r)

if __name__=='__main__':main()
