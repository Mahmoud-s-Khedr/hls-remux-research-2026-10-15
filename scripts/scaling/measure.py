"""Measure one FFmpeg child exactly, including waited-child Linux I/O counters."""
import os,sys,time,json,resource
from pathlib import Path

def counters():
    raw=Path('/proc/self/io').read_text()
    return {k:int(v) for k,v in (line.split(':') for line in raw.splitlines())},len(raw.encode())

def host():
    cpu=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    mem={k:int(v.strip().split()[0])*1024 for k,v in (x.split(':',1) for x in Path('/proc/meminfo').read_text().splitlines())}
    return {'cpu_ticks':cpu,'available_memory_bytes':mem.get('MemAvailable'),'load_average':os.getloadavg()}

def main():
    spec=json.loads(Path(sys.argv[1]).read_text())
    log=os.open(spec['log'],os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o644)
    null=os.open('/dev/null',os.O_WRONLY)
    host_before=host()
    before,n=counters()
    start=time.perf_counter()
    pid=os.fork()
    if pid==0:
        os.dup2(null,1);os.dup2(log,2)
        os.execvp(spec['command'][0],spec['command'])
    _,status,usage=os.wait4(pid,0)
    wall=time.perf_counter()-start
    after,_=counters()
    host_after=host()
    os.close(log);os.close(null)
    io={k:after[k]-before.get(k,0) for k in after}
    # The first /proc read itself was accounted after the baseline snapshot.
    io['rchar']=max(0,io['rchar']-n)
    cpu=usage.ru_utime+usage.ru_stime
    result={'returncode':os.waitstatus_to_exitcode(status),'wall_seconds':wall,
      'started_monotonic':start,'exited_monotonic':start+wall,
      'user_cpu_seconds':usage.ru_utime,'system_cpu_seconds':usage.ru_stime,'cpu_seconds':cpu,
      'average_cpu_percent_one_core':cpu/wall*100,'average_cpu_percent_host':cpu/wall*100/(os.cpu_count() or 1),
      'peak_rss_bytes':usage.ru_maxrss*1024,'major_faults':usage.ru_majflt,'minor_faults':usage.ru_minflt,
      'voluntary_context_switches':usage.ru_nvcsw,'involuntary_context_switches':usage.ru_nivcsw,
      'filesystem_input_blocks':usage.ru_inblock,'filesystem_output_blocks':usage.ru_oublock,
      'io':io,'host_before':host_before,'host_after':host_after}
    ticks=[b-a for a,b in zip(host_before['cpu_ticks'],host_after['cpu_ticks'])]
    total=sum(ticks)
    result['host_busy_cpu_percent']=100*(total-ticks[3]-ticks[4])/total if total else None
    result['host_iowait_percent']=100*ticks[4]/total if total else None
    # Flushing is outside both FFmpeg's wall time and FFmpeg's CPU/I/O counters.
    sync_start=time.perf_counter();files=0
    media_files=[p for p in Path(spec['folder']).iterdir() if p.is_file() and p.suffix in ['.m3u8','.ts','.m4s','.mp4']]
    for p in media_files:
            fd=os.open(p,os.O_RDONLY);os.fsync(fd);os.close(fd);files+=1
    fd=os.open(spec['folder'],os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    result['post_exit_fsync_seconds']=time.perf_counter()-sync_start
    result['completion_with_fsync_seconds']=wall+result['post_exit_fsync_seconds']
    result['flushed_monotonic']=time.perf_counter()
    result['output_file_count']=files
    result['output_bytes']=sum(p.stat().st_size for p in media_files)
    Path(spec['result']).write_text(json.dumps(result,indent=2))

if __name__=='__main__':main()
