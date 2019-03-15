
import os, asyncio, json, discord
from random import choice

def load_messages(json_file,
        bots=[], whitelist=[], blacklist=[],
        urls=False, tags=False):

    with open(json_file) as f:
        data = json.load(f)

    messages = {}
    usernames = {k:v['name'] for k, v in data['meta']['users'].items()}
    idx = data['meta']['userindex']

    for channel_id, channel_data in data['data'].items():
        for message_id, message_data in channel_data.items():

            # get username
            u = usernames[idx[message_data['u']]]
            if len(whitelist) and u not in whitelist:
                continue
            if u in blacklist:
                continue

            # get message
            if 'm' in message_data:
                m = message_data['m']

                # filter messages
                for sign in bots:
                    if m.startswith(sign):
                        m = ''
                if not urls:
                    if 'http' in m or 'www.' in m:
                        m = ''
                if not tags:
                    if m.startswith('<@') and m.endswith('>'):
                        m = ''

                if not m: continue
                if u not in messages: messages[u] = []
                messages[u].append(m)

    return messages

def embed(channel, user, message):
    for member in channel.guild.members:
        avatar = member.default_avatar_url
        if member.name == user:
            if member.nick: user = member.nick
            avatar = member.avatar_url
            break

    embed = discord.Embed(description=message)
    embed.set_author(name=user, icon_url=avatar)
    return embed

def main(json_file, config_file=None):

    # load config file or create it
    if not config_file:
        config_file = 'config.txt'
    if os.path.isfile(config_file):
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {
            'token': '',
            'bot signs': ['!', '-', ';;', '>>'],
            'user whitelist': [],
            'user blacklist': [],
            'allow urls': False,
            'allow lone tags': False,
        }
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    # check for auth token
    if not config['token']:
        print('Error: Token not found.')
        print('Copy bot token into "{}"'.format(config_file))
        return

    # load data
    print('\nLoading {}...'.format(json_file))
    messages = load_messages(json_file,
        bots=config['bot signs'],
        whitelist=config['user whitelist'],
        blacklist=config['user blacklist'],
        urls=config['allow urls'],
        tags=config['allow lone tags'],
    )
    n_messages = [(len(m), u) for u, m in messages.items()]
    for n, u in sorted(n_messages, reverse=True):
        print('Loaded {}: {} messages'.format(u, n))

    # create client
    client = discord.Client()

    @client.event
    async def on_ready():
        print('Logged in as {}'.format(client.user.name))

    @client.event
    async def on_reaction_add(reaction, user):
        channel = reaction.message.channel
        if reaction.emoji == '🐦':
            user = choice(list(messages.keys()))
            message = choice(messages[user])
            await channel.send(embed=embed(channel, user, message))

    # start bot
    client.run(config['token'])

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('json_file')
    parser.add_argument('--config_file', '-c')
    main(**vars(parser.parse_args()))
