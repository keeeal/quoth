from discord import Embed, Message


def embed_message(message: Message) -> Embed:
    if message.embeds and not message.content:
        description = message.embeds[0].description
    else:
        description = message.content

    avatar = message.author.avatar
    embed = Embed(
        description=description,
        timestamp=message.created_at,
    ).set_author(
        name=message.author.display_name,
        icon_url=None if avatar is None else avatar.url,
        url=message.jump_url,
    )

    if message.attachments:
        embed.set_image(url=message.attachments[0].url)

    return embed
