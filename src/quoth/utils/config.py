from __future__ import annotations

from os import getenv
from pathlib import Path

from pydantic import BaseModel
from yaml import safe_dump, safe_load


class BotConfig(BaseModel):
    command_prefix: str = "!"
    model_name: str = "choose-your-model"


class QuothConfig(BaseModel):
    emoji: str = "🐦"


class ReactConfig(BaseModel):
    emoji: str = "🤔"


class Config(BaseModel):
    bot: BotConfig = BotConfig()
    quoth: QuothConfig | None = QuothConfig()
    react: ReactConfig | None = ReactConfig()

    @classmethod
    def from_yaml(cls, file: Path, create_if_not_found: bool = False) -> Config:
        if file.is_file():
            with open(file) as f:
                return Config(**safe_load(f))
        elif create_if_not_found:
            config = cls()
            with open(file, "w") as f:
                safe_dump(config.model_dump(), f, allow_unicode=True, sort_keys=False)
            return config

        raise FileNotFoundError(str(file))


def read_from_env_var(key: str, is_file: bool | None = None) -> str:
    if not (value := getenv(key)):
        raise ValueError(f"The env var '{key}' is not set")

    if is_file or (is_file is None and key.lower().endswith("_file")):
        with open(value) as f:
            return f.readline().strip()
    else:
        return value
