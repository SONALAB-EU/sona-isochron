.PHONY: run run-offline figures docker-check

# make run          Our method (prompt v1 with the repair loop) on data/sample_input.jsonl, in Docker, against
#                   the LLM named by LLM_NAME, LLM_BASE_URL and LLM_API_KEY (from the environment, or from .env:
#                   see .env.example). Writes output/results.jsonl and output/summary.md.
# make run-offline  The same with no network at all: llama-server runs a local GGUF next to the app.
#                   make run-offline GGUF=/path/to/model.gguf [LLM_QUANTISATION=Q4_K_M] [OFFLINE_NAME=name]
# make figures      The report's figures (docs/figures/*.pdf, *.png and the CSV behind each), drawn with
#                   matplotlib from committed results files only. Needs uv, not Docker.
# README.md explains all three, and how to run the method without Docker.

SHELL := /bin/bash
COMMIT := $(shell git rev-parse HEAD 2>/dev/null)
DIRTY := $(shell git status --porcelain --untracked-files=no 2>/dev/null)
# The container is not a git checkout: the app records this commit in output/summary.md
export ISOCHRON_GIT_COMMIT := $(COMMIT)$(if $(DIRTY), (with uncommitted changes to tracked files))
# Output files belong to you, not to root
export ISOCHRON_UID_GID := $(shell id -u):$(shell id -g)
OFFLINE_NAME ?= $(basename $(notdir $(GGUF)))
# Docker Desktop and Colima run containers in a VM that sees only the folders shared with it (by default, your
# home folder). From a checkout anywhere else (/tmp, for example), the bind mounts come up empty and the app
# would fail with "No such file or directory". So, once the image is built, a throwaway container checks them.
# Its arguments are extra docker run options (run-offline adds the GGUF, which must then be a file in there too).
CHECK_MOUNTS = check_mounts() { \
	docker run --rm --network none --user "$(ISOCHRON_UID_GID)" --entrypoint sh -v "$(CURDIR)/data:/app/data:ro" \
		-v "$(CURDIR)/output:/app/output" "$$@" isochron-app:local -c 'test -f data/sample_input.jsonl \
		&& test -w output && { test ! -e /models/model.gguf || test -f /models/model.gguf; }' \
	|| { echo "Docker cannot see this folder ($(CURDIR))$(if $(GGUF), or the GGUF ($(abspath $(GGUF))),), or cannot write to output/ in it. With Docker Desktop or Colima, both must be in a folder shared with Docker's VM (your home folder is shared by default)."; return 1; }; \
}

# A server on the Docker host's loopback interface (LLM_BASE_URL with localhost, 127.x.x.x, [::1] or 0.0.0.0)
# is not at that address inside the container, whose loopback is its own. On a Linux host, where the Docker
# engine runs on the host itself, the app then shares the host's network (docker-compose.host-network.yml) and
# the URL works unchanged. Docker Desktop and Colima run the engine in a VM, so there the address becomes
# host.docker.internal, which they forward to the host. Any other LLM_BASE_URL is passed on as it is.
run: docker-check
	@mkdir -p output
	@url="$$(docker compose config --format json 2> /dev/null | sed -n 's/^ *"LLM_BASE_URL": *"\(.*\)",\{0,1\}$$/\1/p' | head -n 1)"; \
	host="$$(printf '%s\n' "$$url" | sed -E 's#^[A-Za-z][A-Za-z0-9+.-]*://([^@/]*@)?(\[[^]]*\]|[^:/]*).*#\2#')"; \
	files=(-f docker-compose.yml); \
	if [[ "$$host" =~ ^(localhost|127(\.[0-9]{1,3}){3}|\[::1\]|0\.0\.0\.0)$$ ]]; then \
		if [ "$$(uname -s)" = Linux ] && ! docker info --format '{{.OperatingSystem}}' 2> /dev/null | grep -q 'Docker Desktop'; then \
			echo "LLM_BASE_URL is on this host's loopback interface: the app shares the host's network"; \
			files+=(-f docker-compose.host-network.yml); \
		else \
			export LLM_BASE_URL="$$(printf '%s\n' "$$url" | sed -E 's#^([A-Za-z][A-Za-z0-9+.-]*://([^@/]*@)?)(\[[^]]*\]|[^:/]*)#\1host.docker.internal#')"; \
			echo "LLM_BASE_URL is on this host's loopback interface: the app uses $$LLM_BASE_URL"; \
		fi; \
	fi; \
	docker compose "$${files[@]}" build app && $(CHECK_MOUNTS) && check_mounts \
	&& docker compose "$${files[@]}" run --rm app

run-offline: docker-check
	@test -n "$(GGUF)" && test -f "$(GGUF)" || { echo "make run-offline needs GGUF=/path/to/model.gguf (see README.md)"; exit 1; }
	@mkdir -p output
	@export GGUF="$(abspath $(GGUF))" LLM_NAME="$(OFFLINE_NAME)" LLM_API_KEY="$$(od -An -tx1 -N16 /dev/urandom | tr -d ' \n')"; \
	docker compose -f docker-compose.offline.yml build app && $(CHECK_MOUNTS) \
	&& check_mounts -v "$$GGUF:/models/model.gguf:ro" || exit 1; \
	docker compose -f docker-compose.offline.yml up --abort-on-container-exit --exit-code-from app; status=$$?; \
	docker compose -f docker-compose.offline.yml down; exit $$status

figures:
	uv run --group figures python -m isochron.figures --out docs/figures

docker-check:
	@command -v docker > /dev/null || { echo "make run needs Docker with Compose v2 (docker compose). README.md also shows how to run without Docker."; exit 1; }
	@docker compose version > /dev/null 2>&1 || { echo "make run needs Docker Compose v2 (the docker compose command)."; exit 1; }
