# Review of the H.264 → HLS remuxing research

Reviewed 15 October 2026 by Claude (Claude Code), from the reports, the raw `results.json`, `fresh-output.json`, `concurrency.json`, the harness scripts and Codex's run notes. Headline medians were recomputed from raw runs and match the report exactly.

## Overall verdict

The correctness work is excellent and trustworthy. The timing work is careful in method but was run on a disk that was filling up, so most wall-clock numbers in the main matrix describe that disk's state more than FFmpeg's remux cost. Use CPU seconds, RSS, I/O bytes, and the fresh-output control for planning; treat the main-matrix wall times for ≥2-minute inputs as unreliable.

*(Revised 16 October 2026: the noisy wall times come from slow storage in that session **combined with** the matrix overwriting its own output files, which moved disk writes into FFmpeg's measured time. The fresh-output 0.7 s is not a usable completion time. A paired rerun on healthy storage measured ~1.1–1.3 s including fsync. See the [Addendum](#addendum-16-october-2026-overwrite-effect).)*

## What is solid

- **Correctness validation is unusually strict.** Every accepted output matched the reference bit-for-bit at the compressed-payload level (H.264 VCL + SPS/PPS, AAC ADTS), PTS within 2 ms per packet, order-sensitive PTS audit, every segment decoded independently starting on a keyframe, plus browser seek/end checks. 144/168 accepted is a credible result.
- **Failure analysis is honest.** AVI and ASF are rejected even where FFmpeg exited 0 and the browser played to the end. The key lesson — exit code 0 and "it plays" are not proof of a correct asset — is well evidenced.
- **Resource measurement is sound.** `measure.py` uses fork/exec + `wait4`, so CPU seconds and peak RSS are exact for the FFmpeg child; I/O deltas subtract the wrapper's own baseline; fsync is timed separately. CPU seconds are stable across repeats (coefficient of variation ≈ 5–16%).
- **Reproducibility.** Exact argv per case, FFmpeg build config, source SHA-256, seeded run order, per-run logs and measurement JSON are all retained.
- **Scope statements** ("What this does NOT prove") are appropriately cautious.

## Problems and caveats

1. **The disk was filling during timing (most important).** Free space fell from ~42 GiB to ~16–17 GiB on a 236 GiB Btrfs volume (≈93% full) while 102 GiB of writes were issued. Evidence of contamination:
   - Wall time per run varies 2–5× across repeats of the same case (e.g. 10-minute fMP4: 1.54 s → 7.10 s) while CPU seconds stay flat.
   - Median wall/CPU ratio across all runs is 2.1, up to 9.9; the fresh-output control is ≈0.75 (CPU-bound).
   - Warm-round medians drift upward 0.65 → 1.21 s across rounds 1–5.
   - Results are non-monotonic: 10-minute TS median 4.42 s > full-length 3.49 s, although the full file is larger.
   The report discloses drift and Btrfs overwrite effects but still leads with these wall times and fits regressions to them (R² 0.94/0.99 on six noisy points). **Use the fresh-output table (0.23 s at 30 s → ~0.7–0.77 s at full length) as the realistic remux time.**
   *(Superseded in part, 16 October 2026: the cause attributed here and the advice in bold are revised in the [Addendum](#addendum-16-october-2026-overwrite-effect).)*
2. **Fsync numbers are environment-bound.** ~8 s to flush ~250 MB (~30 MB/s) is very slow for NVMe and almost certainly reflects the near-full Btrfs volume. Don't use "exit + flush" or "with-flush jobs/s" for capacity planning on other hardware; re-measure on the target storage.
3. **Concurrency sample is thin.** Three repetitions per point, and with-flush throughput is erratic (fMP4: 0.128 jobs/s with 1 worker vs 0.229 with 4). The exit-time scaling (1.4 → ~3 jobs/s with 4 workers) is directionally useful; the with-flush figures are not.
4. **Machine was not quiet.** `powersave` governor, an active desktop and the Codex app running. Fine for relative comparisons, weaker for absolute numbers.
5. **AVI/ASF failures partly come from how the fixtures were made.** The AVI/ASF inputs were produced by FFmpeg itself from the MP4 reference; these containers cannot carry B-frame PTS faithfully, so part of the failure is in fixture creation, not only in AVI→HLS. The conclusion "these fixtures fail this pipeline" is correct; "real-world AVI uploads will fail" is plausible but not shown. Also, a 2 ms tolerance is far stricter than perceptibility (a ~33 ms A/V offset is near lip-sync thresholds); the right production reading is "needs timestamp repair or re-encode", not "unplayable".
6. **Minor inconsistency between reports.** The 30-second baseline describes AVI as failing on "non-monotonic presentation timestamps", while the scaling report says DTS are increasing and PTS unique, with the failure being PTS values off by up to 65 ms. The scaling report's description is the precise one.
7. **Portability nits.** `hls-scaling/report.md` (4 places) and `research-reference/complete-research-record.md` (14 places) link to absolute paths under `~/Documents/Codex/...`; those image links break once the original folder is removed. `report.html` has no absolute paths and is the better canonical view. Files were left byte-identical here so the checksums stay valid.
8. **Single source.** One film, one codec profile, one laptop. Conclusions about container compatibility are well supported; numbers do not generalise.

## Practical takeaways that hold up

- Stream-copy remux of a ~250 MB 1080p H.264 file to HLS costs about **0.8–1.0 CPU-seconds and ~90 MiB RSS** per output style; time is dominated by storage, not CPU.
- MP4 (all layouts), MOV, MKV, TS/M2TS, FLV, F4V, 3GP/3G2 and NUT inputs remux correctly to both TS and fMP4 HLS with `-c copy` (+ `aac_adtstoasc` for fMP4).
- AVI and ASF with B-frame H.264 need a separate timestamp-repair or re-encode path; going via an MP4 intermediate does not fix them (`hls-via-mp4`).
- Validate outputs; exit code and browser playback alone accepted broken ASF→fMP4 output (0-second playlist) that also used ~540 MiB RAM.

## If this is to be published or relied on

Re-run the timing phase (not validation) on a volume with ample free space, writing to fresh directories, with the `performance` governor and a quiet machine, and add more repetitions for concurrency. The correctness results do not need re-running.

## Addendum (16 October 2026): overwrite effect

A closer look at the raw measurement records changes the explanation for the noisy wall times (issue 1) and the advice drawn from it. Everything else in this review stands.

### What the data shows

The main matrix ran FFmpeg with `-y` into the **same output folder** for all six measured runs of a case, so runs 1–5 and the input-evicted run truncated and rewrote existing files (`outputs/hls-scaling/scripts/run.py`, `command()` and the timing loop). The untimed warm-up of each case was the only run that wrote into a **newly created** folder. Its record is kept in `measurements/*-warmup.json` but excluded from all report statistics.

Medians for every run that wrote ≥200 MB (10-minute and full-length cases), recomputed from `outputs/hls-scaling/measurements/`:

| Runs | n | Output files | FFmpeg exit s | CPU s | fsync s | Exit + fsync s |
|---|---|---|---|---|---|---|
| Warm-up (start of session) | 54 | new | **0.59** | 0.78 | 2.16 | 2.82 |
| Warm repeats 1–5 | 270 | overwritten | **3.53** | 0.87 | 1.17 | 4.88 |
| Input-evicted | 54 | overwritten | **5.94** | 1.16 | 1.46 | 7.21 |
| Fresh-output control (end of session) | 24 | new | **0.69** | 0.90 | 7.22 | 7.91 |

- In **54 of 54** cases, the warm-up was faster than that same case's median overwrite run, while CPU seconds were similar.
- New-file runs were fast to exit both at the **start** of the session (warm-ups, most free space) and at the **end** (fresh control, least free space), so the *exit-time* gap follows the overwrite pattern rather than free space alone.
- When FFmpeg's time was short, fsync was long, and the reverse. The data-to-disk cost did not disappear; it moved. Exit + fsync was **2.8–7.9 s in every mode**.

*(Earlier wording of this addendum said disk fullness "cannot explain" the gap. The rerun below shows that was too strong: the gap needs both the overwrite pattern and slow storage.)*

### Mechanism (confirmed by the rerun)

When Btrfs truncates an existing file and rewrites it, it starts writeback as the file is closed, similar to ext4's `auto_da_alloc`. That puts disk-write time inside FFmpeg's measured run. Newly created files stay in the page cache until the explicit fsync. In the rerun, overwritten outputs never had more than ~9 MiB dirty during FFmpeg's run; new outputs built up ~235 MiB that fsync then had to write.

### Revisions to this review

- **Issue 1:** both explanations hold, in combination. Storage in that session was slow: the same jobs took 4.5–7.9 s including fsync, against 1.1–1.3 s on the same laptop with 99 GiB free. That is likely because of fullness and/or ~100 GiB of sustained writes; the rerun can't separate the two. The overwrite pattern decided *where* that slow write time showed up, putting it inside FFmpeg's exit time. The conclusion "don't trust the main-matrix wall times" is unchanged.
- **Advice replaced:** the fresh-output 0.7 s measures only when FFmpeg exits, before the data is on disk. It is **not** a realistic per-job time. For capacity planning, use **exit + fsync** (or exit + upload), measured on the target storage. On this laptop that was ~1.1–1.3 s for a ~250 MB output on healthy storage and 3–8 s on the degraded volume. Storage state dominates.
- **Unchanged:** CPU seconds (~0.8–1.0 s per output style), peak RSS (~90 MiB), I/O byte volumes and all correctness conclusions.

### Further caveats

- **Length grid.** The 10-minute and full inputs are 241.9 MB and 248.9 MB, only 3% apart. The "non-monotonic" 10-minute vs full result is noise between two near-identical points. Those two points also dominate the six-point regressions, so the R² values say little.
- **CPU % in the main matrix** is CPU seconds ÷ wall seconds. It falls as I/O waits grow (e.g. 18% at 10 minutes), so it measures waiting, not CPU efficiency.
- **AVI timing errors are probably more than a lip-sync issue.** Video PTS errors of up to ~65 ms are about two frames at 30 fps. On a stream with B-frames, wrong PTS can put frames in the wrong display order, i.e. visible judder, not only an audio/video offset. This is not directly shown, but "needs timestamp repair or re-encode" (issue 5) remains the right production reading, and the defect should not be treated as cosmetic.

### Step 2 results

Paired rerun on the same laptop and Btrfs volume, now with 99 GiB free (58% used), `powersave` governor, FFmpeg 8.1.3. Full-length MP4 → TS and fMP4, new folder vs overwritten folder, 10 repeats each, in seeded random order. All 40 outputs were byte-identical to the original study's. Full write-up: `outputs/hls-overwrite-rerun/report.md`.

| Output | FFmpeg exit s, new / overwrite | Exit + fsync s, new / overwrite | Overwrite − new, exit (paired median) |
|---|---|---|---|
| TS | 0.93 / 1.08 | 1.33 / 1.25 | +0.07 s (slower in 7/10) |
| fMP4 | 0.85 / 0.94 | 1.28 / 1.10 | +0.11 s (slower in 8/10) |

- On healthy storage, overwriting costs only ~0.1 s, matched by ~0.1 extra CPU seconds, so it is kernel work rather than waiting. Total time to durable completion is the same or slightly lower.
- So the original ~3 s overwrite gap needed the slow storage of that session. The mechanism is confirmed by the dirty-page trace; its size was set by storage speed.
- Limits: one laptop, Btrfs only, and the nearly full disk state was not reproduced. CPU seconds in the rerun (~1.0–1.3 s) were higher than in the original session (~0.8–0.9 s) for byte-identical work, for unknown reasons, so compare CPU figures within one session only.
