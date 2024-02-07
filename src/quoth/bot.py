from asyncio import gather
from typing import Callable, Coroutine, Optional

from discord import Guild, Intents, Message
from discord.abc import Messageable
from discord.ext.commands import Bot

from quoth.data import QuothData
from quoth.utils.logging import get_logger
from quoth.utils.message import embed_message

LOGGER = get_logger(__name__)

QuothCallback = Callable[[Message, Message, Message], Coroutine]


class QuothBot(Bot):
    def __init__(self, command_prefix: str):
        intents = Intents.default()
        intents.members = True
        super().__init__(command_prefix, intents=intents)

        self.data = QuothData(model_name="BAAI/bge-small-en-v1.5")
        self.callbacks: set[QuothCallback] = set()

    async def initialize(self) -> None:
        await self.data.initialize()

    async def fetch_message(self, channel_id: int, message_id: int) -> Message:
        channel = await self.fetch_channel(channel_id)
        if not isinstance(channel, Messageable):
            raise ValueError(f"{channel} is not messageable")

        return await channel.fetch_message(message_id)

    def add_callback(self, callback: QuothCallback) -> int:
        self.callbacks.add(callback)
        return hash(callback)

    def remove_callback(self, callback_id: int) -> Optional[QuothCallback]:
        for callback in self.callbacks:
            if hash(callback) == callback_id:
                self.callbacks.remove(callback)
                return callback
        return None

    async def quoth(self, origin: Message) -> None:
        if origin.guild is None:
            raise ValueError(f"Message {origin.id} is not in a guild")

        record = await self.data.get_random_message_record(origin.guild.id)
        message = await self.fetch_message(record.channel_id, record.message_id)
        quoth = await origin.channel.send(embed=embed_message(message))
        await gather(*[callback(origin, message, quoth) for callback in self.callbacks])

    async def on_ready(self) -> None:
        await gather(*map(self.data.add_guild, self.guilds))
        LOGGER.info("FINISHED DOWNLOAD")

    async def on_guild_join(self, guild: Guild) -> None:
        await self.data.add_guild(guild)

    async def on_message(self, message: Message) -> None:
        await gather(
            self.data.add_message(message),
            self.process_commands(message),
        )
