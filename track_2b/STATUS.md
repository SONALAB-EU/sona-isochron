# Status

## The loop round by round (2026-10-12; from the logged runs, no new generation)

- **`isochron.rounds`** reads the logged step 2 test runs and computes, per language and level, fit and
  fit & complete after round 0, 1 and 2.
  - "After round k" is the loop's best candidate so far, the output if the loop stopped there.
  - Results: `results/step2_test_rounds.md` and `.csv`; figure 4 in the report.
  - Round 2 and the round-0 baseline are checked against `results/step2_test.md`, and match exactly.
- **What the logs cannot give exactly.** The judge scored only two texts per item: the closest round-0
  candidate and the final output.
  - After rounds 0 and 1, 357–566 of the loop's best candidates (German) were never scored.
  - Fit & complete there is a range: unscored counts as incomplete, or as complete if it fits. The range is
    at most 0.7 points wide.
  - Fit is exact, because every candidate's length and language are logged.
- **Numbers, all levels pooled:**

  | | Fit after rounds 0 / 1 / 2 | Fit & complete after rounds 0 / 1 / 2 |
  |---|---|---|
  | German | 31.6 / 56.3 / 64.7 % | 13.7 / 34.3–35.0 / 38.4 % |
  | French | 31.6 / 58.1 / 67.6 % | 15.2 / 38.6–39.0 / 44.2 % |

- **Acceptance.** The loop accepted 39 % (German) and 42 % (French) of the open items in round 1, but only
  20 % and 23 % in round 2. At level 60 the rate did not fall (German 12 % → 17 %).
- **Third round, an estimate, not a measurement:** at round 2's rate it would add about +2.8 to +3.3 points
  of fit & complete in German and +4.0 to +4.2 in French. The report's one sentence: likely little help.
- **Figures renumbered** to follow the report: 4 is the rounds, 5 step 4, 6 the judges (not inserted).
  The report is 5 pages (A4, two columns).

## Figures and report layout (2026-10-12)

- **`make figures`** draws 5 figures with matplotlib from committed results files only.
  - It stops if an input is untracked or modified.
  - Output: `docs/figures/figN_*.pdf`, `*.png` and the CSV behind each.
  - Two runs give byte-identical files: no timestamps, and every CSV names its inputs' git blobs.
  - matplotlib 3.11.2 is in a `figures` dependency group, so the Docker image stays without it.
- **One new committed input:** `results/step2_test_lengths.csv`, the length of every step 2 test output
  (16,296 rows, numbers only), from `isochron.lengths_csv`. The histogram needs per-output values, and the
  raw runs are not in git. Its fit shares match `results/step2_test.md` exactly.
- **Style:** Okabe & Ito colours. Without the loop is orange and dashed, with the loop blue and solid, in
  every figure. Each figure is 3.5 in wide with 6.2–8.5 pt text. Every axis has units.
- **Report:** figures 1–4 are in `technical_report.md` with captions. The text is shorter, and the tables
  the figures replace are gone; every number is unchanged.
  - Measured with `uv run scripts/report_pdf.py` (A4, two columns, 9.5 pt; headless Chrome): **4 pages**.
  - As one column with 8.9 cm figures: 5 pages.
  - The judges per control type (now figure 6) are in `docs/figures/`, linked from the report but not inserted.
- **A test** redraws the figures and checks that the committed CSVs hold the same numbers, so a stale
  figure fails the test suite.

## Summary (2026-10-11, 14:55 UTC): every planned job is done

**Done**
- **Smoke test on an H100:** clean on all six criteria, which were fixed before any output (job 2636579).
- **Step 2 on test, German and French:** Apertus 1.5 8B BF16, every test sentence × 4 levels × 3 seeds;
  `results/step2_test.md`.
- **Step 4 on dev (exploratory):** `results/hpc_8b_step4_dev.md`.
- **`make run` and `make run-offline`:** written. Docker is not installed on this Mac, so they have not run
  in Docker. The app was tested from a fresh clone, including under a sandbox that allows only localhost.
- **`README.md` and `technical_report.md`:** filled in. The placeholders left are team, demo, the Docker
  check and the final commit.

**Numbers**

Step 2 on test (final; judge Qwen3-14B BF16), pooled over levels 90 to 60 %:

| Language | Fit, without → with the loop | Fit & complete, without → with | Paired gain (points): fit; fit & complete |
|----------|-----------------------------:|-------------------------------:|-------------------------------------------|
| German (347 sentences) | 34.9 % → 64.7 % | 14.2 % → 38.4 % | +29.8 [27.2, 32.4]; +24.3 [22.2, 26.3] |
| French (332 sentences) | 34.4 % → 67.6 % | 15.5 % → 44.2 % | +33.2 [30.6, 35.8]; +28.6 [26.4, 30.9] |

- Fit & complete gains +57 to +62 points at level 90, and only +1.6 (German) and +5.4 (French) at 60 %.

Step 4 on dev (exploratory; NLI against the reference). Fit for (a) plain / (b) one step / (c) translate,
then shorten:

