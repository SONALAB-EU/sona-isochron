# Docker check: `make run` and `make run-offline` as a judge would run them

- Date: 2026-10-12, 13:35–17:05 UTC
- Git commits: `0436ab3` (tested first, as committed), `ebe9e7c` (with the fixes below; every pass
  below is this commit). The commit that adds this file changes only comments and documentation on top of
  `ebe9e7c`.
- Model: apertus-v1.5-8b-text-q4_k_m, quantisation Q4_K_M, llama.cpp llama-server build 11429
  (`b11429-d81235049`): native on the Mac with Metal (steps 2 and 4), or the
  `ghcr.io/ggml-org/llama.cpp:server-b11429` image on the CPU (steps 3 and 5)
- Endpoints: given per step below
- Method: as `make run` records it in `output/summary.md`: prompt `shorten_syllables_v1` with the repair
  loop (`revise_v1`), at most 2 revisions; item seed 0 for every line, so seeds 0, 1000 and 2000 for
  rounds 0, 1 and 2
- Input: `data/sample_input.jsonl`, n = 10 lines (German); TTS: none
- Host: Apple M3, 16 GB, macOS 26.5.1. Colima 0.10.3 (macOS Virtualization.Framework, Rosetta for amd64),
  VM with 6 CPUs and 10 GiB (as `docker info` and `colima list` report them), Ubuntu 24.04.4, Docker
  Engine 29.5.2, Compose 5.6.0 (Mac) and 5.1.4 (VM), buildx 0.38.0
- Times are wall-clock times of single runs, measured with `date +%s` around each command. The LLM samples
  (temperature 0.7) and the network varies, so they are indications, not benchmarks.

## Results

| Step | What | Commit | `LLM_BASE_URL` given | Result | Time |
|------|------|--------|----------------------|--------|-----:|
| 1 | Fresh `git clone` into a temp folder, `cd track_2b` | – | – | – | – |
| 2a | `make run`, clone in `/private/tmp` | `0436ab3` | `http://host.docker.internal:8080/v1` | **fail**: `No such file or directory: 'data/sample_input.jsonl'` (fix 1) | 260 s |
| 2b | `make run`, clone in `$HOME/isochron-judge.*` | `ebe9e7c` | `http://127.0.0.1:8080/v1` (rewritten to `host.docker.internal`, fix 2) | pass, exit 0 | 375 s (image cached) |
| 3 | `make run-offline GGUF=… LLM_QUANTISATION=Q4_K_M`, native llama-server stopped | `ebe9e7c` | `http://127.0.0.1:8080/v1` (set by the compose file) | pass, exit 0 | 594 s, of which 57 s to load the GGUF |
| 4a | `docker buildx build --platform linux/amd64`, cold | `ebe9e7c` | – | **fail**: segmentation fault in eSpeak NG's build, under Rosetta (see below) | 450 s |
| 4b | The same, again | `ebe9e7c` | – | pass | 250 s (apt layer cached from 4a) |
| 4c | `DOCKER_DEFAULT_PLATFORM=linux/amd64 make run` on the amd64 image, under Rosetta | `ebe9e7c` | `http://host.docker.internal:8080/v1` | pass, exit 0 | 7,670 s |
| 5a | `make run` in the Colima VM, a Linux Docker host; server on the VM's 127.0.0.1 | `0436ab3` | `http://localhost:8080/v1` | **fail**: `Connection refused` (fix 2) | 139 s |
| 5b | The same | `ebe9e7c` | `http://localhost:8080/v1` (app on the host's network) | pass, exit 0 | 534 s |

What each passing run wrote (`output/summary.md`):

| Step | Platform | LLM server | Fit | NLI kept | Fit and kept | Wrong language | Revisions per line | Time per line |
|------|----------|------------|----:|---------:|-------------:|---------------:|-------------------:|--------------:|
| 2b | arm64 | native, Metal | 6/10 | 9/10 | 5/10 | 0/10 | 1.50 | 35.4 s |
| 3 | arm64 | container, CPU | 6/10 | 10/10 | 6/10 | 0/10 | 1.40 | 51.2 s |
| 4c | amd64 (Rosetta) | native, Metal | 6/10 | 9/10 | 5/10 | 0/10 | 1.50 | 749.3 s |
| 5b | arm64 (Linux host) | container, CPU | 6/10 | 10/10 | 6/10 | 0/10 | 1.40 | 38.7 s |

- 2b and 4c, the same server and seeds on two architectures: every field of `output/results.jsonl` except
  `time_s` is the same on all 10 lines (outputs, syllable counts, NLI and language decisions).
- 3 and 2b give different outputs on all 10 lines: llama.cpp on the CPU does not compute exactly what it
  computes with Metal, so the same seed samples other tokens.
- 4c is 21 times slower per line than 2b, because the NLI model runs under emulation. On an amd64 host it
  runs natively.
- These 10 lines show the method at work; they are not an evaluation.

## Fixes (commit `ebe9e7c`)

1. **A checkout outside Docker's shared folders.** Docker Desktop and Colima run containers in a VM that
   sees only the folders shared with it (by default the home folder). From `/private/tmp`, the bind
   mounts of `data/` and `output/` came up as empty folders, and the app stopped with
   `No such file or directory: 'data/sample_input.jsonl'`; nothing said why. `make run` and
   `make run-offline` now build the image, then check in a throwaway container (no network) that
   `data/sample_input.jsonl` is visible, `output/` is writable, and for `run-offline` that the GGUF is a
   file. If not, they stop with: "Docker cannot see this folder (…), or cannot write to output/ in it.
   With Docker Desktop or Colima, both must be in a folder shared with Docker's VM (your home folder is
   shared by default)." Checked from the `/private/tmp` clone, and with a GGUF in `/private/tmp`.
