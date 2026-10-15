# AVI/ASF → MP4 → HLS TS: follow-up experiment

Tested 30-second and full-length fixtures from the scaling experiment, with both default timestamp handling and `-fflags +genpts` before reading AVI/ASF. Every stage used `-c copy`; no re-encoding. These eight exploratory attempts are separate from the original benchmark. One attempt per case, no controlled cache or repeated performance measurements.

**All eight routes produced MP4 and HLS files, but none preserved the reference timing within the required 2 ms tolerance.** Encoded video/audio payload identity passed for all eight. The intermediate MP4 gets past the direct ASF-to-TS mux error; it does not prove correct restoration of timestamps.

| Source length | Input | Timestamp mode | MP4 exit | HLS exit | Max PTS error ms | A/V start offset ms | DTS increasing | Accepted |
|---|---|---|---|---|---|---|---|---|
| 30s | AVI | default | 0 | 0 | 99.667 | 0.000 | False | False |
| 30s | AVI | genpts | 0 | 0 | 98.000 | 55.000 | True | False |
| 30s | ASF | default | 0 | 0 | 100.000 | 21.000 | False | False |
| 30s | ASF | genpts | 0 | 0 | 67.000 | 55.000 | True | False |
| full | AVI | default | 0 | 0 | 88.000 | 0.000 | False | False |
| full | AVI | genpts | 0 | 0 | 64.667 | 55.000 | True | False |
| full | ASF | default | 0 | 0 | 67.000 | 21.000 | False | False |
| full | ASF | genpts | 0 | 0 | 34.000 | 55.000 | True | False |

The reference video starts 88 ms after audio. A shared container start-time shift is allowed by comparison; errors above are remaining relative timing differences, not simply a different starting timestamp. Default routes also contain non-increasing decode timestamps. `+genpts` improves that check but does not restore the original timeline.

The failure is established by full-stream compressed-media identity and packet-timing comparison. Independent segment decoding and browser acceptance were not run for these already rejected assets. No claim of correct playback, duration or independent-segment safety is made.

This does not rule out a separate source-specific timestamp repair strategy. Repair and re-encoding were not tested here. Container changes alone are insufficient for these fixtures.

Evidence: [results.json](results.json), exact commands and per-stage logs linked below. Prepared MP4 and HLS files remain in the case subdirectories. Diagnostic wall times are retained but must not be compared as formal benchmark medians.

- 30s-avi-default: [MP4 log](logs/30s-avi-default-to-mp4.log), [HLS log](logs/30s-avi-default-to-hls.log).
- 30s-avi-genpts: [MP4 log](logs/30s-avi-genpts-to-mp4.log), [HLS log](logs/30s-avi-genpts-to-hls.log).
- 30s-asf-default: [MP4 log](logs/30s-asf-default-to-mp4.log), [HLS log](logs/30s-asf-default-to-hls.log).
- 30s-asf-genpts: [MP4 log](logs/30s-asf-genpts-to-mp4.log), [HLS log](logs/30s-asf-genpts-to-hls.log).
- full-avi-default: [MP4 log](logs/full-avi-default-to-mp4.log), [HLS log](logs/full-avi-default-to-hls.log).
- full-avi-genpts: [MP4 log](logs/full-avi-genpts-to-mp4.log), [HLS log](logs/full-avi-genpts-to-hls.log).
- full-asf-default: [MP4 log](logs/full-asf-default-to-mp4.log), [HLS log](logs/full-asf-default-to-hls.log).
- full-asf-genpts: [MP4 log](logs/full-asf-genpts-to-mp4.log), [HLS log](logs/full-asf-genpts-to-hls.log).