| Direction | Characters budget | Syllables budget |
|-----------|-------------------|------------------|
| EN → DE | 27 / 58 / 80 % | 13 / 66 / 69 % |
| EN → FR | 17 / 67 / 79 % | 61 / 47 / 75 % |

- (c) keeps the meaning about as often as plain translation.

GPU: 4.46 H100-hours of the 12 used (sacct). No job is queued.

**Decisions** (each with its reason in the logs below)
- Jobs ran as a chain, with a gate after the smoke test.
- French JSON escapes are reported, not fixed: they were found on test.
- The method's selection rule is unchanged, although it returns long lines when nothing fits.
- torch in the container is the CPU build. The offline mode uses `network_mode: none` plus a shared
  namespace.

**Blockers:** none on the cluster.
- Docker is missing on this Mac, so `make run` is untested in Docker.

**Next steps (your call)**
1. Run `make run` and `make run-offline` on a machine with Docker (or install it here), then fill that
   placeholder in the report.
2. Fill in the team, the demo link and the final commit. The report is about 3,800 words and probably
   needs trimming for the 6-page PDF.
3. The 70B run: 7.5 H100-hours are left. `docs/hpc.md` estimates 4–8 GPU-hours for German on two H100s
   (an estimate).
4. A more lenient JSON parser for French apostrophes, tuned on dev.
5. A native-speaker check of outputs and control pairs.

The earlier summary, written while the weights were missing, follows.

**Done**
- Cluster: the environment passes its tests on an H100. The vLLM container is imported and unpacked once.
  Qwen3-14B and the NLI model are downloaded (no token needed).
- Plan step 4: the judge is decided. Qwen3-14B is the main judge.
- Plan step 6: step 4 is implemented, with tests and a local 5-sentence smoke test
  (`results/step4_smoke_local.md`).
- Provenance: `hpc/sync.sh` records the commit of the cluster copy, so results made there report it.
- `docs/hpc.md` describes what was run, with the commands for the smoke test, step 2 and copying back.

**Numbers (each labelled)**
- Judge validation, measured. Qwen3-14B BF16 on vLLM, job 2634364, temperature 0, seed 0:
  - Hard controls (140 pairs): mean 84 %. Qualifier changes caught 7 of 14, modal changes 10 of 13.
  - NLI suite (200 pairs): 99 %.
- Earlier, local: Qwen3-8B Q4_K_M had a mean of 78 % on the hard controls (qualifier 5 of 14, modal 8 of 13).
- The difference between the two judges is within noise: paired McNemar on the 27 qualifier and modal
  pairs, p = 0.34.
- GPU: 1.45 of the 12 H100-hours used (sacct, measured).
- No step 2 test number exists yet.

**Decisions (reasons in the log below)**
- Qwen3-14B is the main judge, by the rule fixed before its result. The NLI stays the loop's screen.
- Time limits: 1.5 h for the smoke test and 8 h for step 2, which keeps the worst case under 12 H100-hours.
- The local insurance run is not started. The HPC works and only the weights are missing. Your plan
  sends that case to step 6 (done), not to the insurance run.
- Not started either: the 70B model.

**Blockers**
- The Apertus weights need your token, and your Hugging Face account must have accepted the terms of
  `swiss-ai/Apertus-v1.5-8B`. These lines start the download so that it survives a logout:

  ```
  ssh hpi-login
  tmux new -s isochron-download
  cd ~/isochron/track_2b
  read -rs HF_TOKEN
  export HF_TOKEN
  { for attempt in 1 2 3 4 5 6 7 8; do srun --account=aisc --partition=pot-hpi-aisc-shortrun --nodes=1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 --job-name=isochron-download bash hpc/download_models.sh && break; sleep 60; done; } 2>&1 | tee -a hpc/logs/download.log; unset HF_TOKEN
  ```

  Then detach with Ctrl-b d, and `exit`.

**Next steps**
1. You: start the download (above, or `docs/hpc.md`, step 4). Apertus 8B alone should take about 15
   minutes (an estimate).
2. Smoke test: 5 German dev sentences, levels 90 and 80, seed 0. Then compare with the local Q4
   outputs (`isochron.compare_runs`).
3. Step 2 on test, German and French: 4 levels × 3 seeds, 8,148 items. Then `results/step2_test.md`
   (`docs/hpc.md`, steps 5 and 9).
4. Your call: the 70B run.

## Autonomous run, 2026-10-10 evening to 2026-10-11 (decision log)

Times are UTC. Each entry: what was decided, and why. Budget: at most 12 H100-hours; the 70B model
is not started. Nothing is pushed.

- **15:07. `setup.sh` through srun failed in `uv sync`, on a 30-s download timeout.**
  - Measured from compute nodes: the internet is throttled per connection and connections stall for
    minutes.
    - PyPI: 0.1–0.6 MB/s per connection.
    - Hugging Face: 0.6–4 MB/s per connection, 34 MB/s with eight.
    - ghcr.io: 0.1–2.9 MB/s per connection.
  - Decision: split setup. A CPU-only batch job does every download and the eSpeak NG build
    (`setup.sh prefetch`); `setup.sh` on an H100 (srun) then only checks and tests.
  - Why: the downloads take longer than shortrun's hour, and a CPU-only job does not hold a GPU idle.
