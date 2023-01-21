import json
from typing import Optional

from discord import Message
from discord.ext.commands import Bot, Cog, command, Context

from utils.message import embed_message
from utils.path import is_image, is_video
from utils.string import find_urls, truncate


class TopBot(Cog):
    def __init__(self, bot: Bot, comms: Optional[dict[str, str]] = None) -> None:
        self.bot = bot
        self.comms = comms if comms else {}

    @command()
    async def register(self, context: Context):
        self.comms[str(context.guild.id)] = str(context.channel.id)
        await context.send(
            f"{context.channel} is the comms channel for {context.guild}"
        )

    async def notify(self, message: Message, quoth: Message):
        if str(quoth.guild.id) in self.comms:
            channel = self.bot.get_channel(int(self.comms[str(quoth.guild.id)]))
            await channel.send(media_posted(message, quoth))


def media_posted(message: Message, quoth: Message) -> str:
    embed = embed_message(message)
    has_image = any(is_image(a.filename) for a in message.attachments)
    has_video = any(is_video(a.filename) for a in message.attachments)

    description = embed.description.replace("```", "`\u200B`\u200B`")

    if not description and message.attachments:
        if has_image:
            description = "Image"
        elif has_video:
            description = "Video"

    tags = {"quoth"}

    if has_image:
        tags.update({"pic", "picture", "image", "photo"})

    if has_video:
        tags.update({"vid", "video", "movie"})

    for url in find_urls(description):
        tags.update({"url", "link", "website"})

        for key in "youtube", "imgur", "reddit", "github", "spotify":
            if key in url.lower().replace(".", ""):
                tags.add(key)

        if is_image(url):
            tags.update({"pic", "picture", "image", "photo"})

        if is_video(url):
            tags.update({"vid", "video", "movie"})

    if message.pinned:
        tags.add("pin")

    if message.author.bot:
        tags.add("bot")

    tags.update({tag + "s" for tag in tags})

    tags.update({
        message.author.mention,
        message.channel.mention,
        str(message.created_at.year),
    })

    tags.update(map(str, message.reactions))

    payload = {
        "eventType": "media_posted",
        "tags": sorted(list(tags)),
        "uri": message.jump_url,
        "channelId": str(quoth.channel.id),
        "messageId": str(quoth.id),
        "embed": {
            "description": description,
            "timestamp": embed.timestamp.isoformat(),
            "author": {
                "name": embed.author.name,
                "iconURL": embed.author.icon_url,
                "url": embed.author.url,
            },
        },
        "description": f'{message.author.name}: "{truncate(description)}"',
    }

    return f"```json\n{json.dumps(payload, indent=2)}```"


def setup(bot: Bot):
    bot.add_cog(TopBot(bot))
