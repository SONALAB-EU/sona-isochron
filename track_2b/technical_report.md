# SONA Isochron: dubbing lines that fit their slot, with Apertus 1.5

Dubbed lines must fit the time the original actor speaks. SONA Isochron translates English lines into German or French with Apertus 1.5 and shortens those that run long, aiming to keep their meaning.

- **Track:** Track 2B, own project
- **Event:** Hack Apertus 2026, online
- **Team:** SONALAB (Kaushik Mukherjee, Sören Hübner)
- **Demo:** [isochron_demo.mp4 (1:59)](docs/isochron_demo.mp4)
- **Code:** <https://github.com/SONALAB-EU/sona-isochron> · **Data:** <https://huggingface.co/datasets/sonalab/sona-isochron>
- **PDF:** `SONALAB_Report.pdf`

## 1. Summary

**The problem.** A dubbed line has to fit the time the original actor speaks (isochrony). From English into German and French, the two pairs SONALAB currently focuses on, translations come out longer. On the FLEURS test set, the professional German translations have a median of 22 % more syllables than the English, the French ones 15 % (measured after the test runs). Apertus’s own translations add nearly as much: 19 % (German) and 12 % (French). Voice actors rarely make up for this by speaking faster: in professional English-to-German dubs, they kept their pace and missed the timing instead (Brannon et al., 2023). So the line itself has to get shorter without losing its meaning, which dialogue adapters now do by hand.

**What we built.** SONA Isochron translates first, then shortens with a **repair loop** (Figure 1): Apertus 1.5 (Swiss AI Initiative, 2026) proposes 4 candidates, the app checks each for length, meaning and language, and Apertus revises with specific feedback, at most twice. Length counts characters or syllables. An NLI model checks meaning: each version must imply the other.

**How we tested it.** The translation task (step 4 in the repo) translates FLEURS English into German and French within a budget and compares three systems: (a) plain translation; (b) one step straight to the budget, as in isometric MT (Lakew et al., 2022); (c) ours: translate, then shorten with the loop. The shortening task (step 2) shortens German and French sentences in their own language, with and without the loop. Dev numbers are exploratory, test numbers final. “Post-hoc” marks analyses added after the test outputs existed.

**Key results** (translation task on the FLEURS test set; Apertus 1.5 8B, BF16; 347 German and 332 French sentences × 3 seeds; ranges over 2 languages × 2 budgets):

| Result | (a) plain | (b) one step | (c) ours |
| :--- | :---: | :---: | :---: |
| Fit within ±10 % of the budget (%, pre-registered) | 19.6–55.6 | 44.7–71.6 | 69.9–80.2 |
| Too long, over +10 % (%, post-hoc) | 20.5–79.1 | 1.4–14.8 | 4.1–20.4 |
| Meaning kept vs reference, main NLI (%, pre-registered) | 79.5–79.7 | 69.7–76.8 | 80.6–81.6 |
| Meaning kept vs reference, second NLI (%, post-hoc) | 88.2 | 75.4–81.6 | 82.9–87.7 |

- **Fit:** ours fits most often in three of the four settings and ties with one step on the German syllable budget. One step overruns least because it over-shortens, but it keeps meaning less often than ours (all four settings, both NLIs).
- **Meaning:** by the pre-registered NLI, ours keeps meaning as often as plain translation. A second NLI, which the loop never sees, puts ours 0.5–5.3 points below plain (post-hoc).
- **Timing:** syllables predict seconds for one voice (r = 0.98) but not across human readers (κ −0.16 to +0.02), so the budget must be calibrated to the target voice. With a budget calibrated to the voice, ours fits 47 of 99 test lines, plain 25.
- **Cost and deployment:** ours costs 2.40 LLM calls and about 0.47–0.65 H100-seconds per line, plus 5.77 s of checks. It runs against any LLM endpoint (`make run`) or fully offline with a 4-bit model on a CPU (`make run-offline`), and each line is handled on its own.
- **Caveats:** every meaning check misses at least half of the planted qualifier changes (Section 6); the main NLI is the loop’s own model; one native speaker rated 25 lines.

## 2. Architecture

![Figure 1: the engine, offline](docs/figures/fig1_pipeline.png)

*Figure 1. The engine, offline (`make run-offline`). The app asks Apertus for 4 candidates per prompt, checks each and, if the best fails, sends a revision prompt with feedback, at most twice (blue; not drawn: while no candidate exists, the first prompt again). The two containers share only the loopback. The figure shows the shortening task; in the translation task the loop starts from the plain translation, T is the budget, and the NLI checks against that translation.*

