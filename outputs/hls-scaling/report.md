# H.264 to HLS: length, resource use, and production sizing

**144/168 conversion paths passed media integrity, timestamp, independent-segment decoding, and browser spot checks.** The matrix covers six lengths and 14 container/layout variants, each packaged as HLS TS and HLS fragmented MP4.

All timed jobs copy one H.264 High Level 4.1, 1920×1080, 30 fps video stream and one prepared AAC-LC audio track. Video/audio encoding, source download, validation, and remote upload are excluded from remux timings; local fsync is measured separately.

## Main results: repeated output paths

| Video length | MP4 input MB | TS warm s | TS input-evicted s | fMP4 warm s | fMP4 input-evicted s | Validated paths |
|---|---|---|---|---|---|---|
| 30 seconds | 11.92 | 0.192 | 0.425 | 0.242 | 0.431 | 24/28 |
| 1 minute | 24.16 | 0.277 | 0.740 | 0.231 | 0.334 | 24/28 |
| 2 minutes | 39.26 | 0.521 | 0.806 | 0.604 | 1.400 | 24/28 |
| 5 minutes | 101.01 | 1.336 | 3.527 | 1.231 | 2.197 | 24/28 |
| 10 minutes | 241.85 | 4.417 | 6.046 | 3.200 | 5.822 | 24/28 |
| Full: 10:34.6 | 248.93 | 3.486 | 4.456 | 3.185 | 5.453 | 24/28 |

These headline rows use standard MP4 input. Each warm value is the median of five serial runs; input-evicted is one additional observed run. All 168 container/output/length cases appear in the appendix and in the filterable HTML report. Invalid outputs remain visible but are excluded from successful-throughput conclusions.

The main matrix overwrites the same destination files on every repetition. That controls names and retained outputs, but can exercise Btrfs copy-on-write differently from a production job writing a new asset. The following control tests standard MP4 with a **fresh destination directory on every run**, using the same CPU/I/O/flush instrumentation and five warm plus one input-evicted observation per case. Its temporary output files are hashed against the retained matrix output, then removed after each group; exact identity transfers the retained output's correctness validation to that control.

## Production control: fresh output paths

| Length | Output | Overwrite warm s | Fresh warm s | Fresh input-evicted s | Fresh exit + flush s | Fresh CPU s | Fresh CPU % | Fresh peak RSS MiB | Files byte-identical |
|---|---|---|---|---|---|---|---|---|---|
| 30 seconds | TS | 0.192 | 0.230 | 0.225 | 0.705 | 0.237 | 102.5 | 72.2 | YES |
| 30 seconds | fMP4 | 0.242 | 0.229 | 0.228 | 0.579 | 0.235 | 102.9 | 76.2 | YES |
| 1 minute | TS | 0.277 | 0.243 | 0.254 | 1.085 | 0.266 | 108.6 | 76.6 | YES |
| 1 minute | fMP4 | 0.231 | 0.248 | 0.255 | 1.163 | 0.258 | 106.0 | 80.7 | YES |
| 2 minutes | TS | 0.521 | 0.286 | 0.297 | 1.538 | 0.324 | 114.2 | 77.3 | YES |
| 2 minutes | fMP4 | 0.604 | 0.282 | 0.286 | 1.868 | 0.317 | 112.8 | 79.4 | YES |
| 5 minutes | TS | 1.336 | 0.398 | 0.414 | 2.784 | 0.503 | 126.4 | 80.8 | YES |
| 5 minutes | fMP4 | 1.231 | 0.407 | 0.432 | 2.821 | 0.504 | 122.3 | 81.6 | YES |
| 10 minutes | TS | 4.417 | 0.626 | 0.810 | 5.834 | 0.853 | 136.2 | 91.1 | YES |
| 10 minutes | fMP4 | 3.200 | 0.641 | 0.829 | 7.928 | 0.827 | 130.6 | 92.1 | YES |
| Full: 10:34.6 | TS | 3.486 | 0.771 | 0.746 | 7.904 | 1.029 | 136.0 | 91.5 | YES |
| Full: 10:34.6 | fMP4 | 3.185 | 0.698 | 0.738 | 7.909 | 0.919 | 131.7 | 88.6 | YES |


Fresh and overwrite tests were performed in different phases of the same sustained-write workload; a difference cannot be assigned exclusively to copy-on-write without a randomized paired experiment. Use this control as an observed production-path comparison, not a causal filesystem claim. Fresh-target controls cover standard MP4 only; other input containers retain the repeated-path results in the full matrix. Raw observations are in `fresh-output.json`.

![Packaging versus local completion](/home/mk/Documents/Codex/2026-10-15/wha/outputs/hls-scaling/charts/completion-policy.png)

- Fresh TS outputs: full versus 30-second exit time **3.35×**, CPU work **4.34×**, peak RSS **1.27×**, and exit-plus-fsync time **11.22×**; video length grows **21.15×**.
- Fresh fMP4 outputs: full versus 30-second exit time **3.05×**, CPU work **3.91×**, peak RSS **1.16×**, and exit-plus-fsync time **13.65×**; video length grows **21.15×**.

## Scaling in the repeated-path matrix

![Scaling charts](/home/mk/Documents/Codex/2026-10-15/wha/outputs/hls-scaling/charts/scaling.png)

- TS: full/30-second duration ratio **21.15×**, remux-time ratio **18.19×**, peak-RSS ratio **1.26×**. A six-point descriptive fit is `time_seconds = -0.1898 + 0.006516 × video_seconds` (R² = 0.943).
- fMP4: full/30-second duration ratio **21.15×**, remux-time ratio **13.16×**, peak-RSS ratio **1.16×**. A six-point descriptive fit is `time_seconds = -0.0487 + 0.005150 × video_seconds` (R² = 0.988).

Fixed work such as process startup and probing contributes to total time, so a 20× increase in length need not produce a 20× increase in total time. Bytes, packet counts, segment counts, filesystem behavior, and cache state also change. The six-point line describes this one movie and hardware, not a universal service-level prediction; it may not recover the actual fixed cost, and a negative or noisy fitted intercept must not be interpreted as a physical startup cost.

## CPU and memory: repeated-output matrix

| Video length | Output | CPU seconds | CPU % of one core | CPU % of 12-thread host | Peak RSS MiB | Extra fsync s | Exit + fsync s |
|---|---|---|---|---|---|---|---|
| 30 seconds | TS | 0.197 | 104.0 | 8.7 | 72.7 | 0.211 | 0.388 |
| 30 seconds | fMP4 | 0.212 | 100.5 | 8.4 | 75.9 | 0.142 | 0.391 |
| 1 minute | TS | 0.251 | 104.7 | 8.7 | 76.3 | 0.484 | 0.761 |
| 1 minute | fMP4 | 0.246 | 104.6 | 8.7 | 80.6 | 0.378 | 0.605 |
| 2 minutes | TS | 0.302 | 52.9 | 4.4 | 77.1 | 0.719 | 1.004 |
| 2 minutes | fMP4 | 0.316 | 50.1 | 4.2 | 79.4 | 0.269 | 0.935 |
| 5 minutes | TS | 0.494 | 35.0 | 2.9 | 80.4 | 1.643 | 2.494 |
| 5 minutes | fMP4 | 0.479 | 40.0 | 3.3 | 81.4 | 0.746 | 2.079 |
| 10 minutes | TS | 0.838 | 18.1 | 1.5 | 90.8 | 1.199 | 5.706 |
| 10 minutes | fMP4 | 0.799 | 23.4 | 2.0 | 92.0 | 1.095 | 4.608 |
| Full: 10:34.6 | TS | 0.822 | 27.0 | 2.3 | 91.4 | 0.993 | 4.478 |
| Full: 10:34.6 | fMP4 | 0.758 | 26.4 | 2.2 | 88.1 | 1.319 | 5.579 |

CPU % is `(user CPU seconds + system CPU seconds) / elapsed seconds × 100`; 100% means one fully occupied logical CPU. Divide by 12 to express share of this machine's logical CPU capacity. Values above 100% are possible. Peak RSS is the maximum resident memory observed by Linux `wait4/getrusage`, taking the largest value across measured runs. RSS includes shared library mappings and excludes the operating system's file/page cache, controller process, and browser. It is therefore not a complete container memory budget.

