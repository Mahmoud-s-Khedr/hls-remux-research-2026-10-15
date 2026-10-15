# H.264 → HLS remuxing benchmark

Test date: 15 October 2026, Africa/Cairo. **24/28 outputs passed both media validation and normal-speed browser playback.**

The table reports median wall-clock seconds from five measured runs, after one warm-up. Values marked FAIL are not approved working HLS outputs even if FFmpeg produced a file.

| Original container / layout | Video codec | Resolution | HLS TS (s) | HLS fMP4 (s) | TS validation | fMP4 validation |
|---|---|---|---|---|---|---|
| MP4 (standard) | H.264 | 1920×1080 | 0.155 | 0.155 | PASS | PASS |
| MP4 (fast-start) | H.264 | 1920×1080 | 0.182 | 0.163 | PASS | PASS |
| MP4 (fragmented) | H.264 | 1920×1080 | 0.152 | 0.172 | PASS | PASS |
| QuickTime / MOV | H.264 | 1920×1080 | 0.152 | 0.157 | PASS | PASS |
| Matroska / MKV | H.264 | 1920×1080 | 0.161 | 0.161 | PASS | PASS |
| MPEG-TS | H.264 | 1920×1080 | 0.160 | 0.169 | PASS | PASS |
| MPEG-TS (M2TS mode) | H.264 | 1920×1080 | 0.159 | 0.166 | PASS | PASS |
| AVI | H.264 | 1920×1080 | 0.163 | 0.178 | FAIL | FAIL |
| Flash Video / FLV | H.264 | 1920×1080 | 0.158 | 0.167 | PASS | PASS |
| Adobe F4V | H.264 | 1920×1080 | 0.153 | 0.159 | PASS | PASS |
| 3GPP / 3GP | H.264 | 1920×1080 | 0.164 | 0.167 | PASS | PASS |
| 3GPP2 / 3G2 | H.264 | 1920×1080 | 0.153 | 0.162 | PASS | PASS |
| NUT | H.264 | 1920×1080 | 0.153 | 0.165 | PASS | PASS |
| ASF | H.264 | 1920×1080 | — | 0.177 | FAIL | FAIL |

## Sample and controls

- Same H.264 High-profile, 1920×1080, 30 fps, yuv420p stream for every fixture; 900 decoded video frames, nominally 30 seconds. B-frames are present.
- Source: [Big Buck Bunny, Blender download](https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip). The MP4 contains MP3 and AC-3 audio; the first audio track was converted to AAC LC, 48 kHz stereo, 128 kb/s once during fixture preparation. Every measured operation uses `-c copy` for video and audio.
- A common TS intermediate normalizes source edit-list/priming behavior before preparing the input containers. Decoded frame hashes and PCM hashes are checked against `reference.mp4`.
- The requested segment target is six seconds. Keyframe-preserving remuxing produces five segments per passing output: approximately 8.333, 7.900, 3.867, 7.300, and 2.600 seconds. These are not exact six-second segments. The reference timestamps and AAC packet boundaries make player duration approximately 30.1 seconds.
- MP4 variants are actual different file layouts: standard, fast-start, and fragmented. Other ISO base media relatives (MOV, F4V, 3GP, 3G2) are listed separately; their file extensions do not represent different video codecs.

## Timing method and environment

One untimed warm-up per case, five sequential timed runs in seeded shuffled order per round, after all browser/decode tests finished. perf_counter wall time includes process startup, input probing, stream copying, writing all segments and final playlist, and process exit. Warm filesystem cache; no fsync/durability timing; no concurrent benchmark jobs. Download, fixture preparation, audio encoding, and validation excluded.

- CPU: AMD Ryzen 5 PRO 5650U, 6 cores / 12 logical CPUs.
- FFmpeg: `ffmpeg version 8.1.3 Copyright (c) 2000-2026 the FFmpeg developers`.
- OS: `Linux-7.2.10-200.fc44.x86_64-x86_64-with-glibc2.43`.
- Browser: Chromium `156.0.8078.4` with `hls.js 1.6.13` over localhost HTTP.
- Timings apply to this short sample and this machine. Startup and container probing contribute materially; these results should not be extrapolated linearly to large files. The test does not measure upload time, CDN/network behavior, cold storage, or durable disk flushes.

