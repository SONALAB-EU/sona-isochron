# Technical report — Isochron

Dubbing lines that fit their slot: Apertus 1.5 shortens a translated line to a syllable target without
dropping or adding meaning, guided by a repair loop.

- **Track:** Track 2B — Isochron
- **Event:** Online
- **Team:** **[PLACEHOLDER: team name]** — **[PLACEHOLDER: members]**
- **Demo:** **[PLACEHOLDER: link to the 2-minute demo video]**

Placeholders are marked **[PLACEHOLDER: …]**. Every number below is labelled with its split, its model
and quantisation, and its n. Dev numbers are exploratory; test numbers are final.

## 1. Summary

In dubbing, the translated line must fit the time the original actor speaks (isochrony), so translations
that run long are shortened by hand. We use Apertus 1.5 to shorten a line to a target length in
syllables, a proxy for spoken time, without losing or adding information.

- **The baseline failed a pre-registered go/no-go.** A single prompt to Apertus 1.5 8B (prompt v1, the
  closest of 4 candidates) was asked for 80 % of each line's syllables. It fit within ±10 % in only 40.7 %
  of 150 outputs, where 60 % was required. Among the fitting outputs, the NLI found the meaning kept in
  only 62.3 %, where 80 % was required. Apertus over-shortens, and it mostly drops qualifiers.
- **Our method adds a repair loop.** Each candidate is checked for length (eSpeak NG), meaning (a
  bidirectional NLI) and language. Apertus gets specific feedback, for at most 2 revisions.
- **Pilot (30 German dev sentences, Apertus 8B Q4_K_M; exploratory).** The loop raised fit from 33 % to
  73 %, and fit with every fact kept and nothing added, scored by an independent judge, from 18 % to 50 %.
  It costs 2.5 times the time.
- **German test (Apertus 8B BF16; 347 sentences × 4 levels × 3 seeds).**
  - The loop raised fit from 34.9 % to 64.7 %, a paired +29.8 points [27.2, 32.4].
  - It raised fit & complete from 14.2 % to 38.4 % (+24.3 points [22.2, 26.3]).
- **French test (332 sentences).**
  - Fit rose from 34.4 % to 67.6 % (+33.2 points [30.6, 35.8]).
  - Fit & complete rose from 15.5 % to 44.2 % (+28.6 points [26.4, 30.9]).
- **By level.** In both languages the gain is largest at level 90. At level 60 it is small: +1.6 points
  of fit & complete in German (not distinguishable from zero) and +5.4 in French.

## 2. Architecture

The diagrams are in `docs/architecture.md`.

