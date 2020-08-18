
import os, asyncio, json
from itertools import chain
from datetime import date
from random import choice

import discord

data = None


# return a list of messages
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


def main(config_file):

    # load config file or create it
    if os.path.isfile(config_file):
        with open(config_file) as f:
            config = json.load(f)
        config['birthdays'] = {k: date.fromisoformat(v)
            for k, v in config['birthdays'].items()}
    else:
        config = {
            'token': '',
            'banlist': ['QuothBot'],
            'birthdays': {},
        }
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    # check for auth token
    if not config['token']:
        print('Error: Token not found.')
        print('Copy bot token into "{}"'.format(config_file))
        return

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
        if reaction.emoji == '🐦':

            # report no data
            if not data:
                msg = "I can't quoth right now, I'm reading messages."
                embed = discord.Embed(description=msg)
                await channel.send(embed=embed)
                return

            # choose a message
            # TODO: change data structure to make this more efficient
            for sample in range(1000):
                message = choice(data[channel.guild])
                name = message.author.name

                # respect banlist
                if name in config['banlist']:
                    continue

                # check for birthdays
                for key, value in config['birthdays'].items():
                    value = date(date.today().year, value.month, value.day)
                    if value == date.today():
                        if name != key:
                            continue

                break
            else:
                msg = "I couldn't find a message."
                embed = discord.Embed(description=msg)
                await channel.send(embed=embed)
                return

            # get author nickname and avatar
            icon_url = message.author.default_avatar_url
            if isinstance(message.author, discord.Member):
                icon_url = message.author.avatar_url
                if message.author.nick:
                    name = message.author.nick

            # embed with author and timestamp
            embed = discord.Embed(
                description=message.content, timestamp=message.created_at)
            embed.set_author(name=name, icon_url=icon_url)

            # if attachments then choose one
            if message.attachments:
                embed.set_image(url=choice(message.attachments).url)

            # send to reaction channel
            await channel.send(embed=embed)


    # start bot
    client.run(config['token'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', '-c', default='config.json')
    main(**vars(parser.parse_args()))
