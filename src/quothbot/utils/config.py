from configparser import ConfigParser
from pathlib import Path
from typing import Optional


def load_config(file: Path, default: Optional[dict] = None) -> ConfigParser:
    config = ConfigParser()

    if file.is_file():
        config.read(file)
    else:
        if default:
            for key, value in default.items():
                config[key] = value

        with open(file, "w") as f:
            config.write(f)

    return config