| Component | What it does | Where it runs |
|-----------|--------------|---------------|
| `isochron.app` (`make run`) | Reads lines, runs the method, writes `output/results.jsonl` and `output/summary.md` | Docker container, CPU |
| Apertus 1.5 | Writes and revises candidates (OpenAI-compatible API, reached only through `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`) | Any endpoint; llama.cpp b11429 (Mac, or the offline container); vLLM on an H100 (HPC) |
| Length check | Syllables from eSpeak NG 1.52.0's IPA output | In the app (CPU) |
| Meaning check | `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, entailment in both directions | In the app (CPU); GPU in the HPC runs |
| Language check | py3langid 0.4.0, restricted to de/en/fr/it | In the app (CPU) |
| Evaluation judge (not part of the method) | Qwen3-14B BF16 (HPC) or Qwen3-8B Q4 (Mac) lists facts and marks each as kept, changed or dropped | Its own server, only after generation |

**Data flow.**
1. The app counts the line's syllables and sets the target T = level % of them.
2. It sends prompt v1 and gets 4 candidates, then checks each one.
3. If the best candidate fails a check, it sends a revision prompt with the feedback, at most twice.
4. It returns the best candidate over all rounds. Every round is logged with its prompt, raw answer and
   checks.

### Target architecture (mandatory)

- **b) Air-gapped.**
  - `make run-offline` runs the whole method with no network.
  - llama.cpp's server runs a local GGUF in a container without network interfaces (`network_mode:
    none`). The app container joins that namespace, so the two reach each other on 127.0.0.1 only.
  - The NLI model and the language identifier are inside the image.
  - We tested this path without Docker: from a fresh clone, under a macOS sandbox that blocks every
    connection except to localhost.
    - The 10 sample lines ran there, and external connections failed.
    - The outputs were identical to a run with the network on.
  - **[PLACEHOLDER: result of `make run-offline` in Docker; Docker was not installed on our development
    machine, so the images have not been built yet]**
- **a) On-premise.**
  - The evaluation ran on HPI's H100 cluster.
  - Apertus ran in the official vLLM container under Slurm, with the weights on the cluster's own storage
    and Hugging Face set to offline at run time (`docs/hpc.md`).
- **External dependencies, by phase.**
  - **Build time** needs the internet: Debian packages; the eSpeak NG and sonic sources (pinned by
    SHA-256); the Python packages of `uv.lock` (hash-checked); torch as its CPU build at the locked
    version (hash-checked); the NLI model (pinned revision); and the base, uv and llama.cpp images (pinned
    by digest).
  - **Run time:** `make run` needs only the LLM endpoint, and `make run-offline` needs nothing.

## 3. Use of Apertus

- **Model:** `swiss-ai/Apertus-v1.5-8B`, revision `a411d838`. The scripts for Apertus 1.5 70B are ready,
  but it has not been run.
- **How it is used:** inference only, as the system under test. Apertus writes and revises every
  candidate. No other model writes text that is scored.
- **Where it runs:**
  - **HPC (final numbers).** The official BF16 weights in the official container
    `swiss-ai/vllm_apertus_1.5_release`, on one H100.
    - vLLM 0.23.1rc1, swiss-ai fork commit `a601a9d`.
    - 60 % of GPU memory, `--max-model-len 8192`, and `--generation-config vllm`, so the model's own
      defaults never mix with ours.
  - **Mac (development, go/no-go, pilot).** llama.cpp b11429 on Metal, running a Q4_K_M GGUF.
    - The GGUF is a text-only conversion of the official weights (`docs/local_llm.md`).
    - llama.cpp cannot convert the official multimodal checkpoint. The conversion copies the text backbone
      bit for bit, but its outputs were never compared with the official model's.
- **Prompts** (versioned in `src/isochron/prompts/`):
  - `shorten_syllables_v1` gives the line, the syllable target and the word equivalent, and asks for 4
    candidates as JSON.
  - `revise_v1` gives the line, the current best candidate and the feedback.
- **Generation:**
  - temperature 0.7, then top_p 0.95, with no top_k or min_p;
  - at most 1,024 new tokens, and thinking off (`enable_thinking: false`);
  - seeds 0, 1 and 2, and round r of an item uses seed + 1000 × r.

## 4. Data

- **FLEURS** (Conneau et al., 2022; CC BY 4.0), revision `70bb2e8`.
  - The English sentences and their German and French reference translations.
  - Dev: 147 German and 137 French. Test: 347 German and 332 French.
  - Its text comes from FLoRes-101 (Goyal et al., 2022; CC BY-SA 4.0), so our data files are CC BY-SA 4.0.
  - The sentences are from public Wikimedia articles and contain no personal data.
  - We store no audio, and no experiment uses it.
- **Splits.** Prompts are tuned on dev only, outside the 50 go/no-go sentences. Test is used for the final
  numbers only.
- **Control pairs.**
  - The NLI suite has 200 pairs: 20 German and 20 French train sentences, each paired with itself, a
    paraphrase, a deletion, an insertion and a negation.
  - The hard judge controls have 140 German pairs:
    - 60 identity pairs and 20 same-meaning edits;
    - 40 single changes of a modal, number or qualifier;
    - 20 inserted facts.
  - The variants were written by Claude, an AI assistant. No native speaker has reviewed them yet.
- **`data/sample_input.jsonl`**: 10 German dev sentences outside the go/no-go 50, the input of `make run`.

## 5. Evaluation

**Task (step 2).** Shorten one sentence in its own language to level % of its syllables, at levels 90,
80, 70 and 60 %, with seeds 0, 1 and 2. Everything was pre-registered in `docs/eval_protocol.md`, and
every later change is in its changelog.

**Metrics.**
- **Fit:** within ±10 % of the syllable target.
- **NLI kept:** entailment in both directions. It is the loop's own check.
- **Fact recall and added-fact rate:** from the final judge, which the loop never sees.
- **Fit & complete:** the output fits, the judge keeps every fact, and it finds nothing added.
- A missing output, or one in the wrong language, counts as a failure.
- **Intervals:** 95 % bootstrap over sentences (10,000 resamples, seed 0). The loop's effect is a paired
  difference.

| Setup | Metric | Result |
|-------|--------|--------|
| **Baseline: go/no-go.** Prompt v1, closest of 4, no loop; 8B Q4_K_M; 50 German dev sentences × 3 seeds; level 80 % | Fit | 40.7 % [31.3, 50.0] (61/150); **NO-GO**, 60 % needed |
| Same | Kept both ways among fits (NLI) | 62.3 % [46.6, 77.0] (38/61); 80 % needed |
| Pilot without the loop. 8B Q4_K_M; 30 German dev sentences; levels 90 and 80; seed 0 | Fit; fit & complete | 33.3 % [20.0, 46.7]; 18.3 % [8.3, 28.3] |
| **Ours** in the pilot (with the loop) | Fit; fit & complete | 73.3 % [61.7, 85.0]; 50.0 % [38.3, 61.7] |
| Step 2, German test, 8B BF16, without the loop. 347 sentences × 4 levels × 3 seeds (4,164 outputs) | Fit; fact recall; fit & complete | 34.9 % [32.5, 37.3]; 59.9 % [57.0, 62.8]; 14.2 % [12.4, 16.1] |
| **Ours**, German test | Same | 64.7 % [62.1, 67.2]; 78.0 % [75.9, 80.0]; 38.4 % [35.7, 41.2] |
| Effect of the loop, German test (paired) | Difference in points [95 % CI] | Fit +29.8 [27.2, 32.4]; fact recall +18.0 [16.0, 20.1]; fit & complete +24.3 [22.2, 26.3] |
| Step 2, French test, 8B BF16, without the loop. 332 sentences × 4 levels × 3 seeds (3,984 outputs) | Fit; fact recall; fit & complete | 34.4 % [31.7, 37.0]; 61.6 % [58.6, 64.7]; 15.5 % [13.5, 17.6] |
| **Ours**, French test | Same | 67.6 % [65.0, 70.2]; 80.2 % [78.0, 82.3]; 44.2 % [41.3, 47.0] |
| Effect of the loop, French test (paired) | Difference in points [95 % CI] | Fit +33.2 [30.6, 35.8]; fact recall +18.5 [16.5, 20.6]; fit & complete +28.6 [26.4, 30.9] |

**Step 2 on test, German and French (`results/step2_test.md`; final numbers).**
- The loop's gain in fit & complete shrinks as the target tightens:

  | Level | German | French |
  |------:|--------|--------|
  | 90 % | +56.7 [52.7, 60.5] | +61.7 [57.9, 65.5] |
  | 80 % | +28.5 [24.9, 32.2] | +32.9 [29.2, 36.6] |
  | 70 % | +10.2 [7.7, 12.8] | +14.5 [11.5, 17.5] |
  | 60 % | +1.6 [−0.6, +3.8] | +5.4 [3.2, 7.6] |

- At 60 %, fit barely moves: −1.5 points [−5.6, +2.5] in German and +4.5 [0.4, 8.6] in French.
  - The loop keeps the meaning instead. In German, NLI kept rises from 52 % to 96 %, and outputs average
    1.08 × the target.
- Without the loop, Apertus over-shortens (0.83 × the target in German and 0.82 in French). With the
  loop, outputs average 1.05 and 1.03 × the target.
- The runs were clean:
  - no output was in the wrong language;
  - none of the 16,296 judge verdicts was invalid;
  - in German, round 0 left 28 items without a usable answer, and the loop left none.
- French answers break JSON more often: 2.9 % of rounds against 0.5 % in German. Most of these are
  apostrophes escaped as `\'`. After the loop, 11 French items (3 sentences) have no usable answer, and
  they count as failures.
