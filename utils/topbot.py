
import json, re
from pathlib import Path

from discord import Attachment, Message  # type: ignore


def find_urls(content: str) -> list[str]:
    pattern = r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})'
    return re.findall(pattern, content)


def is_image(attachment: Attachment) -> bool:
    return Path(attachment.filename).suffix.lower() in \
    {'.bmp', '.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff'}


def is_video(attachment: Attachment) -> bool:
    return Path(attachment.filename).suffix.lower() in \
    {'.avi', '.flv', '.gif', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg', '.wmv'}


# return a json payload in a discord code block
def media_posted(message: Message, quoth: Message) -> str:
    has_image = any(map(is_image, message.attachments))
    has_video = any(map(is_video, message.attachments))

    payload = {
        'eventType': 'media_posted',
        'tags': ['quoth'],
        'uri': message.jump_url,
        'description': f'{message.author.name}: ',
        'messageId': str(quoth.id),
        'channelId': str(quoth.channel.id),
    }

    # description
    if message.content:
        payload['description'] += '"' + message.clean_content.replace('```', '') + '"'
    elif message.attachments:
        if has_image:
            payload['description'] += 'Image'
        elif has_video:
            payload['description'] += 'Video'

    # tags
    if has_image:
        payload['tags'] += ['pic', 'picture', 'image', 'photo']

    if has_video:
        payload['tags'] += ['vid', 'video', 'movie']

    if message.pinned:
        payload['tags'].append('pin')

    # plurals
    for key in list(payload['tags']):
        payload['tags'].append(key + 's')

    payload['tags'] += [
        message.author.mention,
        message.channel.mention,
        str(message.created_at.year),
    ]

    return f'```json\n{json.dumps(payload, indent=2)}```'
