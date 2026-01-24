from discord import Message


def get_content(message: Message) -> str | None:
    if message.content:
        return message.content
    for embed in message.embeds:
        if embed.description:
            return embed.description
    return None