The app (`isochron.app`) runs the engine, the repair loop (Figure 1), against an LLM endpoint (`make run`) or a local model (`make run-offline`), and reaches Apertus only through three `LLM_*` settings. Each candidate gets three checks. **Length:** syllables from eSpeak NG 1.52.0 phonemes, or characters without spaces. **Meaning:** the NLI model `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (He et al., 2021; Laurer et al., 2024) must find entailment both ways. **Language:** py3langid 0.4.0 (Lui and Baldwin, 2012). The evaluation judge, Qwen3-14B (Qwen Team, 2025), is not part of the method and never feeds it.

**Target architecture (mandatory).** Option b, air-gapped: `make run-offline` runs llama.cpp’s server on a local GGUF in a container with `network_mode: none`; the app joins its network namespace, with the NLI model and language identifier in its image. From a fresh clone (Colima, Apple M3, arm64) the 10 sample lines ran on the CPU (exit 0) and outbound requests failed; a localhost-only macOS sandbox gave identical outputs. Option a, on-premise: the evaluation ran on HPI’s H100 cluster (vLLM under Slurm, weights on the cluster, Hugging Face offline). Only the build needs the internet; `make run` then needs only the LLM endpoint.

**Other models and tools.** Apertus writes and revises every candidate. The models below only check, judge or voice its outputs, or build test data; eSpeak NG 1.52.0 counts syllables and py3langid 0.4.0 checks the language.

| Model | Role | Used in |
| :--- | :--- | :--- |
| mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (He et al., 2021; Laurer et al., 2024) | Main NLI: checks meaning | Repair loop and evaluation |
| bge-m3-zeroshot-v2.0-c (Laurer et al., 2024) | Second NLI, never seen by the loop (post-hoc) | Evaluation only |
| Qwen3-14B, BF16 (Qwen Team, 2025) | Judge: lists the facts, marks each kept, changed or dropped, lists added ones | Evaluation only: test, controls |
| Qwen3-8B, Q4_K_M (Qwen Team, 2025) | Judge for the shortening pilot | Evaluation only: dev |
| Qwen3-TTS-12Hz-1.7B-CustomVoice (Qwen Team) | Synthetic German speech (voices Aiden, Serena) | Timing evaluation, demo |
| Chatterbox multilingual (Resemble AI) | Synthetic speech for the first timing run, which failed its check | Timing evaluation |
| Whisper small (Radford et al., 2023) | Rejects takes that do not say their text | Timing evaluation |
| Claude (Anthropic) | Wrote the planted control pairs; as three agents, annotated 30 go/no-go errors | Evaluation only: controls, error analysis |

## 3. Use of Apertus

`swiss-ai/Apertus-v1.5-8B` (revision `a411d838`), inference only, writes and revises every candidate. Final numbers: official BF16 weights in the official vLLM container (`swiss-ai/vllm_apertus_1.5_release`, vLLM 0.23.1rc1; Kwon et al., 2023), one H100, 60 % of GPU memory. Development (go/no-go, pilot, prompts): llama.cpp b11429 on a Mac, a 4-bit Q4_K_M GGUF of a text-only conversion, not compared with the official model. Temperature 0.7, top_p 0.95, at most 1,024 tokens, thinking off; seeds 0, 1, 2, round r at seed + 1000 × r.

**What we learned about Apertus.** Measured in the test runs: it **follows a length target loosely and over-shortens**. Asked for 80 % of the syllables, its closest candidate gave 0.79 × the target in German and 0.78 × in French; one step to the French syllable budget gave 0.88 ×. It **revises well with specific feedback**: the loop accepted 39–42 % of open lines after the first revision and 20–23 % after the second (post-hoc). It **stays in the target language**: 2 of 10,185 translation-task outputs and 0 of 16,296 shortening-task outputs left it. Its **JSON breaks in French**: `\'` in 3.5 % of French one-step answers, German 1 of 2,082. It **often returns fewer candidates than asked** (in 686 of 5,655 loop rounds). It **mistranslates rare words** in both systems (“Spitze”, “Hirschziegen”).

## 4. Data

FLEURS (Conneau et al., 2022; CC BY 4.0) at `70bb2e8`: dev 147 German and 137 French (97 and 90 without the go/no-go sentences), test 347 and 332. The text comes from FLoRes-101 (Goyal et al., 2022; CC BY-SA 4.0), public Wikimedia articles with no personal data, so our data files are CC BY-SA 4.0. Prompts tuned on dev only, outside the 50 go/no-go sentences. Controls: 200 NLI pairs, 140 hard German judge controls. eSpeak matched hand counts on 46 of 50 items and counts all 963 references alike on Mac and cluster. No audio in the repo; recordings and synthetic speech served only the timing check and the demo. The native speaker’s ratings carry no name; no personal data was collected.

