from asyncio import gather
from collections import defaultdict
from random import choice
from threading import Lock
from typing import Callable

from discord import Guild, Message, TextChannel
from discord.errors import Forbidden


class QuothData:
    def __init__(self):
        self.guilds: dict[int, dict[int, Message]] = defaultdict(dict)
        self.locks: dict[int, Lock] = defaultdict(Lock)

    def add_message(self, message: Message):
        if (guild_id := message.guild.id) is not None:
            with self.locks[guild_id]:
                self.guilds[guild_id][message.id] = message

    async def add_channel(self, channel: TextChannel):
        try:
            async for message in channel.history(limit=None):
                self.add_message(message)
        except Forbidden:
            pass

    async def add_guild(self, guild: Guild):
        await gather(*map(self.add_channel, guild.text_channels))

    def get_messages(
        self, guild_id: int, *filters: Callable[[Message], bool]
    ) -> list[Message]:
        if guild_id not in self.guilds:
            raise LookupError("Guild ID not in data.")

        with self.locks[guild_id]:
            messages = self.guilds[guild_id].values()

            for f in filters:
                messages = filter(f, messages)

            return list(messages)

    def get_random_message(
        self, guild_id: int, *filters: Callable[[Message], bool]
    ) -> Message:
        if len(messages := self.get_messages(guild_id, *filters)) == 0:
            raise LookupError("No valid messages.")

        message = choice(messages)

        if len(message.attachments):
            message.attachments = [choice(message.attachments)]

        return message
