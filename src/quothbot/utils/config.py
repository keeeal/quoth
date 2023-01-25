import logging
from json import dump, load
from pathlib import Path
from typing import Any, Optional


def read_config(
    file: Path,
    default: Optional[dict[str, dict[str, Any]]] = None,
) -> Optional[dict[str, dict[str, Any]]]:
    if file.is_file():
        logging.info(f"Reading: {file}")
        with open(file) as f:
            return load(f)
    elif default:
        logging.info(f"Creating: {file}")
        with open(file, "w") as f:
            dump(default, f, indent=2)
        return default
    else:
        logging.info(f"Not found: {file}")
