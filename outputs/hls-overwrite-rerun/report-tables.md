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

Kernel writeback during repeat 1 (`/proc/meminfo`, sampled every 50 ms; MiB):

| Output | Folder | Peak Writeback while FFmpeg runs | Peak Dirty while FFmpeg runs | Peak Writeback during fsync |
|---|---|---|---|---|
| fMP4 | new | 0.7 | 239.1 | 3.3 |
| fMP4 | overwrite | 2.9 | 7.1 | 0.0 |
| TS | new | 1.1 | 232.7 | 1.8 |
| TS | overwrite | 1.0 | 8.8 | 0.0 |