CPU seconds, CPU utilization, I/O byte volumes, and flush times in these tables are medians of the five warm runs; they need not all come from the same individual run. Peak RSS is the maximum across five warm and one input-evicted run.

The failed ASF-to-fMP4 path is plotted separately because its RAM growth is operationally significant even though the produced output is rejected. Do not use its apparent speed as successful throughput. Resource measurements refer to FFmpeg; the separate post-exit fsync operation is timed but its controller CPU is not included in FFmpeg CPU seconds.

- TS CPU work grows **4.16×** from 30 seconds to the complete source. A descriptive byte-based fit is `CPU_seconds = 0.1918 + 0.002628 × input_MB` (R² = 0.993).
- fMP4 CPU work grows **3.57×** from 30 seconds to the complete source. A descriptive byte-based fit is `CPU_seconds = 0.2057 + 0.002362 × input_MB` (R² = 0.988).
CPU work and wall latency answer different questions. Relatively stable CPU seconds with varying elapsed/flush time is consistent with filesystem or scheduling waits; host iowait snapshots support diagnosis but do not prove exclusive causation or replace device-level telemetry.

For the complete standard-MP4 source, whole-host snapshots during the five warm runs were:

| Output | Host busy CPU % | Host iowait % | Available host RAM GiB |
|---|---|---|---|
| TS | 14.7 | 15.1 | 22.4 |
| fMP4 | 8.9 | 16.4 | 22.4 |

These host percentages cover all logical CPUs and include unrelated activity; they are not attributed solely to FFmpeg. Available host RAM includes reclaimable cache and is not a cgroup memory limit.

## Disk reads, writes, cache, and completion

| Video length | Output | Logical read MB | Logical write MB | Warm storage read MB | Input-evicted storage read MB | Storage write MB | Output files |
|---|---|---|---|---|---|---|---|
| 30 seconds | TS | 12.3 | 12.3 | 0.0 | 11.9 | 12.3 | 6 |
| 30 seconds | fMP4 | 12.3 | 11.9 | 0.0 | 11.9 | 11.9 | 7 |
| 1 minute | TS | 24.5 | 24.9 | 0.0 | 24.2 | 24.9 | 10 |
| 1 minute | fMP4 | 24.5 | 24.1 | 0.0 | 24.2 | 24.2 | 11 |
| 2 minutes | TS | 39.6 | 40.5 | 0.0 | 39.3 | 40.6 | 20 |
| 2 minutes | fMP4 | 39.6 | 39.2 | 0.0 | 39.3 | 39.3 | 21 |
| 5 minutes | TS | 101.4 | 104.3 | 0.0 | 101.0 | 104.4 | 51 |
| 5 minutes | fMP4 | 101.4 | 100.9 | 0.0 | 101.1 | 101.0 | 52 |
| 10 minutes | TS | 242.2 | 249.3 | 0.0 | 241.8 | 249.6 | 96 |
| 10 minutes | fMP4 | 242.2 | 241.5 | 0.0 | 242.0 | 241.8 | 97 |
| Full: 10:34.6 | TS | 249.3 | 256.6 | 0.0 | 249.4 | 256.9 | 100 |
| Full: 10:34.6 | fMP4 | 249.3 | 248.6 | 0.0 | 248.9 | 248.9 | 101 |

- **Logical reads/writes** are Linux `rchar/wchar` deltas attributable to FFmpeg, including probing, libraries, and log writes; they need not equal media file sizes exactly.
- **Storage reads/writes** are Linux `read_bytes/write_bytes` deltas, distinct from cached I/O. Per-run cancellation counters and filesystem block counters are retained in raw results. These are kernel-attributed bytes, not a device-level NAND-write or SSD-wear measurement.
- **Warm mode** pre-reads the input outside the timer. The actual storage-read counters show whether the timed process fetched data from storage.
- **Input-evicted mode** fsyncs the input and requests `POSIX_FADV_DONTNEED` for that specific file before the run. This is not a machine-wide cold-cache test: libraries, metadata, the controller, and device caches may remain warm. No global cache settings were changed.
- **FFmpeg exit time** includes opening/probing, stream copying, writing all segments/playlists, and exit. It does not guarantee durable storage. After exit, the harness fsyncs all output media files and their directory. Extra flush time and exit-plus-flush time are reported separately. Device/filesystem guarantees still apply.
- The harness fsyncs output files serially, then their directory. This is a tested local persistence policy, not a mandatory remuxing step. A production service using disposable local scratch files and a remote completion acknowledgement has a different completion policy and must measure that path separately.
- Fsync measurements cover the media files and their immediate containing directory. Ancestors of newly created directories are not individually fsynced by this harness, and no crash/power-loss test was performed; this is a measured flush policy, not proof of a crash-consistent end-to-end commit protocol.
- Each output uses VOD playlists and a six-second segment target, with cuts at existing keyframes. Exact six-second segments are not forced. Segment counts and file counts are recorded per case.

