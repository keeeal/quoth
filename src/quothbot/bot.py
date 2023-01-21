import logging
from asyncio import gather
from typing import Callable

from discord import Intents, Message, MessageType, TextChannel
from discord.ext.commands import Bot
from discord.utils import setup_logging

from .utils.message import embed_message
from .data import QuothData


_log = logging.getLogger(__name__)
setup_logging()


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
        *filters: Callable[[Message], bool],
    ):
        _filters = list(filters)
        _filters.append(lambda m: not m.author.bot)
        _filters.append(lambda m: m.author.name not in self.banlist)

        # if (topbot := self.get_cog("TopBot")):
        #     _filters.append(topbot.message_not_in_comms_channel)

        try:
            message = self.data.get_random_message(channel.guild.id, *_filters)
        except LookupError as error:
            await channel.send(content=str(error))
        else:
            await channel.send(embed=embed_message(message))

            # if topbot:
            #     await topbot.notify(message, quoth)

    async def on_ready(self):
        _log.info("Ready to quoth")
        await gather(*map(self.data.add_guild, self.guilds))

    async def on_guild_join(self, guild):
        await self.data.add_guild(guild)

    async def on_message(self, message: Message):
        if message.type in [MessageType.default, MessageType.reply]:
            self.data.add_message(message)

        await self.process_commands(message)
