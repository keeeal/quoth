from collections import Counter
from itertools import chain
from typing import Optional

from discord import Embed, Message, User

from .path import is_image, is_video
from .string import find_urls, str_filter


def embed_message(message: Message) -> Embed:
    if message.embeds and not message.content:
        description = message.embeds[0].description
    else:
        description = message.content

    embed = Embed(description=description, timestamp=message.created_at).set_author(
        name=message.author.display_name,
        icon_url=message.author.avatar.url,
        url=message.jump_url,
    )

    if message.attachments:
        embed.set_image(url=message.attachments[0].url)

    return embed


def get_first(messages: list[Message]) -> Message:
    return sorted(messages, key=lambda m: m.created_at)[0]


def get_last(messages: list[Message]) -> Message:
    return sorted(messages, key=lambda m: m.created_at)[-1]


def max_length(messages: list[Message]) -> int:
    return max(messages, key=lambda m: len(m.content))


def most_used_word(messages: list[Message]) -> str:
    words = Counter(chain(*(m.content.split() for m in messages)))
    return words.most_common(1)[0][0]


def most_tagged_id(messages: list[Message]) -> int:
    tags = Counter(chain(*((u.id for u in m.mentions) for m in messages)))
    return tags.most_common(1)[0][0] if len(tags) else None


def on_day(message: Message, day: int) -> bool:
    return message.created_at.weekday() == day % 7


def on_year(message: Message, year: int) -> bool:
    return message.created_at.year == year


def has_tag(message: Message, user: Optional[User] = None) -> bool:
    if user:
        return user in message.mentions
    else:
        return len(message.mentions) > 0


def has_url(message: Message, substring: Optional[str] = None) -> bool:
    urls = find_urls(message.content)

    if substring:
        urls = filter(
            lambda url: substring.lower() in str_filter(str.isalnum, url).lower(), urls
        )

    return len(list(urls)) > 0


def has_text(message: Message, substring: Optional[str] = None) -> bool:
    text = message.content.strip()

    if substring:
        return substring.lower() in text.lower()
    else:
        return len(text) > 0


def has_image(message: Message) -> bool:
    return any(is_image(a.filename) for a in message.attachments)


def has_video(message: Message) -> bool:
    return any(is_video(a.filename) for a in message.attachments)