Linux definitions: [process I/O counters](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html), [CPU and peak RSS](https://man7.org/linux/man-pages/man2/getrusage.2.html), [fsync](https://man7.org/linux/man-pages/man2/fsync.2.html), and [cgroup memory accounting](https://docs.kernel.org/admin-guide/cgroup-v2.html).

## Compatibility and failures

| Input family | Failed paths | Observed finding |
|---|---|---|
| ASF | 12 | FFmpeg muxing failed; target_duration_valid, timestamps / audio-video alignment |
| AVI | 12 | timestamps / audio-video alignment |

For the complete source, the failure evidence is:

| Input | Output | All FFmpeg exits zero | Payload identity | Playlist seconds | Max PTS error ms | Rejection reason |
|---|---|---|---|---|---|---|
| AVI | TS | True | video True, audio True | 627.408 | 64.67 | timestamps / audio-video alignment |
| AVI | fMP4 | True | video True, audio True | 627.408 | 64.67 | timestamps / audio-video alignment |
| ASF | TS | False | not checked / mux failed | — | not comparable | FFmpeg muxing failed |
| ASF | fMP4 | True | video True, audio True | 0.000 | 67.00 | target_duration_valid, timestamps / audio-video alignment |

Exact packet counts, relative audio/video starts, decode-timestamp ordering, and the log for every attempted run are retained in `results.json` and `logs/`. A zero exit code with matching compressed media still fails acceptance when its manifest/timestamps are wrong.
The known compatibility fixes are retained: `aac_adtstoasc` for fMP4 AAC packet adaptation, `delay_moov` when preparing fragmented MP4 to preserve initial audio/video timing, and Annex B H.264 adaptation when preparing ASF. AVI is tested with `-fflags +genpts`. These operations do not re-encode video. They do not waive validation failures.

### AVI → TS and fMP4: media preserved, timing changed

The tested H.264 stream contains B-frames: decode order and presentation order differ, so correct PTS/DTS and the audio/video start offset matter. The AVI fixture and this stream-copy pipeline do not preserve the reference timing. Even with -fflags +genpts, the full-source video starts 55 ms after audio instead of the reference 88 ms, and individual video PTS differ by up to 64.667 ms (acceptance tolerance: 2 ms). All 19,036 video packets and 29,730 audio packets survive with matching compressed payloads. Decode timestamps remain increasing and presentation timestamps unique; those checks alone do not establish correct presentation timing. Both commands exit successfully, but both outputs fail timing/alignment acceptance. Generating missing timestamps cannot recover the original timing merely from packet order.

### ASF → TS: muxer rejects missing initial timestamps

FFmpeg reports unset timestamps for video stream 0, then "first pts and dts value must be set" and an error submitting a packet to the muxer. The TS path therefore fails during packaging, before it can produce an acceptable HLS asset. Preparing ASF with h264_mp4toannexb adapts H.264 packet framing; it does not reconstruct missing presentation/decode timestamps.

### ASF → fMP4: successful process exit, invalid HLS timeline

FFmpeg reports "pts has no value" for all 19,036 full-source video packets. It returns zero, but creates one segment with a playlist total of 0.000 seconds and EXT-X-TARGETDURATION:0 for the approximately 634.5-second video. Video/audio payload identity still passes, while video PTS differ by up to 67 ms and the video/audio start offset becomes 21 ms instead of 88 ms. The manifest and timing failures reject this asset. Full-source peak RSS reaches 543.7 MiB; growth with clip length is consistent with buffering on the broken timeline, but the measurements do not prove the internal allocation cause or a memory leak.

### Scope and remediation

These findings apply to the generated AVI/ASF fixtures, this B-frame H.264/AAC source, and the recorded FFmpeg build and commands. They do not establish that every AVI/ASF file or every H.264 stream in those containers fails. Timestamp repair would require a separately verified strategy that restores presentation order and audio/video alignment; re-encoding would change the stream-copy requirement. Neither repair nor re-encoding was benchmarked. Failed long-video assets were excluded from browser acceptance and the report player; matching payloads or a player starting is not sufficient proof of correctness.

Evidence: [AVI TS log](logs/full-avi-mpegts-warm-1.log), [AVI fMP4 log](logs/full-avi-fmp4-warm-1.log), [ASF TS log](logs/full-asf-mpegts-warm-1.log), [ASF fMP4 log](logs/full-asf-fmp4-warm-1.log), and the full-source validation records in [results.json](results.json). AVI logs are empty because FFmpeg reports no warning at the configured log level; the failure is detected by packet comparison.

## Concurrent production jobs

The complete 10:34 source in standard MP4 was remuxed with 1, 2, and 4 simultaneous jobs, separately for TS and fMP4. Each group has three repetitions. Inputs were pre-read; outputs were fsynced. This short, bounded local contention test measures overlapping jobs, not a long steady-state arrival queue.

| Output | Workers | Batch remux s | Mean job s | Exit jobs/s | With-flush jobs/s | Aggregate CPU % | Sampled peak RSS MiB | Batch + flush s |
|---|---|---|---|---|---|---|---|---|
| TS | 1 | 0.709 | 0.709 | 1.411 | 0.151 | 135.8 | 91.2 | 6.621 |
| TS | 2 | 0.938 | 0.927 | 2.131 | 0.138 | 259.8 | 178.1 | 14.450 |
| TS | 4 | 1.271 | 1.163 | 3.148 | 0.146 | 446.0 | 341.0 | 27.471 |
| fMP4 | 1 | 0.731 | 0.731 | 1.368 | 0.128 | 130.3 | 88.6 | 7.784 |
| fMP4 | 2 | 0.866 | 0.853 | 2.309 | 0.144 | 255.5 | 176.7 | 13.909 |
| fMP4 | 4 | 1.405 | 1.387 | 2.848 | 0.229 | 417.8 | 354.4 | 17.450 |

- TS: four workers changed throughput from **1.411 to 3.148 jobs/s** (+123.2%), while average per-job latency changed from **0.709 to 1.163 s**. Sampled aggregate peak RSS reached **341.0 MiB**.
  After including fsync, the corresponding throughput was **0.151 versus 0.146 completed jobs/s**. Choose the completion policy before using a throughput figure for capacity planning.
- fMP4: four workers changed throughput from **1.368 to 2.848 jobs/s** (+108.2%), while average per-job latency changed from **0.731 to 1.387 s**. Sampled aggregate peak RSS reached **354.4 MiB**.
  After including fsync, the corresponding throughput was **0.128 versus 0.229 completed jobs/s**. Choose the completion policy before using a throughput figure for capacity planning.
![Concurrency charts](/home/mk/Documents/Codex/2026-10-15/wha/outputs/hls-scaling/charts/concurrency.png)
Aggregate RSS is sampled every 10 ms and sums per-process RSS, including shared pages counted for each process; short peaks may be missed. Individual exact peaks and full sample traces are also retained. Batch remux time spans the earliest FFmpeg start to the latest FFmpeg exit. Flushes from an earlier-finishing job can overlap another running job, as in an actual shared-filesystem workload.

## Production interpretation

1. Size CPU from **CPU seconds per accepted job** and desired jobs/second, then reserve headroom and measure under the actual CPU limit. A sub-second local job is not necessarily cheap at a high arrival rate. Use the concurrency measurements to assess contention rather than multiplying a single-worker rate without evidence.
2. Budget memory for FFmpeg RSS **plus** application overhead and page cache. As a provisional starting point for this exact media profile, observed valid-job RSS plus 50% gives a process-memory allowance; it is not a tested cgroup/container limit. Measure `memory.current`, `memory.stat`, and memory-pressure/OOM events in the target runtime before setting limits.
3. Budget input reads and output writes separately. Producing both HLS styles in two independent jobs reads/processes the input twice and writes both packages. A multi-output packaging optimization was not benchmarked here. These are seekable local files; fast-start versus end-index MP4 behavior over HTTP/range requests is not measured.
4. Validate input timestamps early, retain source codec/profile restrictions, and reject or explicitly repair invalid inputs. The ASF/AVI cases show why exit code zero or a browser reaching the end is insufficient. Apply explicit time/memory limits and bounded worker queues; limits themselves were not tested in this run.
5. Network/object-storage latency can dominate this local packaging time. The following are mathematical upload floors for the complete source's measured output sizes, excluding request latency, TLS, retries, per-segment overhead, and storage persistence. They are not measured cloud timings:

| Package | Output MB | At 100 Mb/s: minimum upload s | At 1 Gb/s: minimum upload s |
|---|---|---|---|
| TS output | 256.6 | 20.5 | 2.1 |
| fMP4 output | 248.6 | 19.9 | 2.0 |
| Both outputs | 505.2 | 40.4 | 4.0 |


Input download may add work, and streaming transfers can overlap. Use real network conditions and object-store APIs for the next load test. Local SSD, disk occupancy, filesystem writeback, and CPU power policy all influence these numbers.

For a steady workload, a first planning calculation is `CPU cores ≈ arrival_jobs_per_second × mean_CPU_seconds_per_job / chosen_utilization_fraction`. Likewise, `output_MB_per_second ≈ arrival_jobs_per_second × output_MB_per_job`. Use the mix of accepted input types and the chosen completion policy, not the fastest row. These are demand calculations, not measured service capacities; memory/page cache, metadata I/O, queues, and network overhead still constrain the service.

The measured pipeline starts with AAC audio already available. If production uploads contain MP3, AC-3, or another audio codec requiring conversion, add that preparation cost; the current CPU/time figures cover stream copying, not audio encoding. Input/output validation, upload, orchestration, and queue wait also need their own production budgets. The final media-validation invocation took 29.6 minutes using byte-identical-segment caching across cases; this excludes the interrupted diagnostic pass and is not a per-job or uncached production validation benchmark.

## Assumptions

- One downloaded movie: Big Buck Bunny, Sunflower version. Source MP4 is 276,134,947 bytes, 1920×1080 progressive 30 fps, H.264 High Level 4.1, 8-bit 4:2:0, with B-frames. Original tracks are MP3 stereo and AC-3 5.1.
- Excerpts begin at the beginning of the same source. Requested lengths are 30, 60, 120, 300, and 600 seconds, plus the complete source. Full video stream duration is 634.533 seconds; source container duration is 634.600 seconds. Actual reference/playlist durations and packet counts are retained.
- Audio is prepared once per reference as AAC-LC, stereo 48 kHz at a 128 kb/s target. A TS intermediate normalizes source priming/edit-list behavior. Preparation is excluded from remux timings; every timed operation copies both encoded streams. No video re-encoding occurs.
- Fourteen entries include distinct layouts of the MP4 family, not fourteen unrelated container specifications. WebM/Ogg are outside this H.264 test selection.
- Each HLS package has one 1080p video rendition and one AAC track. TS and fMP4 are two packaging styles of that same quality, not an adaptive-bitrate ladder. Creating additional resolutions/bitrates would require separate encoding work that is not measured here.
- This reruns the 30-second baseline using the new resource/flush/cache methodology. Earlier uninstrumented 30-second values are preserved in `../hls-benchmark/` and are not mixed into these scaling fits.

## Data Quality/Confidence

- **1008 measured main-matrix serial runs**: five warm repetitions plus one input-evicted run for each of 168 cases, in seeded shuffled order per warm round; 168 additional warm-ups. There are also 72 measured fresh-target control runs and 42 concurrency jobs. Timing/resource measurement runs before decoding and browser workloads. Each timed child has its own logs and measurement JSON.
- Measured FFmpeg runs together consumed 538.3 CPU-seconds and were charged approximately 102.2 GiB of storage writes; preparation, warm-ups, fsync-controller work, concurrency tests, and validation are additional. This is a sustained-write experiment, not a single isolated short copy. SSD controller/SLC-cache behavior was not measured, so changes cannot be attributed to that mechanism specifically.
- CPU user/system time and peak RSS are exact child process accounting; I/O counters are read after the wrapper waits for the child and subtract its own baseline. Filesystem-block counts cross-check byte counters. Fsync is measured separately. Wall time starts immediately before FFmpeg fork/exec, excluding Python measurement startup, cache preparation, and JSON output.
- Every accepted output has an entire-stream H.264 VCL payload/parameter-set identity match and an entire AAC ADTS payload match to its duration reference. Video/audio packet counts, presentation timing within 2 ms, increasing decode timestamps, codecs/resolution, manifests, and file existence are checked over the complete asset. A separate order-sensitive audit compares PTS for corresponding access units in decode/demux order, so a matching sorted timestamp set cannot conceal timestamps assigned to the wrong frames; that audit took 1.6 minutes.
- Every accepted segment decodes independently with strict FFmpeg error handling and starts with a keyframe. Byte-identical init+segment assets reuse an already completed decode result, keyed by SHA-256. **1337 unique segment assets** were decoded. All duration references and the complete standard-MP4 TS/fMP4 playlists are also decoded end to end.
- A diagnostic pass found coarse timestamp rounding in the temporary null-output validation sink for some independently opened fMP4 fragments. The sink was changed to a 90 kHz video time base and affected checks were rerun; no input/HLS media or measured timings changed. The original diagnostic results are retained in raw results where applicable. Media packet timestamps are audited separately from the validation sink.
- Browser tests use Chromium 156.0.8078.4 and hls.js 1.6.13, at normal speed: startup, middle seek, near-end seek, and end completion. They do not watch every full long asset in real time. Full packet/segment validation covers the intervening data. Playback is muted; no human listening or subjective visual assessment is claimed. Render counters include seeking and local test load.
- Five warm observations support a median/range comparison, not a production p95/p99. Input-evicted has one observation per case; concurrency has three repetitions. One film and one laptop limit generalization. The full six-point regression is descriptive, with highly correlated length and byte count.
- CPU governor: `powersave`. The desktop was not isolated from unrelated activity; host CPU/iowait/load/available-memory snapshots are retained. The dataset itself changes disk occupancy and sustained-write conditions. Free disk at report time: 15.5 GiB. Compare round drift below before treating small differences between containers as meaningful.

| Warm round | Median valid-job s | Mean valid-job s | Median extra fsync s |
|---|---|---|---|
| 1 | 0.652 | 1.082 | 0.375 |
| 2 | 0.835 | 1.456 | 0.482 |
| 3 | 0.944 | 1.678 | 0.671 |
| 4 | 1.171 | 1.866 | 0.740 |
| 5 | 1.208 | 2.225 | 0.738 |


## What this does NOT prove

It does not establish an SLA or supported peak concurrency for cloud servers; cold object storage performance; network/CDN behavior; container/cgroup limits; long steady-state saturation; power-loss recovery; Safari/iOS/native HLS behavior; other resolutions, frame rates, bitrates, codecs, damaged files, encryption/DRM, multiple languages/subtitles, or live/low-latency HLS. It also does not show that all AVI/ASF inputs fail, only that these particular fixtures fail this tested pipeline.

## Environment and reproducibility

- CPU: AMD Ryzen 5 PRO 5650U, 6 physical cores / 12 logical CPUs; affinity permits 12 logical CPUs.
- Memory: 30.7 GiB physical RAM; initial available 22.3 GiB.
- Storage: NVMe `NV33525GBY3G1-S`, Btrfs filesystem. The test stays on the same local filesystem for inputs and outputs.
- Platform: `Linux-7.2.10-200.fc44.x86_64-x86_64-with-glibc2.43`.
- `ffmpeg version 8.1.3 Copyright (c) 2000-2026 the FFmpeg developers`.
- The complete FFmpeg build configuration is saved in `ffmpeg-build.txt`; this desktop build loads many optional libraries, which can influence startup time and baseline RSS.
- Measured: 15 October 2026, Africa/Cairo. Dataset before report assets: approximately 26.4 GiB.
- `results.json`, `analysis.json`, `measurements/`, `logs/`, `segment-validation-cache.json`, `browser-validation.json`, and `concurrency.json` preserve the evidence. `scripts/` preserves the harness. Script paths refer to this workspace and its installed tools; adapt them for another machine.
- HLS assets are in `durations/<length>/hls/<container>/<mpegts|fmp4>/`. Input fixtures and references are retained alongside them. Only validated outputs are offered in the HTML player.

During this session the [local HTML viewer](http://127.0.0.1:8765/outputs/hls-scaling/report.html) is served by the existing localhost server. To serve the output folder independently, run `python3 -m http.server 8766 --bind 127.0.0.1 --directory "/home/mk/Documents/Codex/2026-10-15/wha/outputs/hls-scaling"` and open [the standalone viewer](http://127.0.0.1:8766/report.html). The player requires HTTP rather than opening the HTML with `file://`.

Source: https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip . Big Buck Bunny © 2008 Blender Foundation / www.bigbuckbunny.org; Sunflower version credits Blender Foundation 2008 and Janus Bager Kristensen 2013. CC BY 3.0. Source SHA-256: `ae51005850b0ff757fe60c3dd7a12d754d3cd2397d87d939b55235e457f97658`.

## Complete results matrix

Times and resource costs of failed attempts are retained for diagnosis; FAIL rows are not usable-output timings.

| Length | Input container | Output | Warm median s | Warm min–max s | Input-evicted s | CPU s | CPU % | Peak RSS MiB | Evicted disk read MB | Disk write MB | Result | Finding |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 30 seconds | MP4 (standard) | TS | 0.192 | 0.177–0.211 | 0.425 | 0.197 | 104.0 | 72.7 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | MP4 (standard) | fMP4 | 0.242 | 0.182–0.429 | 0.431 | 0.212 | 100.5 | 75.9 | 11.9 | 11.9 | PASS | PASS |
| 30 seconds | MP4 (fast-start) | TS | 0.194 | 0.185–0.206 | 0.456 | 0.200 | 103.9 | 72.6 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | MP4 (fast-start) | fMP4 | 0.199 | 0.189–0.316 | 0.282 | 0.207 | 102.9 | 76.1 | 11.9 | 11.9 | PASS | PASS |
| 30 seconds | MP4 (fragmented) | TS | 0.199 | 0.188–0.209 | 0.267 | 0.210 | 105.6 | 72.5 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | MP4 (fragmented) | fMP4 | 0.221 | 0.200–0.232 | 0.277 | 0.231 | 104.1 | 76.0 | 11.9 | 11.9 | PASS | PASS |
| 30 seconds | QuickTime / MOV | TS | 0.200 | 0.174–0.206 | 0.461 | 0.205 | 103.9 | 72.4 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | QuickTime / MOV | fMP4 | 0.203 | 0.181–0.292 | 0.310 | 0.210 | 103.3 | 76.3 | 11.9 | 11.9 | PASS | PASS |
| 30 seconds | Matroska / MKV | TS | 0.194 | 0.183–0.281 | 0.287 | 0.201 | 103.6 | 72.2 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | Matroska / MKV | fMP4 | 0.219 | 0.192–0.364 | 0.280 | 0.217 | 102.5 | 76.0 | 11.9 | 11.9 | PASS | PASS |
| 30 seconds | MPEG-TS | TS | 0.268 | 0.197–0.292 | 0.262 | 0.210 | 102.9 | 72.9 | 12.4 | 12.3 | PASS | PASS |
| 30 seconds | MPEG-TS | fMP4 | 0.212 | 0.199–0.261 | 0.253 | 0.223 | 104.6 | 79.5 | 12.4 | 11.9 | PASS | PASS |
| 30 seconds | MPEG-TS (M2TS mode) | TS | 0.226 | 0.175–0.315 | 0.305 | 0.228 | 104.6 | 73.1 | 12.7 | 12.3 | PASS | PASS |
| 30 seconds | MPEG-TS (M2TS mode) | fMP4 | 0.218 | 0.194–0.248 | 0.271 | 0.220 | 104.2 | 79.2 | 12.7 | 11.9 | PASS | PASS |
| 30 seconds | AVI | TS | 0.191 | 0.181–0.222 | 0.271 | 0.199 | 106.0 | 72.6 | 12.4 | 12.3 | FAIL | timestamps / audio-video alignment |
| 30 seconds | AVI | fMP4 | 0.231 | 0.197–0.297 | 0.260 | 0.218 | 104.7 | 76.0 | 12.4 | 11.9 | FAIL | timestamps / audio-video alignment |
| 30 seconds | Flash Video / FLV | TS | 0.196 | 0.174–0.286 | 0.255 | 0.204 | 104.1 | 72.4 | 12.7 | 12.3 | PASS | PASS |
| 30 seconds | Flash Video / FLV | fMP4 | 0.202 | 0.188–0.337 | 0.306 | 0.207 | 102.1 | 77.8 | 11.9 | 11.9 | PASS | PASS |
| 30 seconds | Adobe F4V | TS | 0.203 | 0.190–0.272 | 0.536 | 0.203 | 101.5 | 72.2 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | Adobe F4V | fMP4 | 0.210 | 0.194–0.669 | 0.282 | 0.215 | 101.8 | 76.1 | 11.9 | 12.0 | PASS | PASS |
| 30 seconds | 3GPP / 3GP | TS | 0.221 | 0.194–0.297 | 0.418 | 0.202 | 99.0 | 72.1 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | 3GPP / 3GP | fMP4 | 0.214 | 0.187–0.294 | 0.278 | 0.209 | 102.6 | 76.0 | 11.9 | 12.0 | PASS | PASS |
| 30 seconds | 3GPP2 / 3G2 | TS | 0.219 | 0.185–0.356 | 0.244 | 0.201 | 103.0 | 72.3 | 11.9 | 12.3 | PASS | PASS |
| 30 seconds | 3GPP2 / 3G2 | fMP4 | 0.199 | 0.184–0.302 | 0.251 | 0.205 | 102.4 | 76.2 | 11.9 | 12.0 | PASS | PASS |
| 30 seconds | NUT | TS | 0.214 | 0.199–0.338 | 0.266 | 0.212 | 102.1 | 71.4 | 12.3 | 12.3 | PASS | PASS |
| 30 seconds | NUT | fMP4 | 0.205 | 0.184–0.251 | 0.268 | 0.200 | 102.6 | 74.7 | 11.9 | 11.9 | PASS | PASS |
| 30 seconds | ASF | TS | 0.161 | 0.148–0.209 | 0.220 | 0.159 | 98.7 | 66.7 | 0.7 | 0.0 | FAIL | FFmpeg muxing failed |
| 30 seconds | ASF | fMP4 | 0.230 | 0.205–0.407 | 0.436 | 0.228 | 103.6 | 88.7 | 12.1 | 11.9 | FAIL | target_duration_valid, timestamps / audio-video alignment |
| 1 minute | MP4 (standard) | TS | 0.277 | 0.218–0.994 | 0.740 | 0.251 | 104.7 | 76.3 | 24.2 | 24.9 | PASS | PASS |
| 1 minute | MP4 (standard) | fMP4 | 0.231 | 0.227–0.447 | 0.334 | 0.246 | 104.6 | 80.6 | 24.2 | 24.2 | PASS | PASS |
| 1 minute | MP4 (fast-start) | TS | 0.240 | 0.200–0.352 | 0.352 | 0.252 | 106.7 | 76.1 | 24.2 | 24.9 | PASS | PASS |
| 1 minute | MP4 (fast-start) | fMP4 | 0.241 | 0.196–0.546 | 0.311 | 0.249 | 105.2 | 80.3 | 24.2 | 24.2 | PASS | PASS |
| 1 minute | MP4 (fragmented) | TS | 0.379 | 0.241–0.472 | 0.660 | 0.265 | 73.6 | 76.8 | 24.2 | 24.9 | PASS | PASS |
| 1 minute | MP4 (fragmented) | fMP4 | 0.297 | 0.254–0.427 | 0.322 | 0.257 | 96.9 | 80.7 | 24.1 | 24.2 | PASS | PASS |
| 1 minute | QuickTime / MOV | TS | 0.232 | 0.217–0.266 | 0.426 | 0.251 | 107.4 | 76.5 | 24.2 | 24.9 | PASS | PASS |
| 1 minute | QuickTime / MOV | fMP4 | 0.269 | 0.226–0.460 | 0.302 | 0.245 | 106.0 | 80.7 | 24.2 | 24.2 | PASS | PASS |
| 1 minute | Matroska / MKV | TS | 0.221 | 0.216–0.271 | 0.288 | 0.240 | 107.9 | 77.0 | 24.1 | 25.0 | PASS | PASS |
| 1 minute | Matroska / MKV | fMP4 | 0.258 | 0.232–0.482 | 0.388 | 0.263 | 106.1 | 80.0 | 24.1 | 24.2 | PASS | PASS |
| 1 minute | MPEG-TS | TS | 0.305 | 0.230–0.594 | 0.362 | 0.292 | 102.7 | 77.0 | 25.5 | 24.9 | PASS | PASS |
| 1 minute | MPEG-TS | fMP4 | 0.264 | 0.258–0.488 | 0.316 | 0.282 | 107.7 | 81.2 | 25.1 | 24.2 | PASS | PASS |
| 1 minute | MPEG-TS (M2TS mode) | TS | 0.241 | 0.233–0.516 | 0.290 | 0.255 | 105.5 | 77.1 | 25.7 | 24.9 | PASS | PASS |
| 1 minute | MPEG-TS (M2TS mode) | fMP4 | 0.280 | 0.236–0.327 | 0.335 | 0.298 | 105.8 | 81.4 | 25.7 | 24.2 | PASS | PASS |
| 1 minute | AVI | TS | 0.345 | 0.232–0.631 | 0.281 | 0.277 | 107.7 | 76.1 | 25.1 | 25.0 | FAIL | timestamps / audio-video alignment |
| 1 minute | AVI | fMP4 | 0.299 | 0.236–0.484 | 0.332 | 0.295 | 107.1 | 80.6 | 25.0 | 24.2 | FAIL | timestamps / audio-video alignment |
| 1 minute | Flash Video / FLV | TS | 0.230 | 0.211–0.281 | 0.448 | 0.247 | 107.2 | 76.3 | 24.2 | 24.9 | PASS | PASS |
| 1 minute | Flash Video / FLV | fMP4 | 0.250 | 0.222–0.288 | 0.285 | 0.258 | 105.4 | 81.5 | 24.2 | 24.2 | PASS | PASS |
| 1 minute | Adobe F4V | TS | 0.278 | 0.223–0.509 | 0.292 | 0.240 | 86.9 | 76.1 | 24.2 | 24.9 | PASS | PASS |
| 1 minute | Adobe F4V | fMP4 | 0.293 | 0.216–0.494 | 0.274 | 0.239 | 100.0 | 80.5 | 24.2 | 24.2 | PASS | PASS |
| 1 minute | 3GPP / 3GP | TS | 0.464 | 0.220–0.620 | 0.310 | 0.242 | 54.8 | 76.3 | 24.2 | 25.0 | PASS | PASS |
| 1 minute | 3GPP / 3GP | fMP4 | 0.307 | 0.225–0.470 | 0.324 | 0.239 | 90.9 | 80.4 | 24.2 | 24.2 | PASS | PASS |
| 1 minute | 3GPP2 / 3G2 | TS | 0.226 | 0.195–0.537 | 0.289 | 0.233 | 107.1 | 76.4 | 24.2 | 24.9 | PASS | PASS |
| 1 minute | 3GPP2 / 3G2 | fMP4 | 0.267 | 0.223–0.657 | 0.351 | 0.256 | 105.1 | 80.4 | 24.2 | 24.2 | PASS | PASS |
| 1 minute | NUT | TS | 0.370 | 0.226–0.831 | 0.660 | 0.250 | 67.6 | 75.9 | 24.2 | 25.0 | PASS | PASS |
| 1 minute | NUT | fMP4 | 0.247 | 0.221–0.497 | 0.312 | 0.251 | 105.8 | 79.7 | 24.1 | 24.2 | PASS | PASS |
| 1 minute | ASF | TS | 0.161 | 0.151–0.184 | 0.217 | 0.159 | 98.5 | 66.9 | 0.7 | 0.0 | FAIL | FFmpeg muxing failed |
| 1 minute | ASF | fMP4 | 0.288 | 0.228–0.336 | 0.324 | 0.274 | 107.8 | 111.4 | 24.4 | 24.2 | FAIL | target_duration_valid, timestamps / audio-video alignment |
| 2 minutes | MP4 (standard) | TS | 0.521 | 0.285–0.804 | 0.806 | 0.302 | 52.9 | 77.1 | 39.3 | 40.6 | PASS | PASS |
| 2 minutes | MP4 (standard) | fMP4 | 0.604 | 0.280–0.712 | 1.400 | 0.316 | 50.1 | 79.4 | 39.3 | 39.3 | PASS | PASS |
| 2 minutes | MP4 (fast-start) | TS | 0.439 | 0.260–0.698 | 1.053 | 0.296 | 71.4 | 77.1 | 39.2 | 40.6 | PASS | PASS |
| 2 minutes | MP4 (fast-start) | fMP4 | 0.789 | 0.557–1.000 | 0.944 | 0.310 | 42.0 | 79.9 | 39.7 | 39.3 | PASS | PASS |
| 2 minutes | MP4 (fragmented) | TS | 0.615 | 0.494–1.256 | 0.756 | 0.307 | 48.9 | 77.6 | 39.2 | 40.6 | PASS | PASS |
| 2 minutes | MP4 (fragmented) | fMP4 | 0.739 | 0.305–1.110 | 1.138 | 0.335 | 44.0 | 79.6 | 39.3 | 39.3 | PASS | PASS |
| 2 minutes | QuickTime / MOV | TS | 0.499 | 0.262–0.854 | 0.934 | 0.325 | 60.1 | 76.9 | 39.3 | 40.6 | PASS | PASS |
| 2 minutes | QuickTime / MOV | fMP4 | 0.542 | 0.236–0.800 | 0.901 | 0.290 | 53.4 | 79.2 | 39.3 | 39.2 | PASS | PASS |
| 2 minutes | Matroska / MKV | TS | 0.642 | 0.241–0.723 | 0.816 | 0.298 | 56.4 | 77.0 | 39.2 | 40.6 | PASS | PASS |
| 2 minutes | Matroska / MKV | fMP4 | 0.543 | 0.425–0.894 | 0.879 | 0.295 | 50.6 | 79.5 | 39.2 | 39.3 | PASS | PASS |
| 2 minutes | MPEG-TS | TS | 0.433 | 0.262–0.742 | 1.242 | 0.320 | 77.1 | 78.4 | 42.6 | 40.6 | PASS | PASS |
| 2 minutes | MPEG-TS | fMP4 | 0.425 | 0.263–0.829 | 0.844 | 0.346 | 86.2 | 80.0 | 41.0 | 39.3 | PASS | PASS |
| 2 minutes | MPEG-TS (M2TS mode) | TS | 0.599 | 0.449–0.978 | 1.391 | 0.326 | 53.0 | 78.2 | 41.9 | 40.6 | PASS | PASS |
| 2 minutes | MPEG-TS (M2TS mode) | fMP4 | 0.361 | 0.291–0.947 | 0.879 | 0.332 | 110.5 | 80.1 | 41.9 | 39.3 | PASS | PASS |
| 2 minutes | AVI | TS | 0.494 | 0.297–0.799 | 0.968 | 0.358 | 68.9 | 76.9 | 41.0 | 40.6 | FAIL | timestamps / audio-video alignment |
| 2 minutes | AVI | fMP4 | 0.779 | 0.299–0.940 | 0.762 | 0.355 | 49.5 | 79.2 | 41.0 | 39.3 | FAIL | timestamps / audio-video alignment |
| 2 minutes | Flash Video / FLV | TS | 0.495 | 0.272–1.029 | 0.882 | 0.315 | 65.8 | 76.8 | 39.3 | 40.6 | PASS | PASS |
| 2 minutes | Flash Video / FLV | fMP4 | 0.588 | 0.475–1.043 | 0.839 | 0.329 | 49.7 | 80.8 | 39.3 | 39.3 | PASS | PASS |
| 2 minutes | Adobe F4V | TS | 0.340 | 0.265–0.531 | 0.887 | 0.300 | 84.6 | 77.3 | 39.3 | 40.6 | PASS | PASS |
| 2 minutes | Adobe F4V | fMP4 | 0.765 | 0.429–0.897 | 1.223 | 0.320 | 54.6 | 79.6 | 39.3 | 39.2 | PASS | PASS |
| 2 minutes | 3GPP / 3GP | TS | 0.491 | 0.240–1.445 | 1.036 | 0.293 | 59.3 | 77.2 | 39.3 | 40.6 | PASS | PASS |
| 2 minutes | 3GPP / 3GP | fMP4 | 0.526 | 0.244–0.806 | 1.488 | 0.298 | 58.3 | 79.4 | 39.3 | 39.3 | PASS | PASS |
| 2 minutes | 3GPP2 / 3G2 | TS | 0.705 | 0.484–1.943 | 1.028 | 0.317 | 51.9 | 77.2 | 47.3 | 40.6 | PASS | PASS |
| 2 minutes | 3GPP2 / 3G2 | fMP4 | 0.435 | 0.317–0.860 | 0.629 | 0.308 | 70.8 | 79.5 | 39.3 | 39.3 | PASS | PASS |
| 2 minutes | NUT | TS | 0.560 | 0.256–0.765 | 0.914 | 0.290 | 51.9 | 76.3 | 39.2 | 40.6 | PASS | PASS |
| 2 minutes | NUT | fMP4 | 0.489 | 0.252–0.877 | 0.792 | 0.285 | 58.3 | 78.3 | 39.2 | 39.2 | PASS | PASS |
| 2 minutes | ASF | TS | 0.167 | 0.153–0.209 | 0.205 | 0.165 | 98.8 | 66.9 | 0.7 | 0.0 | FAIL | FFmpeg muxing failed |
| 2 minutes | ASF | fMP4 | 0.352 | 0.273–0.737 | 0.437 | 0.360 | 107.4 | 141.8 | 39.7 | 39.2 | FAIL | target_duration_valid, timestamps / audio-video alignment |
| 5 minutes | MP4 (standard) | TS | 1.336 | 0.852–3.104 | 3.527 | 0.494 | 35.0 | 80.4 | 101.0 | 104.4 | PASS | PASS |
| 5 minutes | MP4 (standard) | fMP4 | 1.231 | 0.894–2.534 | 2.197 | 0.479 | 40.0 | 81.4 | 101.1 | 101.0 | PASS | PASS |
| 5 minutes | MP4 (fast-start) | TS | 1.623 | 0.869–2.931 | 2.652 | 0.461 | 27.5 | 79.9 | 100.8 | 104.4 | PASS | PASS |
| 5 minutes | MP4 (fast-start) | fMP4 | 1.498 | 0.671–1.691 | 2.434 | 0.467 | 37.3 | 81.5 | 102.0 | 101.0 | PASS | PASS |
| 5 minutes | MP4 (fragmented) | TS | 1.258 | 0.712–2.644 | 3.655 | 0.546 | 38.6 | 81.6 | 100.9 | 104.5 | PASS | PASS |
| 5 minutes | MP4 (fragmented) | fMP4 | 1.539 | 0.924–2.178 | 2.378 | 0.558 | 32.3 | 81.8 | 100.9 | 101.0 | PASS | PASS |
| 5 minutes | QuickTime / MOV | TS | 1.458 | 0.869–2.269 | 2.456 | 0.491 | 35.2 | 79.8 | 101.0 | 104.4 | PASS | PASS |
| 5 minutes | QuickTime / MOV | fMP4 | 1.498 | 1.118–1.719 | 4.060 | 0.470 | 32.5 | 81.7 | 101.0 | 101.0 | PASS | PASS |
| 5 minutes | Matroska / MKV | TS | 1.242 | 0.813–3.694 | 2.069 | 0.494 | 39.8 | 82.0 | 100.9 | 104.4 | PASS | PASS |
| 5 minutes | Matroska / MKV | fMP4 | 1.821 | 0.765–2.908 | 1.830 | 0.485 | 25.6 | 81.7 | 101.0 | 101.1 | PASS | PASS |
| 5 minutes | MPEG-TS | TS | 1.647 | 0.914–2.296 | 2.273 | 0.528 | 30.1 | 81.3 | 105.5 | 104.4 | PASS | PASS |
| 5 minutes | MPEG-TS | fMP4 | 1.645 | 1.115–2.574 | 2.408 | 0.563 | 34.2 | 82.9 | 105.6 | 101.0 | PASS | PASS |
| 5 minutes | MPEG-TS (M2TS mode) | TS | 0.983 | 0.538–2.182 | 2.946 | 0.499 | 49.1 | 80.8 | 107.8 | 104.4 | PASS | PASS |
| 5 minutes | MPEG-TS (M2TS mode) | fMP4 | 1.795 | 0.896–1.962 | 2.309 | 0.531 | 33.6 | 82.8 | 107.7 | 101.0 | PASS | PASS |
| 5 minutes | AVI | TS | 1.430 | 0.914–2.646 | 2.323 | 0.638 | 43.3 | 79.6 | 105.4 | 104.4 | FAIL | timestamps / audio-video alignment |
| 5 minutes | AVI | fMP4 | 1.316 | 0.876–1.676 | 3.854 | 0.615 | 48.4 | 81.3 | 105.4 | 101.1 | FAIL | timestamps / audio-video alignment |
| 5 minutes | Flash Video / FLV | TS | 1.340 | 1.160–2.398 | 2.756 | 0.460 | 32.0 | 80.4 | 101.1 | 104.4 | PASS | PASS |
| 5 minutes | Flash Video / FLV | fMP4 | 2.171 | 1.050–3.203 | 2.120 | 0.495 | 22.8 | 82.4 | 101.1 | 101.1 | PASS | PASS |
| 5 minutes | Adobe F4V | TS | 1.735 | 0.996–2.034 | 2.787 | 0.501 | 25.7 | 80.0 | 120.8 | 104.4 | PASS | PASS |
| 5 minutes | Adobe F4V | fMP4 | 1.393 | 0.811–3.268 | 2.203 | 0.449 | 29.5 | 82.0 | 101.1 | 101.0 | PASS | PASS |
| 5 minutes | 3GPP / 3GP | TS | 1.089 | 0.960–1.871 | 2.351 | 0.468 | 41.8 | 80.3 | 101.1 | 104.4 | PASS | PASS |
| 5 minutes | 3GPP / 3GP | fMP4 | 1.329 | 1.072–2.440 | 2.263 | 0.460 | 32.5 | 81.6 | 101.1 | 101.0 | PASS | PASS |
| 5 minutes | 3GPP2 / 3G2 | TS | 1.356 | 0.557–2.038 | 2.680 | 0.466 | 34.2 | 80.2 | 101.0 | 104.4 | PASS | PASS |
| 5 minutes | 3GPP2 / 3G2 | fMP4 | 0.922 | 0.771–1.382 | 2.594 | 0.464 | 49.7 | 81.7 | 101.1 | 101.0 | PASS | PASS |
| 5 minutes | NUT | TS | 1.302 | 0.838–2.928 | 2.611 | 0.464 | 34.1 | 80.7 | 101.0 | 104.4 | PASS | PASS |
| 5 minutes | NUT | fMP4 | 1.502 | 0.803–1.611 | 1.988 | 0.472 | 29.9 | 80.6 | 100.9 | 101.0 | PASS | PASS |
| 5 minutes | ASF | TS | 0.161 | 0.153–0.210 | 0.230 | 0.158 | 98.5 | 67.0 | 0.7 | 0.0 | FAIL | FFmpeg muxing failed |
| 5 minutes | ASF | fMP4 | 0.556 | 0.505–0.774 | 0.835 | 0.628 | 112.9 | 259.3 | 102.3 | 101.0 | FAIL | target_duration_valid, timestamps / audio-video alignment |
| 10 minutes | MP4 (standard) | TS | 4.417 | 2.739–5.043 | 6.046 | 0.838 | 18.1 | 90.8 | 241.8 | 249.6 | PASS | PASS |
| 10 minutes | MP4 (standard) | fMP4 | 3.200 | 1.538–7.096 | 5.822 | 0.799 | 23.4 | 92.0 | 242.0 | 241.8 | PASS | PASS |
| 10 minutes | MP4 (fast-start) | TS | 3.629 | 2.895–5.217 | 7.015 | 0.798 | 24.0 | 91.2 | 241.7 | 249.5 | PASS | PASS |
| 10 minutes | MP4 (fast-start) | fMP4 | 2.800 | 1.728–4.362 | 4.798 | 0.776 | 27.7 | 91.8 | 241.5 | 241.8 | PASS | PASS |
| 10 minutes | MP4 (fragmented) | TS | 3.213 | 1.997–5.002 | 8.255 | 0.988 | 29.6 | 90.9 | 241.5 | 249.6 | PASS | PASS |
| 10 minutes | MP4 (fragmented) | fMP4 | 2.708 | 1.706–4.531 | 5.449 | 0.962 | 31.8 | 88.8 | 241.8 | 241.8 | PASS | PASS |
| 10 minutes | QuickTime / MOV | TS | 2.882 | 2.106–4.183 | 4.365 | 0.797 | 26.3 | 91.1 | 242.0 | 249.5 | PASS | PASS |
| 10 minutes | QuickTime / MOV | fMP4 | 2.969 | 1.769–4.139 | 5.989 | 0.801 | 25.5 | 92.2 | 241.8 | 241.8 | PASS | PASS |
| 10 minutes | Matroska / MKV | TS | 3.228 | 1.822–4.533 | 6.009 | 0.885 | 24.4 | 85.5 | 241.9 | 249.5 | PASS | PASS |
| 10 minutes | Matroska / MKV | fMP4 | 3.004 | 1.855–4.485 | 4.537 | 0.785 | 25.6 | 87.5 | 241.6 | 242.0 | PASS | PASS |
| 10 minutes | MPEG-TS | TS | 3.303 | 2.781–6.266 | 5.372 | 0.911 | 27.8 | 85.2 | 252.0 | 249.6 | PASS | PASS |
| 10 minutes | MPEG-TS | fMP4 | 3.439 | 2.414–6.239 | 5.979 | 1.016 | 30.1 | 88.8 | 251.6 | 241.8 | PASS | PASS |
| 10 minutes | MPEG-TS (M2TS mode) | TS | 3.757 | 3.055–5.414 | 5.646 | 0.943 | 25.1 | 85.1 | 257.1 | 249.6 | PASS | PASS |
| 10 minutes | MPEG-TS (M2TS mode) | fMP4 | 2.470 | 1.712–4.596 | 5.303 | 1.000 | 35.7 | 88.9 | 257.2 | 241.8 | PASS | PASS |
| 10 minutes | AVI | TS | 4.099 | 1.933–4.939 | 5.903 | 1.111 | 25.9 | 86.0 | 251.0 | 249.6 | FAIL | timestamps / audio-video alignment |
| 10 minutes | AVI | fMP4 | 3.565 | 2.989–6.701 | 6.077 | 1.167 | 27.7 | 87.8 | 251.0 | 241.9 | FAIL | timestamps / audio-video alignment |
| 10 minutes | Flash Video / FLV | TS | 3.810 | 3.204–6.040 | 7.583 | 0.812 | 21.3 | 87.1 | 242.2 | 249.6 | PASS | PASS |
| 10 minutes | Flash Video / FLV | fMP4 | 3.369 | 1.725–7.402 | 5.553 | 0.852 | 29.1 | 89.1 | 242.3 | 242.0 | PASS | PASS |
| 10 minutes | Adobe F4V | TS | 4.654 | 1.730–7.991 | 5.770 | 0.887 | 19.1 | 89.9 | 241.8 | 249.5 | PASS | PASS |
| 10 minutes | Adobe F4V | fMP4 | 2.986 | 2.812–4.332 | 6.028 | 0.781 | 25.9 | 92.0 | 242.0 | 241.8 | PASS | PASS |
| 10 minutes | 3GPP / 3GP | TS | 2.927 | 1.649–5.972 | 6.215 | 0.861 | 29.4 | 90.8 | 242.0 | 249.5 | PASS | PASS |
| 10 minutes | 3GPP / 3GP | fMP4 | 2.749 | 2.291–6.171 | 5.714 | 0.739 | 25.7 | 91.9 | 242.3 | 241.8 | PASS | PASS |
| 10 minutes | 3GPP2 / 3G2 | TS | 3.531 | 2.445–4.873 | 5.531 | 0.831 | 24.2 | 90.4 | 242.1 | 249.5 | PASS | PASS |
| 10 minutes | 3GPP2 / 3G2 | fMP4 | 3.302 | 1.764–4.768 | 6.851 | 0.754 | 22.1 | 92.0 | 241.8 | 241.8 | PASS | PASS |
| 10 minutes | NUT | TS | 3.300 | 2.891–4.654 | 6.128 | 0.760 | 22.1 | 89.7 | 242.0 | 249.5 | PASS | PASS |
| 10 minutes | NUT | fMP4 | 2.886 | 1.695–4.921 | 6.134 | 0.767 | 25.4 | 86.8 | 241.8 | 241.8 | PASS | PASS |
| 10 minutes | ASF | TS | 0.164 | 0.153–0.201 | 0.183 | 0.162 | 98.7 | 66.8 | 0.7 | 0.0 | FAIL | FFmpeg muxing failed |
| 10 minutes | ASF | fMP4 | 3.322 | 2.348–5.007 | 6.914 | 1.216 | 34.8 | 530.8 | 245.0 | 241.7 | FAIL | target_duration_valid, timestamps / audio-video alignment |
| Full: 10:34.6 | MP4 (standard) | TS | 3.486 | 1.907–4.663 | 4.456 | 0.822 | 27.0 | 91.4 | 249.4 | 256.9 | PASS | PASS |
| Full: 10:34.6 | MP4 (standard) | fMP4 | 3.185 | 2.400–5.495 | 5.453 | 0.758 | 26.4 | 88.1 | 248.9 | 248.9 | PASS | PASS |
| Full: 10:34.6 | MP4 (fast-start) | TS | 3.528 | 1.645–4.956 | 5.514 | 0.852 | 23.6 | 91.9 | 248.7 | 256.9 | PASS | PASS |
| Full: 10:34.6 | MP4 (fast-start) | fMP4 | 4.597 | 4.156–7.468 | 6.043 | 0.837 | 15.7 | 88.5 | 249.2 | 248.9 | PASS | PASS |
| Full: 10:34.6 | MP4 (fragmented) | TS | 3.872 | 1.916–6.023 | 4.130 | 1.017 | 26.3 | 90.8 | 248.8 | 256.9 | PASS | PASS |
| Full: 10:34.6 | MP4 (fragmented) | fMP4 | 3.681 | 2.522–4.680 | 6.958 | 0.979 | 28.9 | 86.3 | 248.8 | 248.9 | PASS | PASS |
| Full: 10:34.6 | QuickTime / MOV | TS | 3.100 | 2.702–7.598 | 6.905 | 0.786 | 23.2 | 93.9 | 248.9 | 256.9 | PASS | PASS |
| Full: 10:34.6 | QuickTime / MOV | fMP4 | 3.381 | 1.912–6.203 | 5.606 | 0.918 | 23.9 | 88.5 | 249.3 | 248.9 | PASS | PASS |
| Full: 10:34.6 | Matroska / MKV | TS | 3.218 | 2.048–4.851 | 5.669 | 0.837 | 24.8 | 84.5 | 248.7 | 256.9 | PASS | PASS |
| Full: 10:34.6 | Matroska / MKV | fMP4 | 3.637 | 1.786–6.468 | 5.999 | 0.854 | 22.0 | 85.0 | 249.1 | 249.1 | PASS | PASS |
| Full: 10:34.6 | MPEG-TS | TS | 3.837 | 2.070–4.999 | 6.958 | 0.920 | 24.5 | 85.3 | 259.1 | 256.9 | PASS | PASS |
| Full: 10:34.6 | MPEG-TS | fMP4 | 3.601 | 2.494–4.507 | 6.619 | 0.947 | 26.3 | 86.5 | 259.3 | 248.9 | PASS | PASS |
| Full: 10:34.6 | MPEG-TS (M2TS mode) | TS | 3.868 | 2.690–4.224 | 4.980 | 0.965 | 25.5 | 85.4 | 264.7 | 256.9 | PASS | PASS |
| Full: 10:34.6 | MPEG-TS (M2TS mode) | fMP4 | 3.584 | 2.671–5.715 | 5.770 | 1.011 | 31.1 | 86.4 | 264.8 | 248.9 | PASS | PASS |
| Full: 10:34.6 | AVI | TS | 3.811 | 2.431–4.480 | 4.545 | 1.125 | 32.8 | 86.9 | 258.3 | 256.9 | FAIL | timestamps / audio-video alignment |
| Full: 10:34.6 | AVI | fMP4 | 3.270 | 2.693–4.732 | 5.366 | 1.186 | 33.2 | 85.8 | 258.1 | 249.0 | FAIL | timestamps / audio-video alignment |
| Full: 10:34.6 | Flash Video / FLV | TS | 3.982 | 2.448–4.548 | 6.400 | 0.798 | 20.4 | 83.8 | 249.1 | 256.9 | PASS | PASS |
| Full: 10:34.6 | Flash Video / FLV | fMP4 | 3.236 | 2.864–4.888 | 4.525 | 0.788 | 23.7 | 86.8 | 249.5 | 249.1 | PASS | PASS |
| Full: 10:34.6 | Adobe F4V | TS | 3.424 | 1.625–4.220 | 6.124 | 0.882 | 22.5 | 90.6 | 249.0 | 256.9 | PASS | PASS |
| Full: 10:34.6 | Adobe F4V | fMP4 | 3.748 | 1.794–5.175 | 6.032 | 0.797 | 22.7 | 88.2 | 249.2 | 248.9 | PASS | PASS |
| Full: 10:34.6 | 3GPP / 3GP | TS | 3.916 | 1.999–5.877 | 7.169 | 0.839 | 20.0 | 90.8 | 249.1 | 256.9 | PASS | PASS |
| Full: 10:34.6 | 3GPP / 3GP | fMP4 | 3.416 | 1.782–5.550 | 5.228 | 0.889 | 23.0 | 88.5 | 249.1 | 248.9 | PASS | PASS |
| Full: 10:34.6 | 3GPP2 / 3G2 | TS | 4.161 | 2.469–8.757 | 4.347 | 0.823 | 19.4 | 91.5 | 249.2 | 256.9 | PASS | PASS |
| Full: 10:34.6 | 3GPP2 / 3G2 | fMP4 | 3.656 | 2.552–5.282 | 5.732 | 0.836 | 21.1 | 88.5 | 249.9 | 248.9 | PASS | PASS |
| Full: 10:34.6 | NUT | TS | 4.433 | 2.004–4.709 | 9.299 | 0.816 | 18.0 | 90.2 | 249.0 | 256.9 | PASS | PASS |
| Full: 10:34.6 | NUT | fMP4 | 3.586 | 2.736–7.088 | 6.934 | 0.775 | 23.1 | 84.5 | 248.9 | 248.9 | PASS | PASS |
| Full: 10:34.6 | ASF | TS | 0.174 | 0.152–0.207 | 0.186 | 0.173 | 98.6 | 66.9 | 0.7 | 0.0 | FAIL | FFmpeg muxing failed |
| Full: 10:34.6 | ASF | fMP4 | 3.855 | 2.901–5.127 | 6.415 | 1.325 | 32.4 | 543.7 | 252.1 | 248.8 | FAIL | target_duration_valid, timestamps / audio-video alignment |