- The added-fact rate is about 0 in both conditions.
- An output takes 10.5 s with the loop and 0.7 s for round 0, with 16 items in flight on one H100.

**The baseline (go/no-go, 9 October; `results/gonogo_step2_de.md`).**
- The rule was fixed before any output: GO needs fit ≥ 60 % and kept ≥ 80 % among fits, pooled over 150
  outputs. Both criteria failed, each on its own.
- The result is reported as a null result, and the thresholds stayed as they were.
- Apertus over-shortens: asked for 80 % of the syllables, the chosen outputs average 67 %.
- In 30 NLI-flagged losses, three independent LLM annotators most often found a lost **qualifier** (80 %
  of cases, by majority), then a lost clause (33 %); never a number
  (`results/gonogo_error_analysis.md`).

**The pilot (dev; `results/phase2_pilot.md`).**
- Prompt v1 and three variants (facts first, word target, graded targets) were each run with and without
  the loop. The variants did not help on their own.
- With the loop, all four were within noise of each other. The rule fixed before the judge's output
  picked v1 with the loop.
- Per level, v1's fit & complete rose from 13 % to 67 % at 90 %, and from 23 % to 33 % at 80 %.
- Three outputs came out in English. Since then the loop checks the language, and the reports count a
  wrong-language output as a failure.

