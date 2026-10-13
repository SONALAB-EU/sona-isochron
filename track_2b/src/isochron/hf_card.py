"""The Hugging Face dataset card (data/hf_dataset/README.md): its field types, and whether it can be uploaded.

- features: scans every row of every file the card's `configs` list and writes the card's `dataset_info`
  block, each field's type in the YAML form of the datasets library. The card declares them because that
  library infers types from the first rows, so a field that is null throughout dev (the judge, the second
  NLI) would fail to load. Run it after isochron.hf_export build whenever the fields change.
- ready: fails while the card still holds a TODO or "[More Information Needed]", so it is not uploaded unfilled.

    uv run python -m isochron.hf_card features [--dir data/hf_dataset]
    uv run python -m isochron.hf_card ready [--dir data/hf_dataset]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

PLACEHOLDER = re.compile(r"\bTODO\b|\[More Information Needed\]")


def split_card(text: str) -> tuple[dict[str, Any], str]:
    """The YAML header as a dict, and the markdown body after it."""
    _, front, body = text.split("---\n", 2)
    return yaml.safe_load(front), body


def kind(value: Any) -> Any:
    """A JSON value's type: a dtype name, ("list", item type) or ("struct", ((field, type), ...)); None for null."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int64"
    if isinstance(value, float):
        return "float64"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        item = None
        for v in value:
            item = merge(item, kind(v))
        return ("list", item)
    if isinstance(value, dict):
        return ("struct", tuple((k, kind(v)) for k, v in value.items()))
    raise TypeError(f"no dtype for {value!r}")


def merge(a: Any, b: Any) -> Any:
    """The type that holds both: null gives way to anything, int64 to float64; anything else must agree."""
    if a is None or a == b:
        return b
    if b is None:
        return a
    if {a, b} == {"int64", "float64"}:
        return "float64"
    if isinstance(a, tuple) and isinstance(b, tuple) and a[0] == b[0] == "list":
        return ("list", merge(a[1], b[1]))
    if isinstance(a, tuple) and isinstance(b, tuple) and a[0] == b[0] == "struct":
        fa, fb = dict(a[1]), dict(b[1])
        return ("struct", tuple((k, merge(fa.get(k), fb.get(k))) for k in dict.fromkeys([*fa, *fb])))
    raise ValueError(f"conflicting types {a} and {b}")


def yaml_field(name: str, k: Any, where: str) -> dict[str, Any]:
    """One field in the card's YAML form: {name, dtype}, {name, list: dtype or fields}, {name, struct: fields}."""
    if k is None:
        raise ValueError(f"{where}.{name} is null in every row: its type cannot be declared")
    if isinstance(k, str):
        return {"name": name, "dtype": k}
    if k[0] == "struct":
        return {"name": name, "struct": [yaml_field(n, sub, f"{where}.{name}") for n, sub in k[1]]}
    item = k[1]
    if item is None:
        raise ValueError(f"{where}.{name} is an empty list in every row: its type cannot be declared")
    if isinstance(item, str):
        return {"name": name, "list": item}
    if item[0] == "struct":
        return {"name": name, "list": [yaml_field(n, sub, f"{where}.{name}") for n, sub in item[1]]}
    raise ValueError(f"{where}.{name}: nested lists are not supported")


def dataset_info(d: Path, configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    infos = []
    for config in configs:
        fields: dict[str, Any] = {}
        for data_file in config["data_files"]:
            for line in (d / data_file["path"]).read_text(encoding="utf-8").splitlines():
                for key, value in json.loads(line).items():
                    fields[key] = merge(fields.get(key), kind(value))
        infos.append({"config_name": config["config_name"],
                      "features": [yaml_field(k, t, config["config_name"]) for k, t in fields.items()]})
    return infos


def with_features(text: str, d: Path) -> str:
    """The card with its dataset_info block regenerated from the files, placed just before `configs`."""
    meta, body = split_card(text)
    meta["dataset_info"] = dataset_info(d, meta["configs"])
    keys = [k for k in meta if k not in ("configs", "dataset_info")] + ["dataset_info", "configs"]
    front = yaml.safe_dump({k: meta[k] for k in keys}, sort_keys=False, allow_unicode=True, width=120)
    return "---\n" + front + "---\n" + body


def placeholders(text: str) -> list[str]:
    """Every card line that still holds a TODO or "[More Information Needed]", with its line number."""
    return [f"{n}: {line.strip()}" for n, line in enumerate(text.splitlines(), 1) if PLACEHOLDER.search(line)]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("features", "ready"))
    ap.add_argument("--dir", type=Path, default=Path("data/hf_dataset"))
    args = ap.parse_args(argv)
    card = args.dir / "README.md"
    text = card.read_text(encoding="utf-8")
    if args.cmd == "features":
        new = with_features(text, args.dir)
        card.write_text(new, encoding="utf-8")
        print(f"{card}: dataset_info {'unchanged' if new == text else 'rewritten'}")
        return
    left = placeholders(text)
    if left:
        raise SystemExit(f"{card} is not ready to upload; fill in:\n" + "\n".join(left))
    print(f"{card}: no TODO or [More Information Needed] left")


if __name__ == "__main__":
    main()
