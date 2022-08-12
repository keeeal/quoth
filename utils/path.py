from pathlib import Path
from typing import Union


def is_image(file: Union[Path, str]) -> bool:
    return Path(file).suffix.lower() in {
        ".bmp",
        ".gif",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
    }


def is_video(file: Union[Path, str]) -> bool:
    return Path(file).suffix.lower() in {
        ".avi",
        ".flv",
        ".gif",
        ".m4v",
        ".mkv",
        ".mov",
        ".mp4",
        ".mpeg",
        ".mpg",
        ".webm",
        ".wmv",
    }
