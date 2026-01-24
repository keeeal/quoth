import logging
from contextlib import contextmanager
from logging import Formatter, Logger, StreamHandler
from time import time

from discord.utils import _ColourFormatter, stream_supports_colour


def get_logger(name: str | None = None) -> Logger:
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


@contextmanager
def log_time(logger: Logger, message: str):
    """
    Context manager to log the time taken for a block of code to execute.

    Args:
        logger (Logger): The logger to use for logging the elapsed time.
        message (str): The message to log with the elapsed time.
    """
    start_time = time()
    yield
    elapsed_time = time() - start_time
    logger.info(f"{message} took {elapsed_time:.2f} seconds")
