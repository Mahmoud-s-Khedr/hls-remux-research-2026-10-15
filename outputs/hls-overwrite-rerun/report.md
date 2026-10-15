# Paired rerun: new output folder vs overwritten folder (16 October 2026)

## Question

In the original study (`../hls-scaling/`), repeated runs that overwrote existing HLS files took ~3.5 s to exit, while runs into new folders took ~0.6–0.7 s. Was that caused by overwriting itself, or by the storage state at the time (disk ~93% full after ~100 GiB of writes)?

## Method

- Same laptop, same Btrfs volume, FFmpeg 8.1.3, `powersave` governor (as in the original study).
- Disk state differs on purpose: **99 GiB free (58% used)** instead of ~16 GiB free.
- Full-length standard MP4 input, rebuilt with the original preparation commands. Every output (TS 100 files, fMP4 101 files) was **byte-identical** to the original study's (`prepare.json`, `byte_identical` in each measurement).
- Per output style, 10 repeats × {new folder, overwrite the persistent folder}. Both conditions run back to back in seeded random order (`random.Random(20261016)`). Input pre-read and `sync` + 2 s pause before every run.
- Measurement uses the original `../hls-scaling/scripts/measure.py`, unchanged (exact child CPU/RSS/I/O, then serial fsync of all outputs + directory).
- Repeat 1 also samples `Dirty`/`Writeback` from `/proc/meminfo` every 50 ms (`traces/`).

Scripts: `scripts/rerun.py` (prepare/run) and `scripts/analyze.py` (all numbers below come from it; also in `report-tables.md` and `analysis.json`).

## Results

| Output | Folder | n | FFmpeg exit s median (IQR) | CPU s median (IQR) | fsync s median (IQR) | Exit + fsync s median (IQR) | Byte-identical |
|---|---|---|---|---|---|---|---|
| TS | new | 10 | 0.93 (0.83–1.38) | 1.20 (1.07–1.46) | 0.40 (0.37–0.44) | 1.33 (1.20–1.81) | all |
| TS | overwrite | 10 | 1.08 (0.92–1.33) | 1.33 (1.16–1.55) | 0.17 (0.16–0.20) | 1.25 (1.09–1.52) | all |
| fMP4 | new | 10 | 0.85 (0.75–1.03) | 1.06 (0.95–1.23) | 0.39 (0.37–0.41) | 1.28 (1.12–1.44) | all |
| fMP4 | overwrite | 10 | 0.94 (0.89–1.14) | 1.15 (1.10–1.38) | 0.16 (0.16–0.17) | 1.10 (1.05–1.32) | all |

| Output | Metric | Median paired difference, overwrite − new (s) | Overwrite slower in |
|---|---|---|---|
| TS | FFmpeg exit s | +0.07 | 7/10 |
| TS | CPU s | +0.07 | 7/10 |
| TS | fsync s | -0.22 | 0/10 |
| TS | Exit + fsync s | -0.13 | 1/10 |
| fMP4 | FFmpeg exit s | +0.11 | 8/10 |
| fMP4 | CPU s | +0.12 | 8/10 |
| fMP4 | fsync s | -0.22 | 0/10 |
| fMP4 | Exit + fsync s | -0.11 | 4/10 |

Kernel writeback during repeat 1 (MiB):

| Output | Folder | Peak Writeback while FFmpeg runs | Peak Dirty while FFmpeg runs | Peak Writeback during fsync |
|---|---|---|---|---|
| fMP4 | new | 0.7 | 239.1 | 3.3 |
| fMP4 | overwrite | 2.9 | 7.1 | 0.0 |
| TS | new | 1.1 | 232.7 | 1.8 |
| TS | overwrite | 1.0 | 8.8 | 0.0 |

For comparison, the original session (full-length MP4, medians): overwrite runs 3.49/3.19 s to exit and 4.48/5.58 s with fsync; fresh-folder control 0.77/0.70 s to exit and 7.90/7.91 s with fsync (TS/fMP4).

## Verdict

1. **The mechanism is real.** When files are overwritten, Btrfs writes data out during FFmpeg's run: dirty data never exceeds ~9 MiB. New files accumulate the whole ~235 MiB output as dirty pages until fsync. Overwriting moves writeback from fsync into the run (fsync −0.22 s, 0/10 exceptions).
2. **On healthy storage it barely matters.** Overwriting adds about 0.1 s to FFmpeg's exit time, and the extra time is matched by extra CPU seconds, i.e. kernel work done in FFmpeg's context, not waiting. Total time to durable completion is about the same, or slightly lower for overwrite.
3. **The original 3 s gap needed slow storage.** The same jobs took 1.1–1.3 s including fsync here, against 4.5–7.9 s in the original session. The device or filesystem was roughly 4–6× slower then, so whichever phase carried the writeback (FFmpeg's run for overwrites, fsync for new folders) became slow. Disk fullness and/or ~100 GiB of sustained writes are the likely causes; this rerun can't separate the two.

Decision rule stated in advance: "if there's no gap with ample free space, the original gap depended on disk state". That is the outcome.

**Usable number for this laptop on healthy storage:** about 0.85–1.1 s to remux a 250 MB 1080p file to one HLS style, and about 1.1–1.3 s until it is fsynced. Storage state is the dominant variable; re-measure on target storage.

## Limits

- One film, one laptop, Btrfs only. ext4/XFS may behave differently (ext4 has a similar `auto_da_alloc` rule for truncate-and-rewrite).
- The nearly full disk state was not reproduced (it would need ~85 GiB of filler writes), so the "slow storage" explanation for the original session is inferred from the comparison, not tested directly.
- CPU seconds here (~1.0–1.3 s) are higher than the original session's (~0.76–0.92 s) for identical work. The cause is not known (possibly frequency scaling under `powersave` or background load). Compare CPU figures within a session only.
- 10 paired repeats per output style: fine for the size of effect being tested, not for tail latency.
