# Remux-first HLS: feasibility study (October 2026)

Can a remux server make uploads watchable within seconds for premium users, by repackaging H.264/AAC into HLS without re-encoding, while the full 240p–1080p ladder encodes in the background?

**Yes, for H.264/AAC uploads in common containers, with an input gate and an output check.** About 1 CPU-second and under 100 MiB RAM per 10-minute 1080p file. ~1.2 s including fsync on healthy storage. Bit-exact output from 12 of 14 container types. AVI/ASF must go to the ladder. Time-to-watch is dominated by download/upload, not remuxing.

**Read [`REPORT.md`](REPORT.md).** It has all results, tables, charts, the production design (input gate, output check, switching to the ladder) and the limits.

| | |
|---|---|
| [`REPORT.md`](REPORT.md) | Full report |
| [`charts/`](charts/) | Resource scaling, completion time, CPU by container, memory, concurrency, overwrite vs new |
| [`data/`](data/) | All measured data (JSON) and the 168 output playlists |
| [`logs/`](logs/) | Every non-empty FFmpeg log |
| [`scripts/`](scripts/) | Test harnesses and `report/build.py` (regenerates charts and tables) |
| `MANIFEST.sha256` | `sha256sum -c MANIFEST.sha256` |

Video files (~30 GB) are not kept; they regenerate byte-identically from the public source with FFmpeg 8.1.3 (REPORT.md, Appendix B). Earlier reports and intermediate files remain in git history (commit `5ddbc60` and earlier).

Big Buck Bunny © 2008 Blender Foundation, CC BY 3.0.
