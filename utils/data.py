
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


class QuothData():
    def __init__(self):
        self.data = {}

    def update(self, message: Message) -> None:
        guild_id = message.guild.id

        if guild_id not in self.data:
            self.data[guild_id] = Atomic({})

        with self.data[guild_id].lock:
            self.data[guild_id].load[message.id] = message

    def get_random(self, guild_id: int,
        valid: Optional[Callable[[Message], bool]] = None
    ) -> Message:
        try:
            with self.data[guild_id].lock:
                message = choice(list(filter(
                    valid, self.data[guild_id].load.values()
                )))
        except KeyError:
            raise LookupError(f'Guild ID not in data.')
        except IndexError:
            raise LookupError(f'No valid messages.')

        if len(message.attachments) > 1:
            message.attachements = [choice(message.attachments)]

        return message
