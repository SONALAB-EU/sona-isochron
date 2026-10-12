"""data/nli_controls_xl.jsonl and data/judge_controls_xl.jsonl: the two judge suites, cross-lingual.

Step 4 judges a German or French output against the facts of its English source, so the judge is
validated on the same kind of pair. Each pair of data/nli_controls.jsonl and data/judge_controls_de.jsonl
keeps its output, its control type and its expected verdict. Its source is replaced by the English
original of the same FLEURS train sentence (en_us, the revision of isochron.data.fleurs).

The German and French sources are human translations of these English sentences. So an "identity" pair
now asks whether the judge accepts a faithful human translation as complete, and a changed pair whether
it catches the change across languages.

    uv run python -m isochron.data.build_xl_controls
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from isochron.data.fleurs import train_sentences
from isochron.schema import ControlPair, read_jsonl, write_jsonl

FILES = {Path("data/nli_controls.jsonl"): Path("data/nli_controls_xl.jsonl"),
         Path("data/judge_controls_de.jsonl"): Path("data/judge_controls_xl.jsonl")}


def cross_lingual(pairs: list[ControlPair], english: dict[int, str]) -> list[ControlPair]:
    return [replace(p, id=f"xl-{p.id}", source=english[int(p.fleurs_id)], source_lang="en") for p in pairs]


def main() -> None:
    english = train_sentences("en_us")
    for src, dst in FILES.items():
        pairs = cross_lingual(list(read_jsonl(src, ControlPair)), english)
        n = write_jsonl(dst, pairs)
        print(f"wrote {n} pairs to {dst}")


if __name__ == "__main__":
    main()
