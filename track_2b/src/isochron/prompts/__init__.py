"""Prompt templates, one plain-text file per prompt and version.

Placeholders use string.Template syntax ($language, $target, $text), so the
JSON braces in the templates need no escaping.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from string import Template

PROMPTS = Path(__file__).parent
LANGUAGES = {"en": "English", "de": "German", "fr": "French", "it": "Italian"}


@dataclass(frozen=True)
class Prompt:
    name: str
    """File name without .txt, e.g. shorten_syllables_v1."""
    text: str

    @classmethod
    def load(cls, name: str) -> Prompt:
        return cls(name, (PROMPTS / f"{name}.txt").read_text(encoding="utf-8"))

    @property
    def version(self) -> str:
        return self.name.rsplit("_", 1)[-1]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def render(self, lang: str, target: int | None, text: str, **values: object) -> str:
        """Fill $language, $target, $text and any further $placeholders from values."""
        return Template(self.text).substitute(language=LANGUAGES[lang], target=target, text=text, **values)
