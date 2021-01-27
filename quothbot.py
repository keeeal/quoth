
import os, configparser
from asyncio import gather
from itertools import chain
from random import choice

import discord

data = None


# return all messages from a guild
async def get_messages(guild):
    return list(chain(*await gather(*map(
        lambda c: c.history(limit=None).flatten(),
        guild.text_channels
    ))))


# return a dictionary of guild: messages
async def get_data(client):
    return dict(zip(client.guilds,
        await gather(*map(get_messages, client.guilds))
    ))


# return a message with author and timestamp
def embed_message(message):
    embed = discord.Embed(
        description=message.content,
        timestamp=message.created_at,
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.avatar_url,
        url=message.jump_url,
    )

    # if attachments then choose one
    if message.attachments:
        embed.set_image(url=choice(message.attachments).url)

    return embed


def main(config_file):

    # load config file or create it
    config = configparser.ConfigParser()
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

    # create client
    client = discord.Client()


    # initial server scrape
    @client.event
    async def on_ready():
        global data

        print('Getting data...')
        data = await get_data(client)
        print('Ready to quoth')


    # live updating
    @client.event
    async def on_message(message):
        if data:
            data[message.guild].append(message)


    # respond
    @client.event
    async def on_raw_reaction_add(event):
        if event.emoji.name != '🐦':
            return
        
        channel = client.get_channel(event.channel_id)

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
    parser.add_argument('-c', '--config-file', default='config.ini')
    main(**vars(parser.parse_args()))
