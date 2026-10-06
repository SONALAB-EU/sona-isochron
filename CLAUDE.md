# CLAUDE.md — Hack Apertus 2026, Track 2B

These rules apply to all work in this repository.

## Project

Adapt dubbing translations so the spoken target line fits the source slot in
seconds (isochrony), without adding or dropping meaning, using Apertus 1.5.
Character-count (isometric) prompting is a baseline, not our method.

## Layout and running

- `track_2b/` is the project root. Keep the template's files in it where they
  are: don't rename or move them.
- Judges run `make run` in `track_2b/` on a clean checkout, via Docker.

## LLM access

- The LLM is reached only through the env vars `LLM_NAME`, `LLM_BASE_URL`,
  `LLM_API_KEY` (OpenAI-compatible API).
- No hardcoded endpoints or keys anywhere, including tests, notebooks and docs
  examples.

## Data and repository hygiene

- `data/` stays under 100 MB.
- Never commit audio, model weights, `.env` or caches.

## Licensing

- Code is Apache-2.0.
- Use only openly licensed data and models, and record each one's licence in
  `track_2b/docs/licences.md`.

## Provenance

- New code only. Never read, copy or reuse anything from `~/sonalab` or any
  SonaLab repo.

## Results and honesty

- Never present an estimate as a measurement.
- Every results file records: date, git commit, model + quantisation,
  endpoint, TTS engine + voice, seeds, n.
- If something fails, stop and report it. A null result is a result.
- Tune on the FLEURS dev split only; the test split is for final numbers.

## Git

- Never push, to any remote. Never push to the `template` remote. The user
  pushes manually.

## Communication

- When giving shell commands to paste, no inline `#` comments (zsh breaks on
  them).
