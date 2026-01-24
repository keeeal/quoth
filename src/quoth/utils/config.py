from __future__ import annotations

from os import getenv
from pathlib import Path

from pydantic import BaseModel
from yaml import safe_dump, safe_load


class BotConfig(BaseModel):
    command_prefix: str


class QuothConfig(BaseModel):
    emoji: str
    cooldown_seconds: float


class ReactConfig(BaseModel):
    emoji: str
    trigger_word: str


class RepostConfig(BaseModel):
    cooldown_seconds: float
    min_content_chars: int
    min_occurances: int


class Config(BaseModel):
    bot: BotConfig
    quoth: QuothConfig | None = None
    react: ReactConfig | None = None
    repost: RepostConfig | None = None

    @classmethod
    def from_yaml(cls, file: Path) -> Config:
        if not file.is_file():
            raise FileNotFoundError(file)
        with open(file) as f:
            return Config.model_validate(safe_load(f))


def read_from_env_var(key: str, is_file: bool | None = None) -> str:
    if not (value := getenv(key)):
        raise KeyError(f"The env var '{key}' is not set")

    if is_file or (is_file is None and key.lower().endswith("_file")):
        with open(value) as f:
            return f.readline().strip()
    else:
        return value