**Checking the measures.**
- **Syllables.** eSpeak NG matched hand counts on 46 of 50 items (92 %; the vowel heuristic: 42 %). The
  cluster's build counts all 963 German and French reference sentences exactly as the Mac does.
- **Language check.** It flags none of 1,956 German FLEURS sentences and the 3 English pilot outputs
  (`results/language_check.md`).
- **NLI.** It passes its suite (identity 95 %, paraphrase 95 %, deletion 82 %, insertion 90 %, negation
  100 %). On the hard controls it catches only 3 of 14 qualifier changes.
- **Final judge.** It is validated on both suites before use (`results/judge_validation_*`). On the hard
  controls:

  | Judge | Mean | Qualifier | Modal | Number | Inserted fact | Same meaning |
  |-------|-----:|----------:|------:|-------:|--------------:|-------------:|
  | Qwen3-8B Q4_K_M (Mac) | 78 % | 5/14 | 8/13 | 13/13 | 17/20 | 17/20 |
  | Qwen3-14B BF16 (HPC) | 84 % | 7/14 | 10/13 | 13/13 | 16/20 | 20/20 |

  - A rule fixed before the 14B result made Qwen3-14B the main judge.
  - Paired on the 27 qualifier and modal pairs, the difference is within noise (exact McNemar, p = 0.34).
  - Qwen3-14B scores 99 % on the NLI suite.
- **HPC smoke test** (5 German dev sentences, 2 levels, seed 0, 8B BF16; `results/hpc_8b_step2_de_dev_smoke.md`).
  - Fit with the loop was 7 of 10 (the same items on Q4: 6 of 10).
  - NLI kept was 10 of 10, and none of the 20 judge verdicts was invalid.

**Step 4 (translate to a length budget).**
- The systems are EN → DE and EN → FR:
  - plain translation;
  - one step to the budget;
  - translate, then shorten with our method.
- Each is run under an isometric (characters) and an isosyllabic (syllables × speech-rate ratio)
  budget.