## 5. Evaluation

**Translation task: systems and budgets.** (a) Plain translation. (b) One step: of 4 candidates, the one closest to the budget. (c) Ours: keep (a) if it is at most 1.10 × the budget, even when shorter than the band; otherwise shorten it with the loop. The budget (±10 %) is the English characters without spaces (isometric; Anastasopoulos et al., 2022), or the English syllables × the target’s speech rate ÷ English’s (Pellegrino et al., 2011: German 0.964, French 1.160). Protocol v2.17 froze, before any test output, the prompts (by hash), selection, loop, keep rule and metrics: fit; kept vs reference (main) and vs source, by NLI both ways; and fit & complete, where the line fits and Qwen3-14B finds every source fact kept and nothing added. A missing or wrong-language output fails every metric; intervals are 95 % bootstraps over sentences (10,000, seed 0).

**Translation task** (FLEURS test set, final; % with 95 % intervals; 1,041 German and 996 French outputs per row; too long and second NLI post-hoc, without intervals).

<div class="wide">

| EN →, budget | System | Fit ±10 % | Too long | Kept vs reference (main NLI) | Kept vs source (NLI) | Fit & complete (judge) | Kept vs ref. (2nd NLI) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| DE, characters | (a) plain | 27.2 [23.0, 31.4] | 71.4 | 79.5 [75.7, 83.3] | 78.2 [74.2, 82.1] | 26.8 [22.7, 31.0] | 88.2 |
| DE, characters | (b) one step | 59.4 [55.1, 63.5] | 1.9 | 74.1 [70.3, 77.8] | 69.5 [65.7, 73.4] | 53.7 [49.6, 57.8] | 78.2 |
| DE, characters | **(c) ours** | **80.2 [77.1, 83.2]** | 13.8 | 80.6 [77.0, 84.1] | 79.2 [75.6, 82.5] | **70.5 [66.8, 74.2]** | 84.6 |
| DE, syllables | (a) plain | 19.6 [15.8, 23.6] | 79.1 | 79.5 [75.7, 83.3] | 78.2 [74.2, 82.1] | 19.5 [15.8, 23.4] | 88.2 |
| DE, syllables | (b) one step | **71.6 [67.7, 75.2]** | 14.8 | 76.8 [73.2, 80.2] | 72.5 [68.9, 76.1] | **61.5 [57.4, 65.4]** | 80.3 |
| DE, syllables | **(c) ours** | **70.3 [66.9, 73.8]** | 20.4 | 81.6 [78.2, 84.6] | 77.7 [74.2, 81.1] | **56.9 [52.9, 60.7]** | 82.9 |
| FR, characters | (a) plain | 23.9 [19.7, 28.3] | 74.2 | 79.7 [75.7, 83.6] | 73.5 [69.0, 77.8] | 23.5 [19.4, 27.9] | 88.2 |
| FR, characters | (b) one step | 59.8 [55.5, 64.1] | 5.1 | 69.7 [65.8, 73.5] | 64.7 [60.7, 68.6] | 53.0 [48.7, 57.3] | 75.4 |
| FR, characters | **(c) ours** | **77.3 [74.0, 80.6]** | 12.2 | 80.7 [77.1, 84.1] | 76.9 [73.1, 80.5] | **68.6 [64.9, 72.2]** | 85.3 |
| FR, syllables | (a) plain | 55.6 [50.9, 60.3] | 20.5 | 79.7 [75.7, 83.6] | 73.5 [69.0, 77.8] | 54.9 [50.2, 59.7] | 88.2 |
| FR, syllables | (b) one step | 44.7 [40.1, 49.3] | 1.4 | 74.9 [71.2, 78.5] | 72.4 [68.6, 76.0] | 41.9 [37.4, 46.4] | 81.6 |
| FR, syllables | **(c) ours** | **69.9 [65.7, 74.1]** | 4.1 | 81.5 [77.8, 85.1] | 74.4 [70.2, 78.5] | **68.1 [63.7, 72.4]** | 87.7 |

</div>

Bold: the highest fit or fit & complete in its setting, and any system whose paired interval with it includes 0. For (c), dev fit agreed with test within 5 points. Paired differences (post-hoc):

| Ours minus … (points) | (a) plain | (b) one step |
| :--- | :--- | :--- |
| Fit | +14.3 to +53.4; every interval above 0 | +17.5 to +25.2 in three settings; German syllables −1.2 [−6.0, +3.6], a tie |
| Too long | −16.4 to −61.9 | +2.7 to +11.9: one step undershoots |
| Meaning, main NLI | +1.0 to +2.0; only French syllables excludes 0 | +4.8 to +11.0 |