- **15:44. A pyxis pull of the vLLM image (8.9 GB) did not finish in its hour, so I cancelled it.**
  - Large layers stalled and restarted from zero.
  - Decision: fetch the image's layers in ranged chunks in parallel, each checked against its digest,
    into enroot's cache; `enroot import` then only builds the squashfs.
  - Why: ghcr.io and its CDN serve ranges (HTTP 206), and a stalled chunk costs 32 MB, not a whole
    layer.
- **16:40. `uv sync` restarted each large wheel about ten times without finishing one.**
  - Decision: fetch the 16 locked Linux wheels over 20 MB (3.1 GB) the same way, checked against
    `uv.lock`'s hashes. They are installed from those files, and the rest of the lock is installed with
    `uv pip` from `uv export` (hash-checked).
  - Versions and hashes stay exactly those of `uv.lock`; torch still comes from PyPI.
  - Why: uv cannot resume a download.
  - Checked locally: a preinstalled wheel is left alone by a hash-checked install ("Checked 1 package").
- **16:00. Your model download** waits in your tmux session for `~/isochron_work/.env-ready`.
  - `setup.sh prefetch` writes that marker when the environment is complete.
  - It runs through srun, not sbatch, because Slurm stores a batch job's environment, token included.
- **The 70B weights** get their own location (`ISOCHRON_MODELS_70B`): home has a 200 GB quota. Unused
  tonight.
- **16:53. The downloader's range probe treated a transient 403 or timeout as "no range support"** and fell
  back to one stream, which restarts from zero on every stall.
  - Decision: probe up to 5 times with a fresh token, and fall back to one stream only on a plain HTTP 200.
  - Both jobs were restarted. Finished files and chunks are kept.
- **Step 4 (plan step 6), done while the GPUs waited for the environment.**
  - Built: runner (`isochron.step4`), report (`isochron.step4_report`), tests, and a 5-sentence local smoke
    test per language (`results/step4_smoke_local.md`).
  - (b) and (c) use the closest of 4 candidates, because step 3 has not been run.
  - (c) shortens with v1 and the repair loop, in the budget's unit; the loop now takes a unit.
  - These choices are recorded in protocol v2.10.

- **16:57. Judge selection rule, fixed before any Qwen3-14B result** (plan step 4).
  - Basis: the hard controls, all 140 pairs. Qwen3-8B caught 13 of the 27 qualifier and modal changes
    (qualifier 5 of 14, modal 8 of 13).
  - Qwen3-14B becomes the main judge if it catches more than 13 of those 27 and is not lower in either
    category.
  - Otherwise both judges are reported side by side.
  - The NLI stays the loop's screen in every case.
- **Retry counting** ("retry a failing step at most twice"): only runs that failed on their own count;
  restarts to install a fix do not.
  - So far one failure each: the env setup (uv timeout, job 2634033) and the container import
    (manifest timeout, job 2634227).

- **17:22. The container image is imported** (16.8 GB squashfs).
  - Every layer was fetched in chunks and checked against its digest, then `enroot import`.
- **17:27. The prefetch job died with "Stale file handle".** My own rsync of a fixed `setup.sh` replaced the
  file while bash was still reading it.
  - The environment was already installed; only the eSpeak NG build and the marker were left.
  - Decision: `setup.sh` and `pipeline.sh` now run everything from `main` with a single last line,
    `main "$@"; exit`, so bash reads the whole file before running. A sync can no longer break a job.
  - Not counted as a failure of the step: the cause was my sync.
  - The H100 run of `setup.sh` (job 2634300) finishes the rest.

- **17:35. Your model download had not started** (no `hpc/logs/download.log`, no tmux session on lx01).
  - Decision: download what needs no token myself. `download_models.sh --open` fetches the judge Qwen3-14B
    and the NLI model (job 2634301, CPU-only, submitted with `HF_TOKEN` removed from the environment).
  - Your command still fetches everything; files already present are skipped, and huggingface_hub locks
    each file if both run at once.
  - Why: the judge validation (plan step 4) needs no Apertus weights, so it can run before they arrive.

- **17:51. Setup on an H100 passed** (job 2634300).
  - torch 2.14.1+cu130 sees the H100 (driver 590.48.01).
  - Tests: 115 pass and 4 skip (those need models). The syllable reference test passed: the cluster
    counts syllables exactly as the Mac does on all 963 sentences.
  - The marker `.env-ready` is written.
- **17:55. pyxis runs the imported image** (job 2634285): vLLM 0.23.1rc1 (swiss-ai fork `a601a9d`),
  torch 2.11.0+cu130 (H100 visible), transformers fork 5.14.0.dev0.
  - But pyxis first unpacked the image to `~/.local/share/enroot` (12 GB on the network share) and
    removed it afterwards, which held the GPU for about 20 minutes.
  - Decision: the vLLM container gets a name (`--container-name`). With `container_scope=global` it is
    unpacked once, in a CPU-only job, and reused by every later job.
