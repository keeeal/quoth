import logging
from json import dumps

from discord import Message
from discord.ext.commands import Cog, Context, command

from ..bot import QuothBot
from ..utils.message import embed_message, has_image, has_video
from ..utils.path import is_image, is_video
from ..utils.string import find_urls, truncate


class TopBot(Cog):
    def __init__(self, bot: QuothBot, **comms: str) -> None:
        self.bot = bot
        self.comms = comms
        self.bot.add_callbacks(self.notify)

    @command()
    async def register(self, context: Context):
        self.comms[str(context.guild.id)] = str(context.channel.id)
        info = f"{context.channel} is the comms channel for {context.guild}"
        logging.info(info)
        await context.send(info)

    async def notify(self, message: Message, quoth: Message):
        if str(quoth.guild.id) not in self.comms:
            logging.info(f"Guild {quoth.guild} has no comms channel")
            return

        logging.info(f"Notifying topbot of quoth {quoth.id}")
        channel = self.bot.get_channel(int(self.comms[str(quoth.guild.id)]))
        await channel.send(media_posted(message, quoth))

    def message_in_comms_channel(self, message: Message) -> bool:
        return str(message.channel.id) == self.comms.get(str(message.guild.id))


def media_posted(message: Message, quoth: Message) -> str:
    embed = embed_message(message)
    description = embed.description.replace("```", "`\u200B`\u200B`")

    if not description and message.attachments:
        if has_image(message):
            description = "Image"
        elif has_video(message):
            description = "Video"

    tags = {"quoth"}

    if has_image(message):
        tags.update({"pic", "picture", "image", "photo"})

    if has_video(message):
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

    payload = {
        "eventType": "media_posted",
        "tags": sorted(list(tags)),
        "uri": quoth.jump_url,
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

    return f"```json\n{dumps(payload, indent=2)}```"
