
from random import choice
from threading import Lock
from typing import Callable, Optional

from discord import Message  # type: ignore


class Atomic:
    def __init__(self, value = None):
        self.lock = Lock()
        self._load = value
        self.exception = Exception('Acquire lock before accessing load.')

    @property
    def load(self):
        if not self.lock.locked():
            raise self.exception

        return self._load

    @load.setter
    def load(self, value) -> None:
        if not self.lock.locked():
            raise self.exception

        self._load = value


class QuothData(dict):
    def add(self, message: Message) -> None:
        guild_id = message.guild.id

        if guild_id not in self:
            self[guild_id] = Atomic({})

        with self[guild_id].lock:
            self[guild_id].load[message.id] = message

    def filter(self, guild_id: int,
        valid: Optional[Callable[[Message], bool]] = None
    ) -> list[Message]:
        if guild_id in self:
            with self[guild_id].lock:
                return list(filter(valid, self[guild_id].load.values()))
        else:
            raise LookupError('Guild ID not in data.')

    def random(self, guild_id: int,
        valid: Optional[Callable[[Message], bool]] = None
    ) -> Message:
        messages = self.filter(guild_id, valid)

        if len(messages):
            message = choice(messages)
        else:
            raise LookupError('No valid messages.')

        if len(message.attachments) > 1:
            message.attachements = [choice(message.attachments)]

        return message
