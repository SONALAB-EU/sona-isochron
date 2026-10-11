"""data/sample_input.jsonl: the input of `make run`.

The first 10 German dev sentences in file order (data/fleurs_de_dev.jsonl) that are not among the 50
go/no-go sentences, each with a target level: 90, 80, 70 and 60 % of its syllables in turn (step 2's
levels). The format is the one isochron.app reads (README.md): id, lang, text and level; license and
source are carried over from FLEURS for each line.

    uv run python -m isochron.data.build_sample_input
"""

from __future__ import annotations

import json
from pathlib import Path

from isochron.gonogo import gonogo_ids
from isochron.schema import SentenceRecord, read_jsonl

SOURCE = Path("data/fleurs_de_dev.jsonl")
OUT = Path("data/sample_input.jsonl")
N = 10
LEVELS = (90, 80, 70, 60)


def sample_lines(source: Path = SOURCE) -> list[dict]:
    excluded = set(gonogo_ids(source))
    records = [r for r in read_jsonl(source, SentenceRecord) if r.id not in excluded][:N]
    return [{"id": r.id, "lang": r.tgt_lang, "text": r.ref_text, "level": LEVELS[i % len(LEVELS)],
             "license": r.license, "source": r.source} for i, r in enumerate(records)]


def main() -> None:
    lines = sample_lines()
    OUT.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines), encoding="utf-8")
    print(f"wrote {len(lines)} lines to {OUT}")


if __name__ == "__main__":
    main()
