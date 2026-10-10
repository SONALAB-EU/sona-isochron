"""Build data/judge_controls_de.jsonl: hard controls that validate any meaning judge.

The NLI control suite (data/nli_controls.jsonl) deletes or inserts whole
clauses. The losses that dominate our outputs are smaller: a qualifier, a
number form or a modal verb (results/gonogo_error_analysis.md). These
controls test exactly that, on 60 German FLEURS train sentences:

- 40 changed pairs, one minimal edit each that changes the meaning:
  13 modal_changed (kann → muss, sollte … touren → tourte, durfte → wurde),
  13 number_changed (15. Jahrhundert → vor 15 Jahrhunderten, Millionen →
  Milliarden, mehr als 100 → 100) and 14 qualifier_changed (a dropped hedge,
  restrictor or connective such as möglicherweise, nur, Aber; viele → alle).
  Expected: the judge does not call the output complete.
- 20 fact_inserted pairs: one new fact (a date, a place, a cause, an
  attribute such as kostenpflichtig or jährlich). Expected: the judge lists
  added information.
- 20 same_meaning pairs, on the first 20 changed sentences: a minimal edit
  that keeps the meaning (15. → fünfzehnten, schnell → rasch, passive →
  active). Expected: complete. Without these, a judge that calls every edit a
  change would look perfect.
- 60 identity pairs, one per sentence. Expected: complete.

Selection, so the sentences are not hand-picked: German FLEURS train
sentences minus the 20 used in nli_controls.jsonl, in random.Random(0)
shuffled id order, 8 to 35 words, without a FLEURS transcription artefact
(a trailing "x"). The categories are filled in the order modal, number,
qualifier, inserted; each takes the first sentences in that order that match
its pattern and are not yet taken. A sentence is skipped only for a reason
listed in SKIPS. The edits below were written by hand by Claude (AI
assistant), not by a native speaker; build() checks that the sentences are
exactly the first ones in that order and that each edit applies once.

    uv run python -m isochron.data.build_judge_controls
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from isochron.data.fleurs import train_sentences
from isochron.schema import ControlPair, write_jsonl

OUT = Path("data/judge_controls_de.jsonl")
NLI_CONTROLS = Path("data/nli_controls.jsonl")
ORDER_SEED = 0
MIN_WORDS, MAX_WORDS = 8, 35
LICENSE = "CC-BY-SA-4.0"

PATTERNS = {
    "modal_changed": r"\b(kann|können|konnte|konnten|könnte|könnten|muss|müssen|musste|mussten|müsste|soll|sollen|"
                     r"sollte|sollten|darf|dürfen|durfte|dürfte|will|wollen|wollte|möchte|möchten|scheint|scheinen|"
                     r"würde|würden|wäre|wären)\b",
    "number_changed": r"\d|\b(zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|zwanzig|dreißig|vierzig|"
                      r"fünfzig|hundert|tausend|Millionen?|Milliarden?|Dutzend|Hälfte|Drittel|Viertel|doppelt|"
                      r"zweimal|dreimal|erste[nrsm]?|zweite[nrsm]?|dritte[nrsm]?|vierte[nrsm]?|fünfte[nrsm]?|"
                      r"erstmals|Hunderte|Tausende|beide[nrsm]?)\b",
    "qualifier_changed": r"\b(fast|beinahe|etwa|ungefähr|rund|knapp|nur|sehr|besonders|einige|viele|manche|meist|"
                         r"meistens|oft|häufig|selten|wahrscheinlich|vermutlich|angeblich|möglicherweise|vielleicht|"
                         r"laut|zufolge|zudem|außerdem|auch|bereits|sogar|eher|relativ|ziemlich|generell|"
                         r"normalerweise|typischerweise|überwiegend|hauptsächlich|teilweise|lokale[nrms]?)\b",
    "fact_inserted": r".",
}
QUOTAS = {"modal_changed": 13, "number_changed": 13, "qualifier_changed": 14, "fact_inserted": 20}
N_SAME_MEANING = 20
SKIPS = {
    ("modal_changed", 977): "only near-equivalent modal swaps (könnten → können)",
    ("number_changed", 203): "garbled quotation marks in the FLEURS transcription",
    ("fact_inserted", 203): "garbled quotation marks in the FLEURS transcription",
}

# FLEURS id -> (old, new): the edit that makes the output from the source
EDITS: dict[str, dict[int, tuple[str, str]]] = {
    "modal_changed": {
        1237: ("übernehmen kann.", "übernehmen muss."),
        752: ("kann schnell zu unerwünschten Reaktionen führen", "führt schnell zu unerwünschten Reaktionen"),
        1427: ("eine Diagnose stellen kann", "eine Diagnose stellen darf"),
        1248: ("weil man feststellen muss", "weil man feststellen kann"),
        914: ("muss man sich separat", "kann man sich separat"),
        847: ("erlernen wollen", "erlernen müssen"),
        1277: ("herstellen wollen", "herstellen müssen"),
        939: ("kann die Zollkontrolle ein Ärgernis sein", "ist die Zollkontrolle ein Ärgernis"),
        1071: ("gekauft werden können", "gekauft werden sollen"),
        702: ("sollten ein ecuadorianisches Konsulat aufsuchen", "müssen ein ecuadorianisches Konsulat aufsuchen"),
        1006: ("betreten werden durfte", "betreten wurde"),
        1017: ("sollte bis zum 16. September durch die Vereinigten Staaten und Kanada touren",
               "tourte bis zum 16. September durch die Vereinigten Staaten und Kanada"),
        1395: ("sollte in der Lage sein, weitere", "ist in der Lage, weitere"),
    },
    "number_changed": {
        486: ("im 15. Jahrhundert", "vor 15 Jahrhunderten"),
        282: ("6.500", "5.600"),
        1369: ("die größte bekannte Primzahl", "die zweitgrößte bekannte Primzahl"),
        149: ("2008", "2006"),
        489: ("In seiner Nachfolge standen weitere neun Gurus.", "In seiner Nachfolge stand der neunte Guru."),
        603: ("und einem Sauerstoffatom", "und Sauerstoffatomen"),
        1147: ("bis 5000 v. Chr.", "bis 500 v. Chr."),
        520: ("Millionen", "Milliarden"),
        87: ("in den letzten 15 Jahren", "in den letzten 50 Jahren"),
        1458: ("mehr als 100 Fuß", "100 Fuß"),
        744: ("aus 15 verschiedenen Inseln", "aus fünf verschiedenen Inseln"),
        242: ("mit 1,5 Kilometern pro Sekunde", "mit 15 Kilometern pro Sekunde"),
        60: ("1992", "1982"),
    },
    "qualifier_changed": {
        464: ("höchstwahrscheinlich auch", "auch"),
        227: ("nur aufgrund", "aufgrund"),
        1186: ("eine relativ einfache", "eine einfache"),
        761: ("erfordert für gewöhnlich bloß", "erfordert bloß"),
        380: ("weil nur die der Sonne", "weil die der Sonne"),
        262: ("hat bereits angekündigt", "hat angekündigt"),
        714: ("Die meisten Menschen buchen", "Die Menschen buchen"),
        999: ("Aber unabhängig", "Unabhängig"),
        579: ("dass sie oft als Bausteine", "dass sie als Bausteine"),
        1105: ("viele der kleineren Pyramiden", "alle kleineren Pyramiden"),
        992: ("rollen möglicherweise weiter", "rollen weiter"),
        778: ("ist am verbreitetsten", "ist verbreitet"),
        977: ("die sich sonst nur schwer", "die sich nur schwer"),
        1063: ("der Personenkraftwagen unumgänglich die Entwicklung", "der Personenkraftwagen die Entwicklung"),
    },
    "fact_inserted": {
        865: ("Montezumas Rache", "Montezumas Rache in Mexiko"),
        268: ("Der Fall wurde in Virginia", "Der Fall wurde 2003 in Virginia"),
        24: ("Alex Ovechkin", "der Russe Alex Ovechkin"),
        1083: ("in Schwierigkeiten", "wegen seiner Kamera in Schwierigkeiten"),
        738: ("stellt Genehmigungen", "stellt kostenpflichtige Genehmigungen"),
        518: ("des Schimpansen", "des erwachsenen Schimpansen"),
        1272: ("von Orangutangs in Borneo", "von Orangutangs im Regenwald von Borneo"),
        771: ("werden im Rahmen", "werden jährlich im Rahmen"),
        538: ("als kultureller Tourismus bezeichnet", "von Fachleuten als kultureller Tourismus bezeichnet"),
        363: ("in der Glühbirne irgendwann aus", "in der Glühbirne wegen der Hitze irgendwann aus"),
        880: ("impfen lassen", "kostenlos impfen lassen"),
        742: ("werden die Inseln manchmal", "werden die Inseln von Touristen manchmal"),
        293: ("wurden am Fuß des Berges gemeldet", "wurden am Montagmorgen am Fuß des Berges gemeldet"),
        1274: ("verbesserte sich Südafrika", "verbesserte sich Südafrika dank seines neuen Trainers"),
        1316: ("bleibt geschlossen", "bleibt bis Freitag geschlossen"),
        1425: ("dass der Baum", "dass der 150 Jahre alte Baum"),
        731: ("regelmäßig fahrenden Wassertaxis", "regelmäßig fahrenden, aber teuren Wassertaxis"),
        933: ("andere Anforderungen", "andere und strengere Anforderungen"),
        1036: ("Das Hershey-Chase-Experiment", "Das Hershey-Chase-Experiment von 1952"),
        1093: ("die jede Katze hat", "die jede Katze von Geburt an hat"),
    },
}
SAME_MEANING: dict[int, tuple[str, str]] = {
    464: ("höchstwahrscheinlich auch", "höchstwahrscheinlich ebenfalls"),
    1237: ("geben die leiblichen Eltern ihre Elternrechte auf", "verzichten die leiblichen Eltern auf ihre Elternrechte"),
    486: ("im 15. Jahrhundert", "im fünfzehnten Jahrhundert"),
    282: ("auf 6.500", "auf sechstausendfünfhundert"),
    752: ("kann schnell", "kann rasch"),
    1369: ("ein Mathematiker und Informatik-Professor", "ein Mathematiker und Professor für Informatik"),
    1427: ("lässt sich möglicherweise nicht sofort erkennen", "ist möglicherweise nicht sofort erkennbar"),
    149: ("war 2008 verstaatlicht", "war im Jahr 2008 verstaatlicht"),
    1248: ("Es macht wohl auch das Lesen einfacher", "Es erleichtert wohl auch das Lesen"),
    914: ("muss man sich separat eine globale Nummer kaufen", "muss man sich eine globale Nummer separat kaufen"),
    847: ("erlernen wollen", "lernen wollen"),
    227: ("nur aufgrund ihrer", "nur wegen ihrer"),
    1186: ("Die persische Sprache hat", "Das Persische hat"),
    489: ("Die Religion wurde im 15. Jahrhundert von Guru Nanak (1469-1539) gegründet.",
          "Guru Nanak (1469-1539) gründete die Religion im 15. Jahrhundert."),
    1277: ("als Berliner, Pfannkuchen oder Krapfen bezeichnet wird", "Berliner, Pfannkuchen oder Krapfen genannt wird"),
    603: ("aus zwei Wasserstoffatomen und einem Sauerstoffatom", "aus 2 Wasserstoffatomen und 1 Sauerstoffatom"),
    761: ("für gewöhnlich", "in der Regel"),
    939: ("kann die Zollkontrolle ein Ärgernis sein", "kann die Zollkontrolle lästig sein"),
    1147: ("Die Idee des Skifahrens", "Die Idee des Skilaufens"),
    520: ("deren Alter zwei bis drei Millionen Jahre beträgt", "die zwei bis drei Millionen Jahre alt sind"),
}


def seeded_order() -> tuple[list[int], dict[int, str]]:
    """German train sentence ids in the selection order, and their text."""
    sentences = train_sentences("de_de")
    used = {int(json.loads(line)["fleurs_id"]) for line in NLI_CONTROLS.read_text(encoding="utf-8").splitlines()
            if json.loads(line)["lang"] == "de"}
    ids = sorted(i for i in sentences if i not in used)
    random.Random(ORDER_SEED).shuffle(ids)
    return ids, sentences


def select(ids: list[int], sentences: dict[int, str]) -> dict[str, list[int]]:
    """The first sentences of each category, in category order, as the module docstring says."""
    taken: set[int] = set()
    chosen: dict[str, list[int]] = {}
    for category, quota in QUOTAS.items():
        picks = []
        for i in ids:
            s = sentences[i]
            if len(picks) == quota:
                break
            if (i in taken or not MIN_WORDS <= len(s.split()) <= MAX_WORDS or s.rstrip().endswith("x")
                    or (category, i) in SKIPS or not re.search(PATTERNS[category], s)):
                continue
            picks.append(i)
        taken |= set(picks)
        chosen[category] = picks
    return chosen


def edit(source: str, old: str, new: str, where: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"{where}: {old!r} occurs {source.count(old)} times in {source!r}")
    return source.replace(old, new)


def build() -> list[ControlPair]:
    ids, sentences = seeded_order()
    chosen = select(ids, sentences)
    rank = {i: k for k, i in enumerate(ids)}
    for category, picks in chosen.items():
        if picks != sorted(EDITS[category], key=rank.get):
            raise ValueError(f"{category}: the selection gives {picks}, the edits cover {sorted(EDITS[category], key=rank.get)}")
    changed = sorted((i for c in QUOTAS if c != "fact_inserted" for i in chosen[c]), key=rank.get)
    if sorted(SAME_MEANING, key=rank.get) != changed[:N_SAME_MEANING]:
        raise ValueError(f"same_meaning must cover the first {N_SAME_MEANING} changed sentences: {changed[:N_SAME_MEANING]}")

    pairs = []
    for category in QUOTAS:
        for i in chosen[category]:
            src = sentences[i]
            old, new = EDITS[category][i]
            rows = [("identity", src, None), (category, edit(src, old, new, f"{category} {i}"), f"{old} → {new}")]
            if i in SAME_MEANING:
                o, n = SAME_MEANING[i]
                rows.append(("same_meaning", edit(src, o, n, f"same_meaning {i}"), f"{o} → {n}"))
            pairs += [ControlPair(f"de-{i}-{control}", "de", str(i), control, src, out, LICENSE, note)
                      for control, out, note in rows]
    return pairs


def main() -> None:
    pairs = build()
    n = write_jsonl(OUT, pairs)
    counts = {c: sum(p.control == c for p in pairs) for c in dict.fromkeys(p.control for p in pairs)}
    print(f"wrote {n} pairs to {OUT}: {counts}")


if __name__ == "__main__":
    main()