- It is implemented and was smoke-tested on 5 sentences per language (`results/step4_smoke_local.md`).
- **Step 4 on dev (`results/hpc_8b_step4_dev.md`; exploratory).** Apertus 8B BF16, 97 German and 90
  French dev sentences outside the go/no-go 50, × 3 seeds. Fit within ±10 % of the budget:

  | Direction, budget | (a) plain | (b) one step | (c) translate, then shorten (ours) |
  |-------------------|----------:|-------------:|-----------------------------------:|
  | EN → DE, characters | 26.8 % | 58.1 % | 80.1 % [73.9, 85.6] |
  | EN → DE, syllables | 13.4 % | 66.0 % | 69.4 % [62.5, 75.9] |
  | EN → FR, characters | 17.4 % | 67.4 % | 79.3 % [72.6, 85.6] |
  | EN → FR, syllables | 60.7 % | 46.7 % | 74.8 % [66.3, 82.6] |

  - The meaning check here is the NLI against the human reference. (c) keeps meaning about as often as
    plain translation: 79–82 % against 79 % in German, and 75–79 % against 73 % in French.
  - (b) keeps it no better than (c).
  - In German with syllables, (b) and (c) are within noise of each other.
  - Plain French translation already meets the syllable budget 61 % of the time. That budget is
    generous, because French is spoken faster: 1.160 × the English syllables.
  - In French, one-step answers again broke JSON: 15 of the 270 under the character budget have no
    answer.

## 6. Limitations

- **Syllables are a proxy for time.** We have not synthesised speech or measured seconds. Speaking rate,
  pauses and the actor's delivery are outside the method.
- **The meaning checks are weak on small losses.**
  - The NLI misses most dropped qualifiers (3 of 14 caught), and the final judge misses half (7 of 14).
  - So fact recall and fit & complete are upper bounds, and the added-fact rate is likely undercounted.
  - A native-speaker check of a sample of outputs is planned but not done.
- **Unreviewed control pairs.** Claude wrote the variants in both control suites. No native speaker has
  reviewed them.
- **Tight targets can return a long line.**
  - When no candidate both fits and keeps the meaning, the loop prefers meaning over length. It can then
    return the line nearly or entirely unchanged.
  - In the 10 sample lines (Q4, Mac), all 4 misses kept 90–100 % of the line's syllables, and one was
    unchanged. These were at levels 60 and 80 %.
  - The HPC smoke test had one unchanged line among its 10.
  - On German test at level 60 %, the loop does not improve fit (−1.5 points), and outputs average
    1.08 × the target. Misses that are too long outnumber those too short at every level (at 60 %: 321
    against 145, of 1,041).
  - The final output is the input unchanged in 9.4 %, 4.7 %, 3.0 % and 2.0 % of items at levels 90, 80,
    70 and 60 %.
  - Such outputs count as not fitting.
- **French answers break the answer format more often.**
  - Apertus often escapes French apostrophes as `\'` inside its JSON answer, and strict JSON rejects
    that: 215 of the 253 invalid French answers.
  - 11 French test items from 3 sentences ended without a usable answer, counted as failures.
  - A more lenient parser is a fix to tune on dev first.
- **Grammar is not checked.** Some outputs are ungrammatical (for example *"den 18. Jahrhundert Markt"*).
  No check in the loop looks at grammar.
- **Development ran on a derived 4-bit model.** The go/no-go and the pilot used a Q4_K_M text-only
  conversion. Only the final runs use the official BF16 weights.
- **Small dev pilot.** It had n = 30 sentences and one seed, so the variant comparison is
  underpowered.
- **Untested setups.**
  - French is less tuned than German, and Italian is untested.
  - The 70B model has not been run.
- **Docker was not run here.** Docker is not installed on our development machine. The method, the input
  and output, and offline operation were tested from a fresh clone without it. The images themselves
  have not been built yet.
- **Concurrency changes outputs slightly.** HPC runs process 16 items at once. Batching changes the
  arithmetic slightly, so outputs need not match a sequential run token for token.

## 7. Reproducibility

- **Commits.**
  - The step 2 test runs used commit `68492f2`. The cluster copy records it, since it is not a git
    checkout.
  - **[PLACEHOLDER: the commit of the final reports]**
