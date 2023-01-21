
from argparse import ArgumentParser
from pathlib import Path

from .quothbot import QuothBot
from .utils.config import load_config


DEFAULT_CONFIG = {"bot": {"token": "", "banlist": ["QuothBot"]}, "comms": {}}


def main(config_file: Path, topbot: bool = False):
    config = load_config(config_file, DEFAULT_CONFIG)

    if not config["bot"]["token"]:
        print(f"No token in '{config_file}'")
        return

    bot = QuothBot(config["bot"]["banlist"])

    if topbot:
        from ext.topbot import TopBot

        bot.add_cog(TopBot(bot, config["comms"]))

    bot.run(config["bot"]["token"])


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config-file", type=Path, default="/config/config.ini")
    parser.add_argument("-top", "--topbot", action="store_true")
    main(**vars(parser.parse_args()))
