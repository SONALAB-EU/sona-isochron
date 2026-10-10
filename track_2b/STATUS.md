# Status, 2026-10-10 (evening)

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
