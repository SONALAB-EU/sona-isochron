"""LLM settings, read from the environment or a .env file.

Real environment variables take precedence over .env. Nothing is hardcoded:
if a required variable is missing, LLMConfig.from_env() raises.

The system under test (Apertus) uses LLM_NAME, LLM_BASE_URL and LLM_API_KEY.
The evaluation-only meaning judge uses the same three names with the JUDGE_
prefix: LLMConfig.from_env(prefix="JUDGE").
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REQUIRED = ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY")


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    name: str
    base_url: str
    api_key: str

    @classmethod
    def from_env(cls, env_file: str | Path | None = ".env", prefix: str = "LLM") -> LLMConfig:
        if env_file is not None:
            load_dotenv(env_file, override=False)
        keys = [k.replace("LLM", prefix, 1) for k in REQUIRED]
        missing = [k for k in keys if not os.environ.get(k)]
        if missing:
            raise ConfigError(
                f"missing environment variables: {', '.join(missing)} "
                "(set them or copy .env.example to .env)"
            )
        name, base_url, api_key = (os.environ[k] for k in keys)
        return cls(name=name, base_url=base_url.rstrip("/"), api_key=api_key)

    def __repr__(self) -> str:
        return f"LLMConfig(name={self.name!r}, base_url={self.base_url!r}, api_key='***')"
