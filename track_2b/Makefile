.PHONY: run run-offline docker-check

# make run          Our method (prompt v1 with the repair loop) on data/sample_input.jsonl, in Docker, against
#                   the LLM named by LLM_NAME, LLM_BASE_URL and LLM_API_KEY (from the environment, or from .env:
#                   see .env.example). Writes output/results.jsonl and output/summary.md.
# make run-offline  The same with no network at all: llama-server runs a local GGUF next to the app.
#                   make run-offline GGUF=/path/to/model.gguf [LLM_QUANTISATION=Q4_K_M] [OFFLINE_NAME=name]
# README.md explains both, and how to run the method without Docker.

SHELL := /bin/bash
COMMIT := $(shell git rev-parse HEAD 2>/dev/null)
DIRTY := $(shell git status --porcelain --untracked-files=no 2>/dev/null)
# The container is not a git checkout: the app records this commit in output/summary.md
export ISOCHRON_GIT_COMMIT := $(COMMIT)$(if $(DIRTY), (with uncommitted changes to tracked files))
# Output files belong to you, not to root
export ISOCHRON_UID_GID := $(shell id -u):$(shell id -g)
OFFLINE_NAME ?= $(basename $(notdir $(GGUF)))

run: docker-check
	@mkdir -p output
	docker compose run --rm --build app

run-offline: docker-check
	@test -n "$(GGUF)" && test -f "$(GGUF)" || { echo "make run-offline needs GGUF=/path/to/model.gguf (see README.md)"; exit 1; }
	@mkdir -p output
	@export GGUF="$(abspath $(GGUF))" LLM_NAME="$(OFFLINE_NAME)" LLM_API_KEY="$$(od -An -tx1 -N16 /dev/urandom | tr -d ' \n')"; \
	docker compose -f docker-compose.offline.yml up --build --abort-on-container-exit --exit-code-from app; status=$$?; \
	docker compose -f docker-compose.offline.yml down; exit $$status

docker-check:
	@command -v docker > /dev/null || { echo "make run needs Docker with Compose v2 (docker compose). README.md also shows how to run without Docker."; exit 1; }
	@docker compose version > /dev/null 2>&1 || { echo "make run needs Docker Compose v2 (the docker compose command)."; exit 1; }
