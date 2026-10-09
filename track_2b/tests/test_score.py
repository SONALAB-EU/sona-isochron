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


def _records(hit: bool, kept: bool) -> list[dict]:
    recs = []
    for sid in gonogo.gonogo_ids():
        for seed in gonogo.SEEDS:
            for how in ("closest", "first"):
                recs.append({
                    "id": sid, "seed": seed, "level": gonogo.LEVEL, "selection": how, "output": "x",
                    "hit": {"syllables": hit, "words": hit, "chars": hit},
                    "nli": {"forward": "entailment", "backward": "entailment" if kept else "neutral",
                            "kept": kept, "added": False, "dropped": not kept},
                })
    return recs


@pytest.mark.parametrize(("hit", "kept", "decision"), [(True, True, "GO"), (True, False, "NO-GO"), (False, True, "NO-GO")])
def test_gonogo_lines(monkeypatch: pytest.MonkeyPatch, hit: bool, kept: bool, decision: str) -> None:
    monkeypatch.chdir(ROOT)
    cfg = {"lang": "de", "split": "dev", "unit": "syllables", "levels": [80], "seeds": [0, 1, 2],
           "items": {"ids": gonogo.gonogo_ids()}, "mock": False}
    table = "\n".join(gonogo_lines(cfg, _records(hit, kept)))
    row = next(line for line in table.splitlines() if line.startswith("| closest"))
    assert row.endswith(f"**{decision}** |")
    assert "| decides |" in row


def test_gonogo_lines_skip_mock_and_other_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    cfg = {"lang": "de", "split": "dev", "unit": "syllables", "levels": [80], "seeds": [0, 1, 2],
           "items": {"ids": gonogo.gonogo_ids()}, "mock": True}
    assert gonogo_lines(cfg, _records(True, True)) == ["Go/no-go: mock run, no decision."]
    assert gonogo_lines({**cfg, "mock": False, "seeds": [0]}, _records(True, True)) == []


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