- **GPU budget so far: 1.17 H100-hours** (sacct; tests, setup, the container check).

- **18:06. The ungated models are on the cluster.** Qwen3-14B (29.6 GB) and the NLI model took 23 min
  (job 2634301, CPU-only).
- **18:17. The named vLLM container exists** (`pyxis_isochron_vllm_apertus_1.5`, 19 GB in
  `~/.local/share/enroot`; 11 min, CPU-only, job 2634347).
- **18:17. Judge validation submitted** (job 2634364): Qwen3-14B BF16 on the hard controls and the NLI
  suite. The selection rule above decides from its result.

- **18:23. Decision: Qwen3-14B is the main judge** (plan step 4; job 2634364, BF16 on vLLM).
  - Measured on the hard controls, all 140 pairs: it caught 17 of the 27 qualifier and modal changes.
    Qualifier: 7 of 14 (Qwen3-8B: 5). Modal: 10 of 13 (Qwen3-8B: 8).
  - That passes the rule fixed at 16:57 (more than 13, and not lower in either category).
  - The other control types, against Qwen3-8B:

    | Control type | Qwen3-14B | Qwen3-8B |
    |--------------|----------:|---------:|
    | Same meaning, judged complete | 20/20 | 17/20 |
    | Number change caught | 13/13 | 13/13 |
    | Inserted fact caught | 16/20 | 17/20 |
    | Identity | 60/60 | 60/60 |
    | Mean over the 6 types | 84 % | 78 % |

  - NLI suite (200 pairs, DE and FR), Qwen3-14B: mean 99 %. Identity 100 %, paraphrase 98 %, deletion
    98 %, insertion 100 %, negation 100 %.
  - Caveats:
    - The difference is within noise. Paired on the same 27 pairs, the 14B judge alone caught 7 and the 8B
      judge alone caught 3; both caught 10 (exact McNemar, two-sided p = 0.34). The rule decides the main
      judge; it does not show that the 14B judge is better.
    - The two judges differ in size and also in quantisation and backend (8B: Q4_K_M on llama.cpp; 14B:
      BF16 on vLLM), so this does not isolate model size.
    - The 14B judge still misses half the qualifier changes. A "complete" verdict does not rule out a
      dropped qualifier.
  - The NLI stays the loop's screen.
  - Files: `results/judge_validation_{hard,nli}_v3_qwen3-14b_hpc_8b.md`.
- **18:30. Provenance of results made on the cluster.**
  - Both validation files said "Git commit: unknown", because the cluster copy is an rsync, not a git
    checkout.
  - I checked with `rsync --checksum` that every synced file equals commit 5820d9d (the code is unchanged
    since 1f71399), and wrote that into both files by hand, marked as added by hand.
  - Decision: `hpc/sync.sh` now copies the code and records the commit in `.git_commit` on the cluster, and
    `isochron.provenance` reports it there. The Apertus runs then record their commit themselves.
  - Also: `setup.sh container` now creates the named container itself (before, the one-off job 2634347
    did), so the runbook reproduces the setup.
- **18:34. GPU budget: 1.45 H100-hours used** (sacct, elapsed × H100s), so 10.55 are left.
  - 1.22 before the judge validation, then 0.23 for it (13.6 min: 11 min server start, 2 min judging).
  - Plan: the smoke test runs with a 1.5 h limit and the full step 2 with 8 h. Even if both run to their
    limits, the total stays at or under 10.95.
- **18:28. Your Apertus download has not started** (no `hpc/logs/download.log`, no Apertus files).
  - The environment marker exists, so your command would start at once.
  - Decision: check every 30 minutes until about 08:40 UTC. The smoke test and step 2 follow as soon as
    the weights are complete.
  - Decision: the local insurance run stays off. The HPC has not failed; only the weights are missing.
    Your plan sends "the weights never arrive" to step 6, which is done. The insurance run would also
    cover only a subset: German, levels 90 and 80, seed 0, Q4, about 5 h. The HPC job covers all of it
    in an estimated 3–4 h once the weights are there.
- **18:36. Checked on a compute node** (CPU-only, 1 min, job 2634436): `setup.sh container` finds the
  image and the named container. `isochron.provenance` reports the synced commit
  (`934a808… (synced copy, recorded by hpc/sync.sh)`).
- **Smoke test settings** (decided now, run when the weights arrive): phases generate, judge and
  report.
  - No validate phase: it already ran in job 2634364, and the full run repeats it.
  - Only the files a job writes are copied back, so a local results file can never be overwritten by an
    older cluster copy.
