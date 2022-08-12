from argparse import ArgumentParser
from asyncio import gather
from pathlib import Path
from typing import Callable, Optional

from discord import Intents, Message, MessageType, RawReactionActionEvent, TextChannel
from discord.ext.commands import Bot

from utils.config import load_config
from utils.message import embed_message
from utils.data import QuothData


DEFAULT_CONFIG = {"bot": {"token": "", "banlist": ["QuothBot"]}, "comms": {}}


class QuothBot(Bot):
    def __init__(self, banlist: list[str]):
        intents = Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        self.data = QuothData()
        self.banlist = banlist

    async def quoth(
        self,
        channel: TextChannel,
        _filter: Optional[Callable[[Message], bool]] = lambda _: True,
    ):
        def __filter(message: Message) -> bool:
            return all(
                [
                    _filter(message),
                    self.not_author_banned(message),
                    self.not_in_comms_channel(message),
                ]
            )

        try:
            message = self.data.get_random_message(channel.guild.id, __filter)
        except LookupError as error:
            await channel.send(content=str(error))
        else:
            quoth = await channel.send(embed=embed_message(message))

            if topbot := self.get_cog("TopBot"):
                await topbot.notify(message, quoth)

    async def on_ready(self):
        print("Ready to quoth")
        await gather(*map(self.data.add_guild, self.guilds))

    async def on_guild_join(self, guild):
        await self.data.add_guild(guild)

    async def on_message(self, message: Message):
        if message.type in [MessageType.default]:
            self.data.add_message(message)

        if message.author != self.user:
            content = message.content.lower()
            if "quoth" in "".join(i for i in content if i in "quoth"):
                await message.add_reaction("🤔")

        await self.process_commands(message)

    async def on_raw_reaction_add(self, event: RawReactionActionEvent):
        if event.emoji.name == "🐦":
            channel = self.get_channel(event.channel_id)
            await self.quoth(channel)

    def not_author_banned(self, message: Message) -> bool:
        return message.author.name not in self.banlist

    def not_in_comms_channel(self, message: Message) -> bool:
        if (topbot := self.get_cog("TopBot")) is None:
            return True

        return str(message.channel.id) != topbot.comms[str(message.guild.id)]


def main(config_file: Path, topbot: bool = False):
    config = load_config(config_file, DEFAULT_CONFIG)

    if not config["bot"]["token"]:
        print(f"No token in '{config_file}'")

    bot = QuothBot(config["bot"]["banlist"])

    if topbot:
        from ext.topbot import TopBot

        bot.add_cog(TopBot(bot, config["comms"]))

    bot.run(config["bot"]["token"])


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config-file", type=Path, default="config.ini")
    parser.add_argument("-top", "--topbot", action="store_true")
    main(**vars(parser.parse_args()))