- **Second NLI:** ours − plain −0.5 to −5.3. It also rates one step lower than the main NLI does, so not all of the gap comes from the loop. But on the lines the loop shortened, ours gains more from the main NLI than one step does (German syllables +6.0 [+1.3, +10.7]): there the loop’s own NLI probably inflates ours.
- **French, characters vs syllables (text only):** the French syllable budget is 1.16 × the English syllables, so plain French meets it in 55.6 % of lines (characters: 23.9 %) and one step over-shortens. Speech does not show syllables beating characters (Timing).
- **Parse failures** count as misses, as frozen: plain lost 9 of 2,037 answers, one step 114 of 4,074 (mostly French), ours 28 of 4,074 lines (the 9 plain failures in both budgets, plus 10 lines where the loop ended without an output). Reading `\'` as `'` (post-hoc) brings back 70 answers; ours still leads French characters by 14.2 [9.0, 19.5] points of fit.

**Native speaker** (descriptive). One German native speaker rated 25 lines of a 50-line sheet without system labels, one per English source (translation task, test set, German, syllable budget, seed 0). Lines both systems shared (5 sources) count for both: 30 ratings, with each system’s rates from different sentences (no test). Meaning kept: plain 12 of 14, ours 12 of 16 (minor loss 1 and 3, wrong 1 each, nothing added); natural German 10 of 14 and 11 of 16. Per line, the ratings agree with the automatic checks at κ −0.15 to 0.44. Ours had an inch symbol for “Zoll”, a one-word fragment, broken grammar and a dropped “some”; both gave “Spitze” for “sharpener” and “Hirschziegen” for “spotted deer”.

**Timing in seconds** (exploratory, post-hoc). Human readings: FLEURS test recordings not flagged as noisy, trimmed alike. TTS: Qwen3-TTS (Qwen Team), preset voice Aiden (Apache-2.0), the median of 3 clean takes per line, checked with Whisper (Radford et al., 2023).

<div class="wide">

| Test | n | Fits ±10 %: (a) / (c) | Too long: (a) / (c) | Paired test (fit) |
| :--- | :---: | :---: | :---: | :---: |
| Human readings: do syllable or character counts predict a ±10 % fit in seconds? | 209 DE, 221 FR | κ −0.16 to +0.02 | – | – |
| TTS, translation task’s syllable budget (sheet sources) | 21 | 8 / 6 | 7 / 4 | McNemar p = 0.73 |
| TTS, budget = English seconds ÷ the voice’s 0.231 s per syllable (rate from 30 German dev texts) | 99 | 25 / 47 | 51 / 24 | 22 to 0, p = 4.8e-07 |

</div>

For one voice, syllables predict seconds (r = 0.98). Across human readers speed dominates (r = 0.77–0.93 within a language, yet κ near 0): they speak 1.13 (DE) and 1.35 (FR) times as many syllables per second as the English readers, not the 0.964 and 1.160 the budget assumes. Uncalibrated, ours ran short for this voice (11 of 15 misses).

**Cost per line** (post-hoc; H100-seconds estimated from generation time): plain 1.01 LLM calls, 0.41 s, 42 completion tokens, 0.04–0.10 H100-s; one step 1.00, 0.93 s, 124, 0.08–0.29; ours, plain included, 2.40, 1.57 s, 197, 0.47–0.65, plus 5.77 s of loop checks.

**Shortening task** (test set, final; 8B BF16): shorten a sentence in its own language to 90–60 % of its syllables (347 German and 332 French × 4 levels × 3 seeds), without the loop (closest of 4 candidates) and with it. The loop’s effect is a paired difference, pre-registered (v2.12).

<div class="wide">

| Shortening task | Fit: without → with loop | Paired gain | Fit & complete: without → with | Paired gain |
| :--- | :---: | :---: | :---: | :---: |
| German | 34.9 → 64.7 % | +29.8 [27.2, 32.4] | 14.2 → 38.4 % | +24.3 [22.2, 26.3] |
| French | 34.4 → 67.6 % | +33.2 [30.6, 35.8] | 15.5 → 44.2 % | +28.6 [26.4, 30.9] |

</div>

