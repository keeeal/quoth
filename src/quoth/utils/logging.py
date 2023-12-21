import logging
from logging import Formatter, Logger, StreamHandler
from typing import Optional

from discord.utils import _ColourFormatter, stream_supports_colour


def get_logger(name: Optional[str] = None) -> Logger:
    logger = logging.getLogger(name)
    handler = StreamHandler()
    formatter: Formatter

    if isinstance(handler, StreamHandler) and stream_supports_colour(handler.stream):
        formatter = _ColourFormatter()
    else:
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = Formatter(
            "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