2. **`LLM_BASE_URL` on the host's own loopback.** The template says only "LLM_BASE_URL — endpoint base
   URL" (README of `HackApertus/project-template`, `main` at `09f8e9e`, fetched 2026-10-12); it does not
   say where the judges' endpoint will be. If it is a server on the judge's machine, `localhost` is a
   natural value, and inside the container `localhost` is the container. On a Linux host, 5a failed with
   `Connection refused`. `make run` now reads the resolved `LLM_BASE_URL` (from the environment or `.env`,
   via `docker compose config`) and, if its host is `localhost`, `127.x.x.x`, `[::1]` or `0.0.0.0`:
   - on a Linux host whose engine is not Docker Desktop: adds `docker-compose.host-network.yml`
     (`network_mode: host`), so the URL works unchanged (5b);
   - otherwise (Docker Desktop, Colima): replaces the host with `host.docker.internal` (2b).
   Any other URL is passed on unchanged. The decision was checked with stub `docker` and `uname` commands
   on 12 URLs × 3 platforms (including `user:pw@localhost`, `[::1]`, and look-alikes such as
   `localhost.example.ch` and `127.0.0.1.nip.io`, which are left alone), and for real in 2b and 5b.
   `make run-offline` is unaffected: its app and server share a network namespace.
   - Not handled, and not tested: rootless Docker on Linux. Its host network is RootlessKit's namespace,
     not the host's, and it maps container uids differently, so both the localhost case and the
     `user:` setting the compose files already had would need other handling there. The README says so.
   - Not measured here: on a plain Linux host, `host.docker.internal` (the README's earlier advice) maps to
     the docker0 bridge, which does not reach a server listening only on 127.0.0.1; that is Docker's
     documented behaviour. In Colima it does reach it, because `host-gateway` is the Mac and the Mac
     forwards the VM's ports, so this setup cannot show the failure. The README now recommends
     `localhost`.
3. **README.md was in the dependency layer.** The Dockerfile copied `README.md` with `pyproject.toml` and
   `uv.lock` before `uv pip install`, so any README edit invalidated that layer and downloaded every
   package again. In 2a, BuildKit logged 685 s for that step; 2a had joined it while another rebuild
   on the same Mac (for the step 4 runs), started 9 min earlier, was running it, so the step did not take that long within 2a. `uv export --frozen` does not need it (checked), so it is no
   longer copied, nor in the build context.

## amd64 under Rosetta: the eSpeak NG build crashes at random

4a failed in the eSpeak NG stage: `espeak-ng --compile=ar` crashed with a segmentation fault while
ninja built the dictionaries. A debug copy of that stage (`--target espeak`, build tree kept), built
again and again in the same VM:

| Platform | Build | Runs | Failed (segmentation fault) |
|----------|-------|-----:|----------------------------:|
| amd64 (Rosetta) | `cmake --build -j 6`, as in the Dockerfile (4a and 4b included) | 8 | 5 (`espeak-ng` compiling `ar_dict`, `pt_dict`, `af_dict`, `phondata`, and one not logged) |
| amd64 (Rosetta) | the program at `-j 6`, then the data at `-j 6` | 3 | 3 |
| amd64 (Rosetta) | the program at `-j 6`, then the data at `-j 1` | 1 | 1 |
| amd64 (Rosetta) | `-j 1` | 6 | 3 (`pt_dict`; and **gcc** itself, compiling `numbers.c` and `compiledict.c`) |
| arm64 (native) | `-j 6` | 10 | 0 |
| arm64 (native) | the program at `-j 6`, then the data at `-j 1` | 1 | 0 |

- Since gcc crashes too, the cause is the emulation, not eSpeak NG or this project's build. Neither
  the project's amd64 `espeak-ng` nor Debian's (`1.52.0+dfsg-5`, built on amd64 hardware) crashed in 90 parallel phoneme
  runs or 30 parallel dictionary compiles each, outside ninja.
- The Dockerfile is unchanged: on an amd64 or arm64 host, nothing is emulated. If you build for amd64 on
  an Apple Mac and the build fails like this, run it again: the layers that succeeded are cached.
- The amd64 image that 4b built has eSpeak NG data identical, file by file (364 files, SHA-256), to a
  native arm64 build of the same sources and options. With 4c matching 2b line by line, syllables are
  counted the same on both architectures.

## Also checked

- The image runs as the calling user: every output file belongs to that user, on the Mac and on Linux.
- Build times of the arm64 image at `0436ab3`: 40 min in the first build (an earlier build); 802 s
  (UV_NO_CACHE=1, image 3.14 GB) in a rebuild for the step 4 runs the same day, which ran at the same time as
  2a and shared its steps, so neither of those two times is clean.

## eSpeak NG's git fallback

The Dockerfile fetches eSpeak NG and sonic as pinned tarballs (SHA-256 checked) and, if GitHub cannot
serve one, the same commit with git. Exercised on arm64 with a tarball URL that does not exist
(`--build-arg ESPEAK_URL=…/refs/tags/no-such-tag.tar.gz`, `--target espeak`), at `ebe9e7c`:

- curl got HTTP 404 seven times (the first try and its 6 retries, 10 s apart), then the build printed
  "espeak: the tarball is unavailable, so fetching commit 4870adfa25b1a32b4361592f1be8a40337c58d6c",
  fetched it with git, and built eSpeak NG 1.52.0. Exit 0, 85 s.
- Its eSpeak NG data are identical, file by file (SHA-256), to those of the app image built from the
  tarball, and `espeak-ng -q -x` gives the same phonemes for a German, French, English and Italian
  sentence.
