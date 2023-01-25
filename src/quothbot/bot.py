import logging
from asyncio import gather
from typing import Callable, Coroutine

from discord import Intents, Message, MessageType, TextChannel
from discord.ext.commands import Bot

from .data import QuothData
from .utils.message import embed_message


class QuothBot(Bot):
    def __init__(self, command_prefix: str):
        intents = Intents.default()
        intents.members = True
        super().__init__(command_prefix, intents=intents)

        self.data = QuothData()
        self.callbacks: list[Callable[[Message, Message], Coroutine]] = []
        self.filters: list[Callable[[Message], bool]] = []

        # By default, do not quoth other bots:
        self.add_filters(lambda m: not m.author.bot)

    def add_filters(self, *filters: Callable[[Message], bool]) -> None:
        self.filters.extend(filters)

    def add_callbacks(self, *callback: Callable[[Message, Message], Coroutine]) -> None:
        self.callbacks.extend(callback)

    async def quoth(
        self,
        channel: TextChannel,
        *filters: Callable[[Message], bool],
    ) -> None:
        try:
            message = self.data.get_random_message(channel.guild.id, *self.filters, *filters)
        except LookupError as error:
            logging.error(str(error))
            await channel.send(content=str(error))
            return

        logging.info(f"Quothing message {message.id} in {channel.name}")
        quoth = await channel.send(embed=embed_message(message))
        await gather(*[callback(message, quoth) for callback in self.callbacks])

    async def on_ready(self) -> None:
        logging.info("Ready to quoth")
        await gather(*map(self.data.add_guild, self.guilds))

    async def on_guild_join(self, guild) -> None:
        await self.data.add_guild(guild)

    async def on_message(self, message: Message) -> None:
        if message.type in [MessageType.default, MessageType.reply]:
            self.data.add_message(message)

        await self.process_commands(message)
