# Status

## Summary (2026-10-10, 18:45 UTC)

**Blocked: the Apertus 1.5 8B weights are missing.** Your download (`download_models.sh` with your
token) has not started: there is no `hpc/logs/download.log` and no Apertus file on the cluster.
- Everything else is ready on the cluster.
- A watcher on the Mac checks every 30 minutes until about 08:40 UTC.
- When the weights are complete, the smoke test runs, then step 2 on test (plan steps 3 and 5).

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
- The Apertus weights need your token. In the tmux commands from my earlier message, the
  `until … .env-ready` wait now passes at once.

**Next steps**
1. You: start the download (`docs/hpc.md`, step 4). Apertus 8B alone should take about 15 minutes (an
   estimate).
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
