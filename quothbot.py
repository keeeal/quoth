
import os
from asyncio import gather
from configparser import ConfigParser
from typing import Callable, Optional, Union

import discord # type: ignore
from discord.ext import commands # type: ignore
from discord_slash import SlashCommand, SlashContext # type: ignore
from discord_slash.utils.manage_commands import create_option # type: ignore

from utils.data import QuothData
from utils.topbot import media_posted


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
        icon_url = message.author.avatar,
        url = message.jump_url,
    )

    if message.attachments:
        embed.set_image(url = message.attachments[0].url)

    return embed


def main(config_file: str) -> None:
    config = load_config(config_file)

    if not config['bot']['token']:
        print(f'No token in "{config_file}"')
        return

    def not_banned(message: discord.Message) -> bool:
        return message.author.name not in config['bot']['banlist']

    # create client and data
    intents = discord.Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix = '🐦', intents = intents)
    slash = SlashCommand(bot, sync_commands = True)
    data = QuothData()

    async def send_quoth(
        channel: Union[discord.TextChannel, commands.Context, SlashContext],
        valid: Optional[Callable[[discord.Message], bool]] = None,
    ) -> None:
        try:
            message = data.random(channel.guild.id, valid)
        except LookupError as error_message:
            await channel.send(
                content = str(error_message),
                hidden = isinstance(channel, SlashContext),
            )
        else:
            quoth = await channel.send(embed = embed_message(message))

            # notify comms
            if str(channel.guild.id) in config['comms']:
                comms_channel_id = int(config['comms'][str(channel.guild.id)])
                comms_channel = bot.get_channel(comms_channel_id)
                await comms_channel.send(media_posted(message, quoth))

    async def add_channel(channel: discord.TextChannel) -> None:
        try:
            async for message in channel.history(limit = None):
                data.add(message)
        except discord.errors.Forbidden:
            pass

    async def add_guild(guild: discord.Guild) -> None:
        await gather(*map(add_channel, guild.text_channels))

    @bot.event
    async def on_guild_join(guild) -> None:
        await add_guild(guild)

    @bot.event
    async def on_ready() -> None:
        print('Ready to quoth')
        await gather(*map(add_guild, bot.guilds))

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.type == discord.MessageType.default:
            data.add(message)

        # react to "quoth" in message
        if message.author != bot.user:
            content = message.content.strip()
            if 'quoth' in content.lower().replace(' ', '') \
            or 'QUOTH' in ''.join(filter(str.isupper, content)):
                await message.add_reaction('🤔')

        # process commands
        await bot.process_commands(message)

    @bot.event
    async def on_raw_reaction_add(
        event: discord.RawReactionActionEvent
    ) -> None:
        if event.emoji.name == '🐦':
            await send_quoth(bot.get_channel(event.channel_id), not_banned)

    @slash.slash(
        description = 'Caw! Caw!',
        options = [
            create_option(
                name = "user",
                description = "Quoth a message from a user",
                option_type = 6,
                required = False,
            ),
        ]
    )
    async def quoth(
        context: SlashContext,
        user: Optional[discord.Member] = None,
    ) -> None:
        select_user = lambda m: m.author == user or user == None
        await send_quoth(
            channel = context,
            valid = lambda m: select_user(m) and not_banned(m)
        )

    @slash.slash(description = 'Register channel as comms')
    async def comms(context: SlashContext) -> None:
        config['comms'][str(context.guild_id)] = str(context.channel_id)
        await context.send('Registered comms channel.')

    @slash.slash(
        description = 'Count messages in server',
        options = [
            create_option(
                name = "user",
                description = "Count messages from a user",
                option_type = 6,
                required = False,
            ),
            create_option(
                name = "channel",
                description = "Count messages in a channel",
                option_type = 7,
                required = False,
            ),
        ]
    )
    async def count(
        context: SlashContext,
        user: Optional[discord.Member] = None,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        select_user = lambda m: m.author == user or user == None
        select_channel = lambda m: m.channel == channel or channel == None

        n_messages = len(data.filter(
            guild_id = context.guild_id,
            valid = lambda m: select_user(m) and select_channel(m),
        ))

        await context.send(
            f'{n_messages} messages' \
            + (f'by {user}' if user else '') \
            + (f'in {channel}' if channel else '')
        )

    # start bot
    bot.run(config['bot']['token'])



if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-file', default = 'config.ini')
    main(**vars(parser.parse_args()))