- **Hardware.**
  - Development: an Apple M3 with 16 GB.
  - Final runs: one NVIDIA H100 80 GB per job, on HPI's cluster (driver 590.48.01).
  - Compute: 4.46 H100-hours in total (sacct), out of a budget of 12. That is, each rounded: setup
    and checks 1.22, judge validation 0.23, the smoke test 0.19, German 1.04, French 0.96 and step 4 0.83.
- **Seeds.**
  - Generation uses seeds 0, 1 and 2, plus 1000 × the round for revisions.
  - The judge runs at temperature 0 with seed 0.
  - The bootstrap uses seed 0.
- **Records.** Every results file records its date, git commit, model and quantisation, endpoint,
  backend, TTS (none), seeds and n. Raw runs keep every prompt and answer.
- **Rebuilding the numbers.**
  - Mac: `docs/local_llm.md`.
  - HPC: `docs/hpc.md`, which has the exact `sbatch` lines.
  - The step 2 report: `uv run python -m isochron.step2_report results/raw/hpc_8b_step2_de_test
    results/raw/hpc_8b_step2_fr_test --validation …`.
- **The demo.** `make run`, or `make run-offline` with a GGUF.

## 8. Next steps

- **Seconds instead of syllables.** Synthesise each output with TTS and measure it against the source's
  voice-activity-trimmed slot (the stretch goal).
- **Better meaning checks.**
  - A native-speaker review of the outputs and of both control suites.
  - A meaning check aimed at qualifiers, which both the NLI and the judges miss.
- **Larger and broader runs.**
  - Apertus 1.5 70B on the same test set.
  - Italian.
  - Step 3: does selection or the exact target help?
- **Product.**
  - Read and write subtitle formats (SRT and TTML), so the method fits a dubbing editor's workflow.
  - Flag a line as "cannot fit without losing meaning" instead of returning it unchanged.

## License

Creative Commons Attribution 4.0 (CC-BY-4.0). All HackApertus projects are open-sourced. The code is
Apache-2.0, and the data files are CC BY-SA 4.0 (`docs/licences.md`).

## References

- Anastasopoulos, A. et al. (2022). Findings of the IWSLT 2022 Evaluation Campaign (isometric spoken
  language translation). *Proc. IWSLT 2022.*
- Conneau, A. et al. (2022). FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech.
  arXiv:2205.12446.
- Goyal, N. et al. (2022). The Flores-101 Evaluation Benchmark for Low-Resource and Multilingual Machine
  Translation. *TACL* 10. arXiv:2106.03193.
- He, P., Gao, J. and Chen, W. (2021). DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with
  Gradient-Disentangled Embedding Sharing. arXiv:2111.09543.
- Kwon, W. et al. (2023). Efficient Memory Management for Large Language Model Serving with PagedAttention
  (vLLM). *Proc. SOSP 2023.*
- Lakew, S. M., Virkar, Y., Mathur, P. and Federico, M. (2022). Isometric MT: Neural Machine Translation
  for Automatic Dubbing. *Proc. ICASSP 2022.*
- Laurer, M., van Atteveldt, W., Casas, A. and Welbers, K. (2024). Less Annotating, More Classifying:
  Addressing the Data Scarcity Issue of Supervised Machine Learning with Deep Transfer Learning and
  BERT-NLI. *Political Analysis* 32(1).
- Lui, M. and Baldwin, T. (2012). langid.py: An Off-the-shelf Language Identification Tool. *Proc. ACL
  2012 System Demonstrations.*
- Pellegrino, F., Coupé, C. and Marsico, E. (2011). A cross-language perspective on speech information
  rate. *Language* 87(3).
- Qwen Team (2025). Qwen3 Technical Report. arXiv:2505.09388.
- Swiss AI Initiative (2025). Apertus 1.5 model cards, huggingface.co/swiss-ai/Apertus-v1.5-8B and
  Apertus-v1.5-70B.
- eSpeak NG, github.com/espeak-ng/espeak-ng; llama.cpp, github.com/ggml-org/llama.cpp; py3langid,
  github.com/adbar/py3langid.
