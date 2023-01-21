from asyncio import gather
from collections import defaultdict
from random import choice
from threading import Lock
from typing import Callable, Optional

from discord import Guild, Message, TextChannel
from discord.errors import Forbidden


class QuothData:
    def __init__(self):
        self.guilds: defaultdict[int, dict[int, Message]] = defaultdict(dict)
        self.locks: defaultdict[int, Lock] = defaultdict(Lock)

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
        self, guild_id: int, _filter: Optional[Callable[[Message], bool]] = None
    ) -> list[Message]:
        if guild_id not in self.guilds:
            raise LookupError("Guild ID not in data.")

        with self.locks[guild_id]:
            return list(filter(_filter, self.guilds[guild_id].values()))

    def get_random_message(
        self, guild_id: int, _filter: Optional[Callable[[Message], bool]] = None
    ) -> Message:
        if len(messages := self.get_messages(guild_id, _filter)) == 0:
            raise LookupError("No valid messages.")

        message = choice(messages)

        if len(message.attachments) > 1:
            message.attachments = [choice(message.attachments)]

        return message