- **18:40. The step 2 report gets the loop's effect as a paired difference** (protocol v2.12, commit
  bf8f429).
  - What it shows: with − without, in points, for fit, fact recall, added-fact rate and fit & complete,
    pooled and per level. The interval comes from a paired bootstrap over sentences.
  - Why: the pilot's open item. Two overlapping per-condition intervals do not show whether the loop
    helps; the paired interval does. It is added before any test output exists, so it cannot be fitted to
    the results.
  - Checked: the pilot tables regenerate identically. A mock run in the current format goes through
    `isochron.compare_runs`, so the smoke comparison is ready.
- **08:37 (11 October). The weights never arrived.**
  - 29 checks from 18:37 to 08:37 all reached the cluster. None found a download log, an Apertus file or
    a download job.
  - No GPU was used overnight. The total is still 1.45 H100-hours (sacct); the only job since 18:36 is a
    1-second CPU-only check.
  - Decision: following your plan ("if the weights never arrive, skip to step 6"), nothing else ran on the
    cluster. Step 6 was already done. The insurance run stays off, because the HPC has not failed.
  - Decision: a new watcher checks every 15 minutes until about 20:40 UTC. If your download completes,
    the smoke test runs first, and step 2 is submitted only if the smoke test is clean.
  - Why keep watching: you are back today. Your plan already covers what follows the download, so it
    can start without another round trip.

## Second autonomous run, from 2026-10-11 11:08 UTC (decision log)

Your instruction: the smoke test now, then step 2 on test (German, then French) only if the smoke test is
clean, then step 4 on dev. Same rules: at most 12 H100-hours in total, no 70B, commit locally only, no
workflows. Ultracode mode was switched on in this session, but your rules say no workflows, so I run none.

- **11:08. The weights are verified.**
  - All 17 files of `swiss-ai/Apertus-v1.5-8B` carry the pinned revision a411d838 in their download
    metadata.
  - All 6 shards in the index are present (18 GB), with no partial files.
- **11:08. Smoke test submitted** (job 2636579, 1.5 h limit; phases generate, judge, report).
  - It waits for a GPU: all 60 H100s on the cluster are busy. The earliest scheduled end is about 14:30
    UTC, though jobs often end early.
  - For a single H100 we are first in line. The jobs ahead need 4–8 GPUs on one node or are held by
    per-user limits.
- **11:17. Decision: chain the jobs with dependencies instead of submitting each one after the last.**
  - Why: with every H100 busy, a job submitted after its predecessor ends queues again for hours.
    With `--dependency=afterok`, it can take the GPU the previous job frees.
  - The chain: smoke → step 2 German test → step 2 French test → step 4 dev.
  - **A gate keeps "only if the smoke test is clean".** The German job starts Apertus (about 11 min),
    then waits for `hpc/gates/step2_test.go`, created by me only after I have checked the smoke test, or
    for `hpc/gates/step2_test.go.stop`.
    - It waits at most 45 min.
    - Stopping fails the job, so the jobs after it never start.
    - No test sentence is generated before the gate opens.
  - Time limits: smoke 1.5 h, German 4 h, French 3.5 h, step 4 1.5 h. With the 1.45 H100-hours already
    used, the worst case (every job runs to its limit) is 11.95 H100-hours.
  - Estimates, not measurements: German about 2.5 h, French about 2.5 h, step 4 about 1 h.
  - Submitted at 11:17: German 2636592 (gated), French 2636593, step 4 2636594, each `afterok` on the
    one before.
- **11:17. Step 4 on dev: what runs.**
  - German and French dev, without the 50 go/no-go sentences (as the pilot and the local step 4 smoke
    test). Seeds 0, 1, 2; both budgets; Apertus 8B BF16; NLI scoring; no judge.
  - Checked on a cluster CPU node (job 2636588): the step 4 tests pass there, including a dry run, and
    eSpeak NG's `en-us` voice (needed for English syllables) works.
- **11:17. The smoke test counts as clean only if all of these hold** (fixed now, before any output):
  1. The job completes, with the generate, judge and report phases and no traceback in its log.
  2. Of the 10 items (5 sentences × 2 levels), at most 1 final output (with the loop) is missing or in
     the wrong language, and at most 1 round-0 output.
  3. At most 1 of the 20 judge verdicts is invalid.
  4. Fit with the loop is at least 3 of 10. On the same items the local Q4 run fits 6 of 10, and if
     the true rate were 0.6, 2 of 10 or fewer would happen about 1 % of the time.
  5. The run's `config.json` records the model, BF16, the vLLM backend and version, the endpoint, the
     commit (synced copy), the seed and n.
  6. Reading the 10 final outputs, they are German shortenings of their sources.
  - If any fails, I stop at the gate, find the cause, fix it and retry, at most twice.
