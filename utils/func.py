
import os
from configparser import ConfigParser

import discord # type: ignore

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
    if message.embeds and not message.content:
        description = message.embeds[0].description
    else:
        description = message.content

    embed = discord.Embed(
        description = description,
        timestamp = message.created_at,
    ).set_author(
        name = message.author.display_name,
        icon_url = message.author.avatar,
        url = message.jump_url,
    )

    if message.attachments:
        embed.set_image(url = message.attachments[0].url)

    return embed
