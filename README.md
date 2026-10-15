# H.264 → HLS remuxing research (15 October 2026)

Preserved evidence from a Codex session that measured how fast, and how correctly, FFmpeg 8.1.3 remuxes one H.264/AAC film (Big Buck Bunny, 1080p30) from 14 container layouts into HLS (TS and fMP4), at six lengths from 30 seconds to the full 10:34.

Original workspace: `~/Documents/Codex/2026-10-15/wha` (may be deleted later).

## Start here

| File | What it is |
|---|---|
| `outputs/hls-scaling/report.html` | **Main report.** Open in a browser (tables and charts work offline; the video player needs the media, which is not kept). |
| `outputs/hls-scaling/report.md` | Same report as Markdown. |
| `REVIEW.md` | Independent review of the methodology and conclusions; read before reusing any number. |
| `outputs/research-reference/README.md` | Codex's index of every experiment (E1–E4, V1–V4) and where its evidence lives. |
| `outputs/hls-benchmark/report.md` | Earlier 30-second baseline (different method; don't mix its timings with the scaling data). |
| `outputs/hls-via-mp4/report.md` | Follow-up: AVI/ASF → MP4 → HLS, all eight routes rejected. |

## What is kept, and what is not

Kept (≈45 MB): every report, `results.json` and other raw JSON, all 1,008+ per-run measurement records, every FFmpeg log, HLS playlists, charts, harness scripts (`outputs/*/scripts`, `work/scaling`), Codex's run notes, inventories and checksums, and Codex's `evidence.zip`.

Not kept: video files (`.ts .m4s .mp4 .mkv .mov .flv .nut .avi .asf .m2ts .3gp .3g2 .f4v`) and the source download. They were ~30 GB and are regenerable:

1. Download `https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip` and check the extracted MP4's SHA-256 is `ae51005850b0ff757fe60c3dd7a12d754d3cd2397d87d939b55235e457f97658`.
2. Use FFmpeg **8.1.3** (other versions may produce different bytes); the exact commands are in `results.json` (`cases[].command`) and the scripts.
3. Compare regenerated segments against `outputs/research-reference/inventory.json` and `outputs/hls-scaling/segment-validation-cache.json`.

Integrity: when copied, all 5,242 files listed in Codex's `outputs/research-reference/SHA256SUMS.txt` that are present here matched byte-for-byte. `MANIFEST.sha256` covers every file in this folder; verify with `sha256sum -c MANIFEST.sha256`.

Big Buck Bunny © 2008 Blender Foundation, CC BY 3.0.
