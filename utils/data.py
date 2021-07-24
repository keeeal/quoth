
from random import choice
from threading import Lock


class Atomic:
    def __init__(self, value=None):
        self.lock = Lock()
        self._load = value
        self.exception = Exception('Acquire lock before accessing load.')

    @property
    def load(self):
        if not self.lock.locked():
            raise self.exception

        return self._load

    @load.setter
    def load(self, value):
        if not self.lock.locked():
            raise self.exception

        self._load = value


class QuothData():
    def __init__(self):
        self.data = {}

    def update(self, message):
        guild_id = message.guild.id

        if guild_id not in self.data:
            self.data[guild_id] = Atomic({})

        with self.data[guild_id].lock:
            self.data[guild_id].load[message.id] = message

    def get_random(self, guild_id, valid=None):
        try:
            with self.data[guild_id].lock:
                messages = filter(valid, self.data[guild_id].load.values())
                message = choice(list(messages))
        except LookupError:
            raise LookupError(f'No valid messages in this guild.')

        if len(message.attachments) > 1:
            message.attachements = [choice(message.attachments)]

        return message
