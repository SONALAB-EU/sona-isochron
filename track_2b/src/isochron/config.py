"""LLM settings, read from the environment or a .env file.

Real environment variables take precedence over .env. Nothing is hardcoded:
if a required variable is missing, LLMConfig.from_env() raises.
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
    def from_env(cls, env_file: str | Path | None = ".env") -> LLMConfig:
        if env_file is not None:
            load_dotenv(env_file, override=False)
        missing = [k for k in REQUIRED if not os.environ.get(k)]
        if missing:
            raise ConfigError(
                f"missing environment variables: {', '.join(missing)} "
                "(set them or copy .env.example to .env)"
            )
        return cls(
            name=os.environ["LLM_NAME"],
            base_url=os.environ["LLM_BASE_URL"].rstrip("/"),
            api_key=os.environ["LLM_API_KEY"],
        )

    def __repr__(self) -> str:
        return f"LLMConfig(name={self.name!r}, base_url={self.base_url!r}, api_key='***')"
