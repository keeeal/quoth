import logging
from argparse import ArgumentParser
from asyncio import run
from pathlib import Path

from .bot import QuothBot
from .ext.quoth import Quoth
from .ext.react import React
from .ext.topbot import TopBot
from .utils.config import read_config

DEFAULT_CONFIG = {
    "token": "",
    "bot": {
        "command_prefix": "!!!",
    },
    "quoth": {
        "emoji": "🐦",
    },
    "react": {
        "emoji": "🤔",
    },
    "topbot": {},
}


def main(config_file: Path):
    logging.basicConfig(level=logging.INFO)
    config = read_config(config_file, DEFAULT_CONFIG)

    if not config["token"]:
        print(f"No token in '{config_file}'")
        return

    bot = QuothBot(**config["bot"])

    if "quoth" in config:
        run(bot.add_cog(Quoth(bot, **config["quoth"])))

    if "react" in config:
        run(bot.add_cog(React(bot, **config["react"])))

    if "topbot" in config:
        run(bot.add_cog(TopBot(bot, **config["topbot"])))

    bot.run(config["token"])


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config-file", type=Path, default="/config/config.json")
    main(**vars(parser.parse_args()))
