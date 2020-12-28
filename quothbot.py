
import os, asyncio
from itertools import chain
from configparser import ConfigParser
from random import choice

import discord

data = None


# return all messages from a guild
async def get_messages(guild):
    return list(chain(*await asyncio.gather(*map(
        lambda c: c.history(limit=None).flatten(),
        guild.text_channels
    ))))


# return a dictionary of guild: messages
async def get_data(client):
    return dict(zip(client.guilds,
        await asyncio.gather(*map(get_messages, client.guilds))
    ))


def embed_message(message):
    embed = discord.Embed(
        description=message.content,
        timestamp=message.created_at
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.avatar_url
    )

    # if attachments then choose one
    if message.attachments:
        embed.set_image(url=choice(message.attachments).url)

    return embed


def main(config_file):

    # load config file or create it
    config = ConfigParser()
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
        raise discord.LoginFailure(f'Empty token in "{config_file}"')

    # create client
    client = discord.Client()


    @client.event
    async def on_ready():
        global data

        print('Getting data...')
        data = await get_data(client)
        print('Ready to quoth')


    @client.event
    async def on_reaction_add(reaction, user):
        channel = reaction.message.channel
        if reaction.emoji != '🐦':
            return

        # report no data
        if not data:
            content = "I can't quoth right now, I'm reading messages."
            embed = discord.Embed(description=content)
            await channel.send(embed=embed)
            return

        # filter messages
        banned = lambda m: m.author.name in config['quothbot']['banlist']
        messages = filter(lambda m: not banned(m), data[channel.guild])

        # send random message
        await channel.send(embed=embed_message(choice(list(messages))))


    # start bot
    client.run(config['quothbot']['token'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', '-c', default='config.ini')
    main(**vars(parser.parse_args()))
