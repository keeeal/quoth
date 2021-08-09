
import json, re
from pathlib import Path

from discord import Message # type: ignore

from utils.func import embed_message


def find_urls(content: str) -> list[str]:
    pattern = r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})'
    return re.findall(pattern, content)


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in \
    {'.bmp', '.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff'}


def is_video(filename: str) -> bool:
    return Path(filename).suffix.lower() in \
    {'.avi', '.flv', '.gif', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg', '.webm', '.wmv'}


def truncate(text: str, length: int = 128):
    return text[:length] + ('...' if len(text) > length else '')


# return a json payload in a discord code block
def media_posted(message: Message, quoth: Message) -> str:
    embed = embed_message(message)
    has_image = any(is_image(a.filename) for a in message.attachments)
    has_video = any(is_video(a.filename) for a in message.attachments)

    description = embed.description

    if not description and message.attachments:
        if has_image:
            description = 'Image'
        elif has_video:
            description = 'Video'

    tags = {'quoth'}

    if has_image:
        tags.update({'pic', 'picture', 'image', 'photo'})

    if has_video:
        tags.update({'vid', 'video', 'movie'})

    for url in find_urls(description):
        tags.update({'url', 'link', 'website'})

        for key in 'youtube', 'imgur', 'reddit', 'github', 'spotify':
            if key in url.lower().replace('.', ''):
                tags.add(key)

        if is_image(url):
            tags.update({'pic', 'picture', 'image', 'photo'})

        if is_video(url):
            tags.update({'vid', 'video', 'movie'})

    if message.pinned:
        tags.add('pin')

    if message.author.bot:
        tags.add('bot')

    tags.update({tag + 's' for tag in tags})

    tags.update({
        message.author.mention,
        message.channel.mention,
        str(message.created_at.year),
    })

    tags.update(map(str, message.reactions))

    payload = {
        'eventType': 'media_posted',
        'tags': sorted(list(tags)),
        'uri': message.jump_url,
        'channelId': str(quoth.channel.id),
        'messageId': str(quoth.id),
        'embed': {
            'description': description,
            'timestamp': embed.timestamp.isoformat(),
            'author': {
                'name': embed.author.name,
                'iconURL': embed.author.icon_url,
                'url': embed.author.url,
            }
        },
        'description': f'{message.author.name}: "{truncate(description)}"',
    }

    return f'```json\n{json.dumps(payload, indent=2)}```'