- **11:41. The smoke test is clean, so I opened the gate at 11:41:40** (job 2636579 ran 11:28:54–11:40:25 on
  gx07: 691 s, 0.19 H100-hours, sacct).
  1. Pass: generate, judge and report all ran, with no traceback.
  2. Pass: 0 of 10 outputs are missing or in the wrong language, after the loop and at round 0.
  3. Pass: 0 of 20 judge verdicts are invalid.
  4. Pass: fit with the loop is 7 of 10.
  5. Pass: `config.json` records apertus-v1.5-8b-bf16, BF16, vLLM 0.23.1rc1 (swiss-ai fork a601a9d99),
     the endpoint, commit 68492f2 (synced copy), seed 0, n = 5 sentences.
  6. Pass, with one exception noted here. All 10 final outputs are German and come from their sources,
     and 9 are shorter.
     - The exception: for 1528 at level 80 the final output is the source sentence unchanged (24
       syllables for a target of 19).
     - No candidate both fit and kept the meaning, so the loop kept the closest candidate that kept it,
       and that was the source. The scores count it as a miss, as the method intends. It is not a setup
       fault.
  - Quality notes, which reflect the model, not the setup:
    - 1525 has grammar errors: "Der 18. Jahrhundert Markt", "mediterranes Europa-Stimmung".
    - 1528 at level 90 drops the qualifier "Manche", and the NLI still calls it kept.
  - The same 10 items against the local Q4 pilot (`results/hpc_smoke_vs_local.md`; a smoke test, not a
    measurement):
    - Fit without the loop: 4 (Q4) and 3 (BF16) of 10. With the loop: 6 and 7.
    - NLI kept with the loop: 9 and 10.
  - Timing: Apertus was healthy after 420 s, the 10 items took under a minute with 8 workers, and the
    judge was healthy after 210 s.
  - The German job 2636592 started at 11:40:28 on the GPU the smoke test freed. The gate opened before its
    server was healthy, so it did not wait.
  - GPU so far: 1.45 + 0.19 = 1.64 H100-hours. Worst case with the remaining limits (4 + 3.5 + 1.5 h):
    10.64.

- **12:42. Step 2 on German test is complete** (job 2636592: 3,726 s, 1.04 H100-hours).
  - The gate opened after about 0 s, because it was already open when Apertus became healthy (11:45:29).
  - Generation: 4,164 items with 16 workers, from 11:45 to about 12:33.
  - The judge server was healthy at 12:37. Validation and judging ran from the judge cache and new requests,
    and finished at 12:42.
  - Checks: 4,164 items and 4,164 verdicts, 0 invalid verdicts, 0 wrong-language outputs. 28 round-0 items
    had no answer; after the loop, none.
  - The validate phase re-ran both judge suites. Its tables, mean, invalid count and n are identical to
    job 2634364's, served from the judge cache. The committed validation files stay as they are.
  - Report: `results/step2_test.md` (German; French pending), with a hand-written summary in
    `results/step2_test_notes.md`. It was generated from commit 837e380, after a fix: the judge-validation
    tables had included a stray header row of the next table.
  - Also copied back: the job log, the server logs and the cluster's own report
    (`results/hpc_8b_step2_de_test.md`).
- **12:44. French (job 2636593) waits for resources.** No H100 was free when the German job ended, so it
  could not take that GPU. It starts when one frees up; I do not touch it.

- **13:57. Step 2 on French test is complete** (job 2636593: 12:59:52–13:57:20, 3,448 s, 0.96 H100-hours).
  - It waited 17 min for a free H100.
  - 3,984 items and 3,984 verdicts, 0 invalid verdicts, 0 wrong-language outputs.
  - Without the loop, 89 round-0 items had no usable answer; with the loop, 11 still have none (3
    sentences).
  - The cause is invalid JSON: 2.9 % of French rounds against 0.5 % of German. 215 of the 253 are
    apostrophes escaped as `\'`, which strict JSON rejects.
  - Decision: report it as a limitation and do not change the parser. It was found on test, and a fix must
    be tuned on dev before any use.
  - `results/step2_test.md` was generated again with both languages (commit 7bce3a4). The header now lists
    every run's endpoint and judge endpoint.
- **13:57. Step 4 on dev** (job 2636594) took the GPU the French job freed.

- **14:47. Step 4 on dev is complete** (job 2636594: 13:57:21–14:47:09, 2,988 s, 0.83 H100-hours).
  - 561 items (291 German, 270 French), with no traceback.
  - The report was written on the cluster, with commit 68492f2 recorded.
  - (c), translate then shorten, has the highest fit in all four settings. Its meaning check against the
    reference is level with plain translation.
  - French one-step answers broke JSON again: 15 of 270 have no answer under the character budget.
- **14:50. Every planned job is done.** The total is 4.46 H100-hours (sacct), of a budget of 12. The 70B was
  not started.

## Local work while the H100 jobs run (your second message on 11 October)

Tasks: `make run` and `make run-offline`, `README.md` and `technical_report.md`. I did not touch the cluster
jobs, apart from the gate, and synced nothing: the cluster stays at commit 68492f2.

