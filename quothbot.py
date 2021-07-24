
import os, json
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from random import choice
from threading import Lock

import discord


class DotDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


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
        self.guilds = {}

    def update(self, message):
        guild_id = message.guild.id

        if guild_id not in self.guilds:
            self.guilds[guild_id] = Atomic({})

        with self.guilds[guild_id].lock:
            self.guilds[guild_id].load[message.id] = get_message(message)

    def get_random(self, guild_id, valid=None):
        if guild_id not in self.guilds:
            return None

        with self.guilds[guild_id].lock:
            messages = list(filter(valid, self.guilds[guild_id].load.values()))

        if not messages:
            return None

        return choice(messages)

    def to_disk(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)

        for guild_id in self.guilds:
            with open(path / f'{guild_id}.json', 'w') as f:
                with self.guilds[guild_id].lock:
                    json.dump(self.guilds[guild_id].load, f)

    def from_disk(self, path):
        for file in os.listdir(path):
            with open(path / file) as f:
                messages = json.load(f)

            guild_id = int(Path(file).stem)
            self.guilds[guild_id] = Atomic(messages)


def get_message(message):
    return DotDict(
        content = message.content,
        jump_url = message.jump_url,
        created_at = message.created_at.isoformat(),
        attachments = [
            DotDict(url = a.url)
            for a in message.attachments
        ],
        author = DotDict(
            name = message.author.name,
            display_name = message.author.display_name,
            avatar_url = message.author.avatar_url,
        ),
    )


# return a message with author and timestamp
def embed_message(message):
    embed = discord.Embed(
        description = message.content,
        timestamp = datetime.fromisoformat(message.created_at),
    ).set_author(
        name = message.author.display_name,
        icon_url = message.author.avatar_url,
        url = message.jump_url,
    )

    # if attachments then choose one
    if message.attachments:
        embed.set_image(url = choice(message.attachments).url)

    return embed


DATA = QuothData()


def main(config_file, data_dir):
    config = ConfigParser()

    # load config from file or create one
    if os.path.isfile(config_file):
        config.read(config_file)
    else:
        config['quothbot'] = {
            'token': '',
            'banlist': ['QuothBot'],
        }

        with open(config_file, 'w') as f:
            config.write(f)

    # check for auth token
    if not config['quothbot']['token']:
        raise discord.LoginFailure(f'No token in "{config_file}"')

    # load data from directory or create one
    if os.path.isdir(data_dir):
        DATA.from_disk(data_dir)
    else:
        os.mkdir(data_dir)

    # create client
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents = intents)

    @client.event
    async def on_ready():
        global DATA

        # update data
        for guild in client.guilds:
            for channel in guild.text_channels:
                try:
                    async for message in channel.history(limit=None):
                        DATA.update(message)
                except discord.errors.Forbidden:
                    pass

        # save data
        DATA.to_disk(data_dir)

    @client.event
    async def on_message(message):
        DATA.update(message)

        # react to "quoth" in message
        content = message.content.strip()
        if 'quoth' in content.lower().replace(' ', '') \
        or 'QUOTH' in ''.join(filter(str.isupper, content)):
            await message.add_reaction('🤔')

        # # process commands
        # prefix = '🐦'
        # if content.startswith(prefix):
        #     command, *args = content[len(prefix):].strip().split()

        #     if command ==  'comms':
        #         comms_channel_id = args[0]

    @client.event
    async def on_raw_reaction_add(event):
        if event.emoji.name !=  '🐦':
            return

        # get random message
        valid = lambda m: m.author.name not in config['quothbot']['banlist']
        message = DATA.get_random(event.guild_id, valid)

        if not message:
            print('no message')

        # send message
        channel = client.get_channel(event.channel_id)
        await channel.send(embed = embed_message(message))

    # start bot
    client.run(config['quothbot']['token'])


if __name__ ==  '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-file', type=Path, default='config.ini')
    parser.add_argument('-d', '--data-dir', type=Path, default='data')
    main(**vars(parser.parse_args()))
