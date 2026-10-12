# syntax=docker/dockerfile:1
# The container `make run` starts (Makefile, docker-compose.yml, README.md): our method, prompt v1 with the
# repair loop, on data/sample_input.jsonl, with the NLI and the language check on the CPU.
#
# Build time needs the internet: Debian packages; the eSpeak NG 1.52.0 and sonic sources (pinned by
# SHA-256); the Python packages of uv.lock (hash-checked), with torch as its CPU build from
# download.pytorch.org (the locked version, hash-checked); and the NLI model from Hugging Face (pinned
# revision). Run time needs only the LLM endpoint (make run), or no network at all (make run-offline).

ARG PYTHON_IMAGE=python:3.11.15-slim-trixie@sha256:90744cff8f32887f075c47d747a173ff333e9e98801667af93c357fa9f5e28ff

# eSpeak NG 1.52.0 from source, built as on the HPC (hpc/setup.sh), so that syllables are counted as in
# every result in this repository (tests/test_syllable_reference.py checks the HPC build against the Mac)
FROM ${PYTHON_IMAGE} AS espeak
ARG ESPEAK_URL=https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.52.0.tar.gz
ARG ESPEAK_SHA256=bb4338102ff3b49a81423da8a1a158b420124b055b60fa76cfb4b18677130a23
ARG ESPEAK_COMMIT=4870adfa25b1a32b4361592f1be8a40337c58d6c
ARG SONIC_URL=https://github.com/waywardgeek/sonic/archive/fbf75c3d6d846bad3bb3d456cbc5d07d9fd8c104.tar.gz
ARG SONIC_SHA256=715827b5a39b79e56e44397d7b845910df996d4cca74777b3b61629b1ddc98c1
ARG SONIC_COMMIT=fbf75c3d6d846bad3bb3d456cbc5d07d9fd8c104
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# Build tools only, in this stage only; the base image's digest fixes the Debian release they come from
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gcc g++ git make \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir cmake==3.31.6 ninja==1.11.1.4
WORKDIR /build
# Each source is the pinned tarball, checked against its SHA-256. GitHub's archive service sometimes fails to
# serve a tarball (HTTP 504), so the same commit is then fetched with git and checked against its commit id
# (espeak-ng has no .gitattributes, so the files are the tarball's).
RUN fetch() { \
        local name=$1 url=$2 sha256=$3 repo=$4 commit=$5; \
        if curl -fsSL --retry 6 --retry-delay 10 --retry-all-errors -o "$name.tar.gz" "$url" \
            && echo "$sha256  $name.tar.gz" | sha256sum -c -; then \
            mkdir "$name" && tar -xzf "$name.tar.gz" -C "$name" --strip-components=1; \
        else \
            echo "$name: the tarball is unavailable, so fetching commit $commit of $repo"; \
            rm -rf "$name" "$name.tar.gz" && git init -q "$name" \
                && git -C "$name" fetch -q --depth 1 "$repo" "$commit" && git -C "$name" checkout -q FETCH_HEAD \
                && test "$(git -C "$name" rev-parse HEAD)" = "$commit"; \
        fi; \
    }; \
    fetch espeak "$ESPEAK_URL" "$ESPEAK_SHA256" https://github.com/espeak-ng/espeak-ng.git "$ESPEAK_COMMIT" \
    && fetch sonic "$SONIC_URL" "$SONIC_SHA256" https://github.com/waywardgeek/sonic.git "$SONIC_COMMIT" \
    && cmake -S espeak -B out -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/espeak-ng \
        -DBUILD_SHARED_LIBS=OFF -DUSE_MBROLA=OFF -DUSE_LIBPCAUDIO=OFF -DUSE_ASYNC=OFF -DBUILD_TESTING=OFF \
        -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DFETCHCONTENT_SOURCE_DIR_SONIC-GIT=/build/sonic \
    && cmake --build out -j "$(nproc)" \
    && cmake --install out \
    && /opt/espeak-ng/bin/espeak-ng --version

FROM ${PYTHON_IMAGE} AS app
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
COPY --from=ghcr.io/astral-sh/uv:0.12.3@sha256:2d890623d310b57771ce840f0da5eed5fc6d657da05ffaa45d82797b53fa3abc /uv /usr/local/bin/uv
COPY --from=espeak /opt/espeak-ng /opt/espeak-ng
ENV PATH=/app/.venv/bin:/opt/espeak-ng/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/hf \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
WORKDIR /app

# Every package of uv.lock, hash-checked, except torch and the CUDA packages only its CUDA build needs; then
# torch itself at the locked version as the CPU build: one hash for the amd64 wheel, one for the arm64 wheel.
# The command substitution is unquoted on purpose: it gives one --no-emit-package option per package.
COPY pyproject.toml uv.lock .python-version README.md ./
# hadolint ignore=SC2046
RUN uv venv --python /usr/local/bin/python3 .venv \
    && uv export --frozen --no-dev --no-emit-project \
        $(python3 -c "import tomllib; print(' '.join('--no-emit-package ' + p['name'] for p in tomllib.load(open('uv.lock', 'rb'))['package'] if p['name'] in ('torch', 'triton') or p['name'].startswith(('nvidia-', 'cuda-'))))") \
        -o /tmp/requirements.txt \
    && uv pip install --python .venv/bin/python --require-hashes -r /tmp/requirements.txt \
    && echo 'torch==2.14.1+cpu --hash=sha256:5e38154c8896d426a5df58bf2276b603e82184dfae4f54d77dbb212f36e34f37 --hash=sha256:36a03a3f87ec875ca39c8e29eccbaf0fc704605f78a3f7f179f157048c3c395e' > /tmp/torch-cpu.txt \
    && uv pip install --python .venv/bin/python --no-deps --require-hashes \
        --index-url https://download.pytorch.org/whl/cpu -r /tmp/torch-cpu.txt \
    && rm /tmp/requirements.txt /tmp/torch-cpu.txt \
    && python -c "import torch; assert torch.__version__ == '2.14.1+cpu', torch.__version__"

# The NLI model at its pinned revision, inside the image, so the container needs no internet; this layer
# depends only on the NLI module, so code changes do not download it again
COPY src/isochron/__init__.py src/isochron/
COPY src/isochron/metrics/__init__.py src/isochron/metrics/meaning.py src/isochron/metrics/
RUN python -c "from isochron.metrics.meaning import NLI; NLI(device='cpu')" && chmod -R a+rX /opt/hf

COPY src ./src
COPY data/sample_input.jsonl ./data/sample_input.jsonl
RUN espeak-ng --version | grep -q 'eSpeak NG text-to-speech: 1.52.0' \
    && python -c "import isochron.app, isochron.loop_run"
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HOME=/tmp
ENTRYPOINT ["python", "-m", "isochron.app"]
CMD ["--input", "data/sample_input.jsonl", "--out", "output", "--device", "cpu"]
