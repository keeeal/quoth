
import os
from asyncio import gather
from configparser import ConfigParser

import discord # type: ignore

from utils.data import QuothData
from utils.topbot import media_posted


# global data
DATA = QuothData()


# update DATA with the messages in a channel
async def read_channel(channel: discord.TextChannel) -> None:
    try:
        async for message in channel.history(limit=None):
            DATA.update(message)
    except discord.errors.Forbidden:
        pass


# update DATA with the messages in a guild
async def read_guild(guild: discord.Guild) -> None:
    await gather(*map(read_channel, guild.text_channels))


# load config from file or create default
def load_config(path: str) -> ConfigParser:
    config = ConfigParser()

    if os.path.isfile(path):
        config.read(path)
    else:
        config['bot'] = {
            'token': '',
            'banlist': ['QuothBot'] # type: ignore
        }
        config['comms'] = {}

        with open(path, 'w') as f:
            config.write(f)

    return config


# return an embedded message with author and timestamp
def embed_message(message: discord.Message) -> discord.Embed:
    embed = discord.Embed(
        description = message.content,
        timestamp = message.created_at,
    ).set_author(
        name = message.author.display_name,
        icon_url = message.author.avatar_url,
        url = message.jump_url,
    )

    if message.attachments:
        embed.set_image(url = message.attachments[0].url)

    return embed


def main(config_file: str) -> None:

    # check config
    config = load_config(config_file)

    if not config['bot']['token']:
        print(f'No token in "{config_file}"')
        return

    # create client
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents = intents)


    # process message commands
    def process_commands(message: discord.Message, command: str, *args: str) -> str:
        if command == 'comms':
            try:
                comms_channel_id = int(args[0])
            except ValueError:
                return f'Invalid channel ID: {args[0]}'

            channel_ids = map(lambda c: c.id, message.guild.text_channels)

            if comms_channel_id not in channel_ids:
                return f'Channel ID not in guild: {comms_channel_id}'

            config['comms'][str(message.guild.id)] = str(comms_channel_id)

            with open(config_file, 'w') as f:
                config.write(f)

            comms_channel = client.get_channel(comms_channel_id)
            return f'Registered comms channel: {comms_channel}'
        else:
            return f'Unknown command: {command}'


    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.id == client.user.id:
            return

        # update DATA
        DATA.update(message)

        # react to "quoth" in message
        content = message.content.strip()
        if 'quoth' in content.lower().replace(' ', '') \
        or 'QUOTH' in ''.join(filter(str.isupper, content)):
            await message.add_reaction('🤔')

        # process commands
        prefix = '🐦'
        if content.startswith(prefix):
            command, *args = content[len(prefix):].strip().split()
            reply = process_commands(message, command, *args)

            if reply:
                await message.channel.send(reply)


    @client.event
    async def on_raw_reaction_add(event: discord.RawReactionActionEvent) -> None:
        if event.emoji.name != '🐦':
            return

        # send random message
        channel = client.get_channel(event.channel_id)
        valid = lambda m: m.author.name not in config['bot']['banlist']

        try:
            message = DATA.get_random(event.guild_id, valid)
        except LookupError as e:
            await channel.send(str(e))

        quoth = await channel.send(embed = embed_message(message))

        # notify comms
        guild_id_str = str(event.guild_id)

        if guild_id_str in config['comms']:
            comms_channel_id = int(config['comms'][guild_id_str])
            comms_channel = client.get_channel(comms_channel_id)
            await comms_channel.send(media_posted(message, quoth))


    @client.event
    async def on_ready() -> None:
        print('Ready to quoth')

        # update DATA
        await gather(*map(read_guild, client.guilds))


    # start bot
    client.run(config['bot']['token'])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-file', default='config.ini')
    main(**vars(parser.parse_args()))