- **Docker is not installed on this Mac** (no `docker`, Docker Desktop, OrbStack, Colima or Podman). As
  you asked, I wrote the files and did not build the images. Here is what I tested instead.
  - Static checks:
    - Both compose files are valid against the official Compose schema (compose-spec commit 914ec15).
    - The Dockerfile passes hadolint 2.15.1, with two ignores whose reasons are in the file.
    - Every pin exists, checked against the registries: the base, uv and llama.cpp images by digest
      (each built for amd64 and arm64), and the two CPU wheels of torch by their hashes on the PyTorch
      index.
  - From a fresh clone (commit a7d8e97):
    - Without Docker, `make run` and `make run-offline` stop with a clear message, and `make -n` shows the
      commands they would run.
    - The app (`uv run python -m isochron.app`) ran on the 10 sample lines against llama-server b11429,
      with Q4_K_M and an API key required. Fit was 6 of 10 (4 at round 0), NLI kept 9 of 10, at 19.4 s
      per line.
  - Offline: the same run under a macOS sandbox that allows connections to localhost only, with Hugging
    Face offline.
    - An external connection fails there (the DNS lookup is refused), and the app still ran.
    - All 10 outputs and their checks are identical to the first run's. Only the times differ.
  - llama-server is stopped, and the temporary key is deleted.
- **Decisions.**
  - **torch in the image is the locked version (2.14.1) as its CPU build,** hash-pinned for amd64 and
    arm64. Every other package comes from `uv.lock`, hash-checked.
    - Why: the container runs the NLI on the CPU. The lock's Linux build of torch is the CUDA build, which
      adds about 3 GB of NVIDIA libraries.
    - A test (`tests/test_app.py`) fails if the Dockerfile's torch version ever drifts from the lock.
  - **Offline networking.** llama-server runs with `network_mode: none`, and the app joins its network
    namespace.
    - Why: neither container has a network interface besides loopback, and the two still talk over
      127.0.0.1. That is "networking disabled" in the strict sense.
    - The address `http://127.0.0.1:8080/v1` is written once, in `docker-compose.offline.yml`, next to the
      server's port. There is no API key in any file: the Makefile makes a fresh random one for each run.
  - **The NLI model is built into the image** at its pinned revision, so nothing is downloaded at run time.
  - **The app calls the experiments' own runner** (`isochron.loop_run.run`, variant v1, seed 0). So
    `make run` is exactly the method we evaluate, with the same logs and provenance.
  - **Sample input:** the first 10 German dev sentences in file order outside the go/no-go 50, at levels
    90, 80, 70 and 60 % in turn (`isochron.data.build_sample_input`).
  - **The container's commit:** the Makefile passes the host's commit in `ISOCHRON_GIT_COMMIT`, and the
    summary records it.
  - **Not changed: the selection rule.**
    - In the sample, all 4 misses kept 90–100 % of the line's syllables, and one is the line unchanged.
      When nothing fits and keeps the meaning, the loop prefers meaning.
    - The test runs use this rule, so it stays. It is listed as a limitation in the report.
- **A slip, fixed.** Commit 9764177 went in with one test failing: `test_data_files` had no schema for the
  new sample file, and pytest's exit status was lost in a pipe. The next commit (a7d8e97) fixed it, and
  all 128 tests pass.
- **README.md** is rewritten: what it does, how to run it, input and output, licences.
- **technical_report.md** has every template section filled. Test results, team, demo, the Docker check
  and the final commit are marked **[PLACEHOLDER: …]**. `docs/architecture.md` has the diagrams.

## Previous status (2026-10-10, before the autonomous run)


**Done, not blocked.** All four tasks of this round are committed locally; nothing was pushed. Nothing has
run on the cluster, and the local insurance run has not been started. No llama-server is running.

- **Method (decided):** prompt v1 with the repair loop; v2a is dropped.
- **Provenance of the figures below:**
  - Pilot: Apertus 1.5 8B Q4_K_M under llama.cpp b11429; judge Qwen3-8B Q4_K_M.
  - TTS: none. Seed 0. n = 30 German dev sentences × 2 levels.
  - Endpoints and commits are in each results file's header.

## 1. Language check in the loop

- **Rule.** py3langid 0.4.0 (BSD-3-Clause, checked in the wheel), restricted to de/en/fr/it. A candidate is
  in the wrong language when another of these languages is the top label with probability ≥ 0.9.
- **In the loop.** A wrong-language candidate ranks last and is never accepted. If it is the best candidate,
  the only feedback is "It is not in German. Answer in German."
- **In scoring.** A wrong-language output counts as a failure, like a missing output.
- **Validation** (`results/language_check.md`, chosen on train and dev). It flags exactly the 3 English
  pilot outputs among 2,643, and 0 of 1,956 whole German sentences.
- **Pilot re-scored** (`results/phase2_pilot.md`):

| Variant | Repair loop | Fit ±10 % | Fact recall | Fit & complete | Time / output |
|---------|-------------|----------:|------------:|---------------:|--------------:|
| v1  | without | 33.3 | 59.9 | 18.3 [8.3, 28.3] | 6.2 s |
| v1  | with    | 73.3 (was 75.0) | 83.4 | **50.0 [38.3, 61.7]** | 15.6 s |
| v2b | with    | 56.7 (was 60.0) | 83.7 | 41.7 [30.0, 53.3] | 17.0 s |
| v2c | with    | 63.3 | 91.1 | 48.3 [35.0, 63.3] | 16.6 s |

  The other rows are unchanged. Fit & complete and the recommendation do not change.

