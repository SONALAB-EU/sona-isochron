"""Go/no-go reporting and smoke-test language check."""

from __future__ import annotations

from pathlib import Path

import pytest
from huggingface_hub import try_to_load_from_cache

from isochron import gonogo
from isochron.checks import guess_language
from isochron.data.fleurs import REPO_ID, REVISION
from isochron.score import gonogo_lines, pooled_ci

ROOT = Path(__file__).resolve().parents[1]


def test_pooled_ci() -> None:
    assert pooled_ci([(3, 3), (0, 3)]).startswith("50.0 % [")
    assert pooled_ci([(3, 3), (3, 3)]).startswith("100.0 % [100.0, 100.0] (6/6)")
    assert pooled_ci([(0, 0), (0, 0)]) == "–"


def _records(hit: bool, kept: bool, seeds=gonogo.SEEDS) -> list[dict]:
    recs = []
    for sid in gonogo.gonogo_ids():
        for seed in seeds:
            for how in ("closest", "first"):
                recs.append({
                    "id": sid, "seed": seed, "level": gonogo.LEVEL, "selection": how, "output": "x",
                    "target_mismatch": False,
                    "hit": {"syllables": hit, "words": hit, "chars": hit},
                    "nli": {"forward": "entailment", "backward": "entailment" if kept else "neutral",
                            "kept": kept, "added": False, "dropped": not kept},
                })
    return recs


def _cfg(**changes) -> dict:
    cfg = {"lang": "de", "split": "dev", "unit": "syllables", "levels": [80], "seeds": [0, 1, 2],
           "items": {"ids": gonogo.gonogo_ids()}, "mock": False,
           "prompt": {"name": "shorten_syllables_v1", "sha256": gonogo.PROMPT_SHA256}}
    return {**cfg, **changes}


@pytest.fixture(autouse=True)
def _in_project_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)


@pytest.mark.parametrize(("hit", "kept", "decision"), [(True, True, "GO"), (True, False, "NO-GO"), (False, True, "NO-GO")])
def test_gonogo_lines(hit: bool, kept: bool, decision: str) -> None:
    lines = gonogo_lines(_cfg(), _records(hit, kept))
    closest = next(line for line in lines if line.startswith("| closest"))
    first = next(line for line in lines if line.startswith("| first"))
    assert closest.endswith(f"**{decision}** |") and "| decides |" in closest
    assert "**GO**" not in first and "**NO-GO**" not in first
    assert lines[-1] == f"**Decision: {decision}**"


def test_gonogo_lines_no_decision() -> None:
    full = _records(True, True)
    assert gonogo_lines(_cfg(mock=True), full) == ["Go/no-go: mock run, no decision."]
    assert "not the frozen v1" in gonogo_lines(_cfg(prompt={"name": "x", "sha256": "f" * 64}), full)[0]
    partial = [r for r in full if not (r["seed"] == 2 and r["id"] in gonogo.gonogo_ids()[:10])]
    assert "incomplete or duplicated" in gonogo_lines(_cfg(), partial)[0]
    duplicated = full + [r for r in full if r["seed"] == 0]
    assert "incomplete or duplicated" in gonogo_lines(_cfg(), duplicated)[0]
    mismatched = [{**r, "target_mismatch": r["id"] == gonogo.gonogo_ids()[0]} for r in full]
    assert "targets differ" in gonogo_lines(_cfg(), mismatched)[0]


def test_gonogo_lines_ignore_other_runs() -> None:
    full = _records(True, True)
    assert gonogo_lines(_cfg(seeds=[0]), full) == []
    assert gonogo_lines(_cfg(items={"ids": gonogo.gonogo_ids() + ["1510"]}), full) == []
    assert gonogo_lines(_cfg(unit="words"), full) == []


train_cached = all(
    isinstance(try_to_load_from_cache(REPO_ID, f"data/{cfg}/train.tsv", revision=REVISION, repo_type="dataset"), str)
    for cfg in ("en_us", "de_de", "fr_fr", "it_it")
)


@pytest.mark.skipif(not train_cached, reason="FLEURS train transcriptions not in the local Hugging Face cache")
def test_guess_language() -> None:
    assert guess_language("Die Vereinten Nationen hoffen, einen Fonds einzurichten.") == "de"
    assert guess_language("Fünf CEP in vier Jahren – Martelly") == "de"  # short, no function words
    assert guess_language("Argentinien besitzt Weltklasse-Polo-Spieler") == "de"
    assert guess_language("Le train est parti de Berne à neuf heures.") == "fr"
    assert guess_language("Il treno è partito da Berna alle nove.") == "it"
    assert guess_language("The train left Bern at nine.") == "en"
    assert guess_language("") == "unknown"
