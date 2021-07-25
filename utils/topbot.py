
import json
from pathlib import Path

from discord import Attachment, Message  # type: ignore


def is_image(attachment: Attachment) -> bool:
    return Path(attachment.filename).suffix.lower() in \
    {'.bmp', '.gif', '.jpeg', '.jpg', '.png', '.tif', '.tiff'}


def is_video(attachment: Attachment) -> bool:
    return Path(attachment.filename).suffix.lower() in \
    {'.avi', '.flv', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg', '.wmv'}


# return a json payload in a discord code block
def media_posted(message: Message, quoth: Message) -> str:
    payload = {
        'eventType': 'media_posted',
        'tags': ['quoth'],
        'uri': message.jump_url,
        'description': message.clean_content.replace('```', ''),
        'messageId': str(quoth.id),
        'channelId': str(quoth.channel.id),
    }

    if message.pinned:
        payload['tags'].append('pin')

    if message.attachments:
        if any(map(is_image, message.attachments)):
            payload['tags'] += ['pic', 'picture', 'image', 'photo']

            if not payload['description']:
                payload['description'] = f'Image by {message.author.name}'

        elif any(map(is_video, message.attachments)):
            payload['tags'] += ['vid', 'video', 'movie']

            if not payload['description']:
                payload['description'] = f'Video by {message.author.name}'

    # add plurals
    for tag in list(payload['tags']):
        payload['tags'].append(tag + 's')

    payload['tags'] += [
        f'<@!{message.author.id}>',
        str(message.channel),
        str(message.created_at.year),
    ]

    return f'```json\n{json.dumps(payload, indent=2)}```'
