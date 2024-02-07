from random import choice, random
from typing import Optional

from discord import Attachment, Embed, Message


def get_content(message: Message) -> Optional[str]:
    if message.content:
        return message.content
    for embed in message.embeds:
        if embed.description:
            return embed.description


def get_random_attachment(message: Message) -> Optional[Attachment]:
    if message.attachments:
        return choice(message.attachments)


def embed_message(message: Message) -> Embed:
    content = get_content(message)
    attachment = get_random_attachment(message)

    if content is None and attachment is None:
        raise ValueError("Message has no content or attachments")

    if content and attachment:
        if random() < 0.5:
            attachment = None
        else:
            content = None

    avatar = message.author.avatar
    embed = Embed(
        description=content,
        timestamp=message.created_at,
    ).set_author(
        name=message.author.display_name,
        icon_url=None if avatar is None else avatar.url,
        url=message.jump_url,
    )

    if attachment:
        embed.set_image(url=attachment.url)

    return embed
