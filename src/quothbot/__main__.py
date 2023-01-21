from argparse import ArgumentParser
from asyncio import run
from pathlib import Path

from .bot import QuothBot
from .ext.quoth import Quoth
from .ext.react import React
from .ext.topbot import TopBot
from .utils.config import load_config


DEFAULT_CONFIG = {"bot": {"token": "", "banlist": ["QuothBot"]}, "comms": {}}


def main(
    config_file: Path,
    react: bool = False,
    topbot: bool = False,
):
    config = load_config(config_file, DEFAULT_CONFIG)

    if not config["bot"]["token"]:
        print(f"No token in '{config_file}'")
        return

    bot = QuothBot(config["bot"]["banlist"])
    run(bot.add_cog(Quoth(bot, "🐦")))

    if react:
        bot.add_cog(React(bot, "🤔"))

    if topbot:
        bot.add_cog(TopBot(bot, config["comms"]))

    bot.run(config["bot"]["token"])


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config-file", type=Path, default="/config/config.ini")
    parser.add_argument("-r", "--react", action="store_true")
    parser.add_argument("-t", "--topbot", action="store_true")
    main(**vars(parser.parse_args()))
