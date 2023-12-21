from asyncio import gather
from typing import Callable, Coroutine

from discord import Guild, Intents, Message
from discord.abc import Messageable
from discord.ext.commands import Bot

from quoth.data import QuothData
from quoth.errors import NoGuild, NotMessageable
from quoth.utils.logging import get_logger
from quoth.utils.message import embed_message

LOGGER = get_logger(__name__)


class QuothBot(Bot):
    def __init__(self, command_prefix: str):
        intents = Intents.default()
        intents.members = True
        super().__init__(command_prefix, intents=intents)

        self.data = QuothData(fetch_message=self.fetch_message)
        self.callbacks: set[Callable[[Message, Message], Coroutine]] = set()

    async def initialize(self) -> None:
        await self.data.initialize()

    async def fetch_message(self, channel_id: int, message_id: int) -> Message:
        channel = await self.fetch_channel(channel_id)
        if not isinstance(channel, Messageable):
            raise NotMessageable(f"Channel {channel_id} is not messageable")

        return await channel.fetch_message(message_id)

    def add_callbacks(
        self, *callbacks: Callable[[Message, Message], Coroutine]
    ) -> None:
        self.callbacks.update(callbacks)

    def remove_callbacks(
        self, *callbacks: Callable[[Message, Message], Coroutine]
    ) -> None:
        self.callbacks.difference_update(callbacks)

    async def quoth(
        self,
        origin: Message,
        *filters: Callable[[Message], bool],
    ) -> None:
        if origin.guild is None:
            raise NoGuild(f"Message {origin.id} is not in a guild")

        message = await self.data.get_random_message(origin.guild.id)
        quoth = await origin.channel.send(embed=embed_message(message))
        await gather(*[callback(message, quoth) for callback in self.callbacks])

    async def on_ready(self) -> None:
        await gather(*map(self.data.add_guild, self.guilds))
        LOGGER.info("Finished initial download")

    async def on_guild_join(self, guild: Guild) -> None:
        await self.data.add_guild(guild)

    async def on_message(self, message: Message) -> None:
        await gather(
            self.data.add_message(message),
            self.process_commands(message),
        )