## What PASS means

1. Every playlist references existing, nonempty files, has VOD/end markers, and has a valid target duration. fMP4 outputs also reference an existing initialization segment.
2. The complete playlist decodes with strict FFmpeg error handling. All 900 decoded video frames match the reference, frame by frame, and decoded audio PCM matches the reference exactly.
3. Every individual TS segment, or fMP4 fragment combined with its initialization segment, decodes independently and begins with a video keyframe.
4. Decode timestamps increase. Presentation timestamps, including relative audio/video alignment, match the reference within 2 ms after allowing a shared container start-time shift.
5. The browser preloads the clip, seeks to 18 seconds and back to the beginning, and plays to the end at normal speed with no HLS.js or media errors. Playback starts at 0.1 seconds to avoid the reference's small leading audio-only interval. This is automated muted playback, not a human listening test.

This establishes correctness for the tested assets and browser. Safari/iOS native HLS, other hardware decoders, and variable network conditions were not tested. Browser dropped-frame counters are retained in the raw results; they describe rendering under the local test load, separately from the decoded-frame integrity check.

## Compatibility findings

- **Fragmented MP4 fixture:** `+frag_keyframe+delay_moov+default_base_moof` preserves the reference's initial relative audio/video alignment. The first `empty_moov` preparation shifted alignment by approximately 21 ms; the timestamp audit rejected it despite successful playback. The corrected fixture and both corrected HLS outputs were revalidated. The first attempt remains in the raw results.
- **TS/M2TS → fMP4:** requires `-bsf:a aac_adtstoasc` in this workflow. It adapts AAC packet headers without re-encoding. The initial unadapted attempts failed and remain recorded.
- **ASF:** fixture preparation requires `-bsf:v h264_mp4toannexb` to produce a decodable H.264 ASF file with this FFmpeg build. That bitstream adaptation does not re-encode video. The subsequent HLS TS mux still fails on missing timestamps, and the fMP4 output fails strict timing/decode validation. Both ASF paths are rejected.
- **AVI:** this H.264 B-frame fixture exposes timestamp limitations. `-fflags +genpts` was tested. Both resulting HLS variants reach the end in the browser, but strict validation catches non-monotonic presentation timestamps, so both are rejected. This is a finding for this fixture, not a claim that every H.264 AVI file must fail.
- WebM and Ogg are outside the H.264 container selection. MPEG-PS, DVD/VOB, and MXF are not claimed as tested here. File aliases alone are not counted as additional container coverage.
- An exploratory 8× browser stress run reached playback completion but logged buffering warnings. It is preserved separately as `browser-stress-8x.json`; the PASS statuses above require the subsequent normal-speed run with no HLS/media errors. No claim of clean 8× playback is made.

## Files and reproduction

- `inputs/`: the actual input fixtures; `reference.mp4`: the common reference.
- `hls/<input>/mpegts/playlist.m3u8`: TS HLS output.
- `hls/<input>/fmp4/playlist.m3u8`: fMP4 HLS output, `init.mp4`, and `.m4s` fragments.
- `results.json`: all measured runs, codec probes, validation results, and initial failures.
- `browser-validation.json`: normal-speed browser playback and seeking results.
- `logs/`: FFmpeg logs and per-frame MD5 records. `commands.json`, `adjustment-commands.json`, and `final-timing-commands.json` contain the exact executed command arguments.
- `scripts/`: benchmark, compatibility adjustments, timestamp audit, final timing, and browser harness scripts. They retain this workspace's tool paths; adjust them for another machine. For the Python scripts, `HLS_BENCHMARK_ROOT` can point to the workspace root containing `work/` and `outputs/`. The source download belongs in `work/` under its original MP4 filename.

To play the files, serve this output directory over HTTP and open `report.html`; local `file://` playback does not provide the same browser behavior. Serve only trusted test files.

## Attribution

Big Buck Bunny © 2008 Blender Foundation / www.bigbuckbunny.org. Source material licensed under Creative Commons Attribution 3.0: https://peach.blender.org/about/ . This test uses a shortened excerpt, remuxed video, and a prepared AAC audio track. The source MP4 SHA-256 is `ae51005850b0ff757fe60c3dd7a12d754d3cd2397d87d939b55235e457f97658`.