## 2. Hard judge controls

- **The file.** `data/judge_controls_de.jsonl` has 60 German FLEURS train sentences in a seeded order.
  - 40 have one modal, number or qualifier change, as in your examples (*fünftes → fünf*, *soll → ist*,
    *fast alle → alle*, a dropped *zudem*).
  - 20 have one inserted fact.
- **Additions of mine:**
  - 20 same-meaning edits and 60 identity pairs. Without them, a judge that calls everything "changed"
    would look perfect.
  - The edits were written by Claude; no native speaker has reviewed them yet.
- **Validation.** `judge controls --suite hard` validates any judge.
- **Measured on the current judge** (Qwen3-8B, `results/judge_validation_hard_v3_all.md`):

| Control | Qwen3-8B | NLI |
|---------|---------:|----:|
| identity | 100 % | 92 % |
| same meaning | 85 % | 90 % |
| modal changed | 62 % | 77 % |
| number changed | 100 % | 92 % |
| qualifier changed | 36 % | 21 % |
| fact inserted | 85 % | 100 % |

## 3. HPC kit (scripts only, not run)

- **Files.** `hpc/` and the runbook `docs/hpc.md`, which lists every command in order with no inline `#`
  comments.
  - `sync_include.txt` with the rsync commands for both directions.
  - `setup.sh`, `download_models.sh`, `run.sbatch` (8B BF16, one H100) and `run_70b.sbatch` (70B BF16, two
    H100s, tensor parallelism 2).
  - Helpers: `pipeline.sh`, `env.sh`, `lib.sh`, and `hf_server.py` (the transformers fallback).
- **What a job does.**
  1. It starts vLLM (the official container, via pyxis) on localhost with a random port and key, and
     waits for `/health`.
  2. It runs step 2 on German test (4 levels × 3 seeds = 4,164 items), then stops the server.
  3. It starts Qwen3-14B (Apache-2.0, checked), validates it on both control suites, judges the same
     outputs, and writes the reports.
  - Everything resumes.
- **Estimated GPU-hours:**
  - 8B: about 1–2.
  - 70B: about 4–8.
  - Setup and downloads: 1–2.
- **Checked here:**
  - bash syntax and ShellCheck: clean.
  - The rsync allowlist, as a dry run: no `.env`, raw results or caches.
  - The eSpeak NG CMake build: identical syllable counts on all 963 DE/FR sentences. A test now guards
    this on the cluster.
  - The fallback server, with our client: auth, seeds, `backend_info`.
  - The server start, health and stop helpers, the loop runner and the judge, end to end with llama.cpp.
- **Not checked, because only the cluster can:**
  - the GPU type name for `--gres`;
  - network access from compute nodes;
  - a C compiler on the nodes;
  - the container under pyxis;
  - whether 70B BF16 fits two H100s with the NLI beside it.
  - `docs/hpc.md` says what to do in each case.

## 4. Insurance run (not started)

- **Script.** `scripts/local_step2_de_test.sh`: German test, levels 90 and 80, seed 0, with the local llama.cpp
  setup.
  - It is resumable, and runs generate, judge and report, alone or together.
  - It starts and stops both servers itself, never both at once.
  - It was checked on one dev sentence outside the go/no-go 50, including resuming.
- **Estimated duration on this M3:** about 5 h. Generation is about 3.0 h (694 items at 15.6 s); judging
  is about 2.1 h (1,388 outputs at about 5.4 s).

## Choices I made without asking

- **Language check.**
  - It uses py3langid rather than our own n-gram identifier, which knows only four languages.
  - It is restricted to four languages, with a 0.9 threshold. Without them, German sentences led by a
    foreign name were flagged.
  - The without-loop baseline still picks the closest candidate; scoring then fails it if it is in the
    wrong language.
- **Hard controls.** The same-meaning and identity positives described above.
- **HPC defaults.**
  - Languages: German only, with French optional, because the method was piloted on German.
  - Generation: `--generation-config vllm`, `--max-model-len 8192`, 16 items in flight.
  - Judge cache: one per job, the 70B job starting from the 8B job's cache, so both use the same fact
    lists.
  - 70B: 92 % of GPU memory for vLLM, with the NLI on the GPU.
- **Fallback.** The transformers fork is installed from GitHub's archive of the model card's commit, so no
  git is needed.

## Next steps (your call)

1. Run the HPC kit (`docs/hpc.md`, steps 1–9); first check the GPU type name with `sinfo`.
2. Read the Qwen3-14B hard-control result before trusting any meaning figure from the full runs.
3. If the HPC fails: `bash scripts/local_step2_de_test.sh` (about 5 h).
4. Still open: a native-speaker check of the hard controls, and the 50-line native-speaker check.

## Commits since the last status

`1aae5c8`, `f981ca6`, `9978737` and the one that adds this file.
