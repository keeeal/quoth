from configparser import ConfigParser
from pathlib import Path


def load_config(file: Path, default: dict) -> ConfigParser:
    config = ConfigParser()

    if file.is_file():
        config.read(file)
    else:
        for key, value in default:
            config[key] = value

        with open(file, "w") as f:
            config.write(f)

    return config
