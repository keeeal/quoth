from argparse import ArgumentParser
from asyncio import new_event_loop
from pathlib import Path

from quoth.bot import QuothBot
from quoth.ext import Commands, Quoth, React
from quoth.utils.config import Config, read_from_env_var
from quoth.utils.logging import get_logger

LOGGER = get_logger(__name__)


def main(config_file: Path) -> None:
    try:
        token = read_from_env_var("DISCORD_TOKEN_FILE")
    except Exception as error:
        LOGGER.error(error)
        return

    config = Config.from_yaml(config_file, create_if_not_found=True)
    bot = QuothBot(**config.bot.model_dump())
    loop = new_event_loop()

    LOGGER.info("Adding cogs to bot")
    loop.run_until_complete(bot.add_cog(Commands(bot)))
    if config.quoth:
        loop.run_until_complete(bot.add_cog(Quoth(bot, **config.quoth.model_dump())))
    if config.react:
        loop.run_until_complete(bot.add_cog(React(bot, **config.react.model_dump())))

    LOGGER.info("Starting main loop")
    loop.run_until_complete(bot.initialize())
    loop.run_until_complete(bot.start(token))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config-file", type=Path, default="config.yaml")
    main(**vars(parser.parse_args()))