The pre-registered go/no-go, an early test of one prompt without the loop (dev, 4-bit, 50 German sentences × 3, level 80 %), failed both thresholds, a null result: fit 40.7 % [31.3, 50.0] (60 % needed), NLI kept among fits 62.3 % (80 % needed); in a random sample of 30 of the 67 outputs that the NLI flagged as dropping information, three Claude agents (not native speakers) found a lost qualifier in 24. By level, fit & complete gains +56.7 points at 90 % and +1.6 [−0.6, +3.8] at 60 % in German (French +61.7 and +5.4 [+3.2, +7.6]); at 60 % the loop prefers what its NLI accepts, and its misses run long.

## 6. Limitations

- **Meaning checks miss small changes** (table below). The judge’s fit & complete is an upper bound, looser from English (translation task), where its near-zero added facts (0.0–0.1 %) mean little. **The main NLI is the loop’s own model**; the second NLI rates ours 2.8–5.3 points below plain in three settings. Kept vs source is cross-lingual and weaker: the main NLI keeps only 29 of 40 cross-lingual identity pairs.

*Planted German changes caught, source in German or, as in the translation task, in English (second NLI post-hoc; the judge passed its identity-pair check, 100 % against 90 % needed).*

<div class="wide">

| Planted change (n) | NLI | NLI, from English | Second NLI | Second NLI, from English | Judge | Judge, from English |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Qualifier (14) | 3 | 6 | 1 | 1 | 7 | 0 |
| Modal (13) | 10 | 7 | 1 | 0 | 10 | 4 |
| Number (13) | 12 | 12 | 9 | 5 | 13 | 12 |
| Inserted fact (20) | 20 | 20 | 20 | 14 | 16 | 5 |

</div>

- **Small human checks:** timing uses one TTS voice, not dubbing actors. One rater saw 25 lines, rates come from different sentences, and blinding was partial (both lines of a source were on the sheet, the shorter visible; the rater noted “looks longer” on six lines). Claude wrote the control pairs; no native speaker has reviewed them.
- **The loop can game the length count** with symbols eSpeak counts as 0 syllables (`"` for “Zoll”). **Tight targets give long lines** (shortening task, with the loop). **No grammar check** (*“den 18. Jahrhundert Markt”*).
- **Not tested:** Italian; 70B (scripts ready); Docker on an amd64 host (emulation only); the 4-bit development model against the official weights. **Batching** 16 items on the HPC may change outputs slightly.

## 7. Reproducibility

- **Runs:** shortening task `68492f2`, translation task `7b22d93`, second NLI `f0e566c`; results reports as of `0108111`. Apple M3 (16 GB); one H100 80 GB per HPC job; 6.44 of 12 budgeted H100-hours (sacct): 6.03 setup and experiments, 0.42 text-to-speech.
- **Records:** each file in `results/` gives date, commit, model, quantisation, endpoint, seeds and n (judge: temperature 0, seed 0); rebuild with `docs/hpc.md`, `docs/local_llm.md`, `make figures`, `make run`.

## 8. Next steps

Calibrate the syllable budget to the target voice and check the fit with that voice (done for one TTS); a target that aims slightly short; a “cannot fit” flag for human review; a meaning check aimed at qualifiers; the exact-length task (step 3 in the protocol); 70B; Italian; subtitle formats.

## Licence

This report CC BY 4.0, code Apache-2.0, data files CC BY-SA 4.0 (`docs/licences.md`); all HackApertus projects are open source.

## References

- Anastasopoulos et al. (2022), Findings of the IWSLT 2022 Evaluation Campaign, *Proc. IWSLT*.
- Brannon, Virkar and Thompson (2023), Dubbing in Practice: A Large Scale Study of Human Localization With Insights for Automatic Dubbing, *TACL* 11, 419–435.
- Conneau et al. (2022), FLEURS, arXiv:2205.12446.
- Goyal et al. (2022), The Flores-101 Evaluation Benchmark, *TACL* 10.
- He, Gao and Chen (2021), DeBERTaV3, arXiv:2111.09543.
- Kwon et al. (2023), PagedAttention (vLLM), *SOSP*.
- Lakew et al. (2022), Isometric MT, *ICASSP*.
- Laurer et al. (2024), Less Annotating, More Classifying, *Political Analysis* 32(1).
- Lui and Baldwin (2012), langid.py, *ACL Demos*.
- Pellegrino, Coupé and Marsico (2011), A cross-language perspective on speech information rate, *Language* 87(3), 539–558.
- Qwen Team (2025), Qwen3 Technical Report, arXiv:2505.09388.
- Qwen Team, Qwen3-TTS, model card Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice.
- Radford et al. (2023), Whisper, *ICML*.
- Swiss AI Initiative (2026), Apertus 1.5, <https://huggingface.co/swiss-ai/Apertus-v1.5-8B>.
- eSpeak NG, llama.cpp, py3langid, matplotlib, Chatterbox (GitHub).
