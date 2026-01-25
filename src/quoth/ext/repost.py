from dataclasses import dataclass
from datetime import datetime
from string import Template

from discord import Embed, Message
from discord.ext.commands import Cog

from quoth.bot import QuothBot
from quoth.data import MessageRecord
from quoth.utils.logging import get_logger
from quoth.utils.message import get_content

LOGGER = get_logger(__name__)


DESCRIPTION = Template("""
Said ${num_reposts} times before!
First said: [${first_date}](${first_url}) by ${first_user}
Last said: [${last_date}](${last_url}) by ${last_user}
""")


def truncate(content: str, max_length: int) -> str:
    if len(content) <= max_length:
        return content
    return content[: max_length - 3] + "..."


def embed(
    content: str,
    num_reposts: int,
    first_record: MessageRecord,
    last_record: MessageRecord,
    time_format: str = "%d %b %Y",
) -> Embed:
    return Embed(
        title=f"{truncate(content, 32)}",
        description=DESCRIPTION.substitute(
            {
                "num_reposts": num_reposts,
                "first_date": first_record.created_at.strftime(time_format),
                "first_user": first_record.display_name,
                "first_url": first_record.jump_url,
                "last_date": last_record.created_at.strftime(time_format),
                "last_user": last_record.display_name,
                "last_url": last_record.jump_url,
            }
        ),
    )


@dataclass
class Repost(Cog):
    bot: QuothBot
    cooldown_seconds: float
    min_content_chars: int
    min_occurances: int

    def __post_init__(self):
        self.last_repost_time = 0.0

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return
        if message.guild is None:
            return
        content = get_content(message)
        if content is None:
            return
        if len(content) < self.min_content_chars:
            return

        cooldown_time = self.cooldown_seconds - (
            self.bot.loop.time() - self.last_repost_time
        )
        if cooldown_time > 0:
            return

        records = [
            record
            for record in await self.bot.data.fetch_records(
                guild_id=message.guild.id,
                content=content,
            )
            if record.message_id != message.id
        ]
        if len(records) < self.min_occurances:
            return

        self.last_repost_time = self.bot.loop.time()
        first_record = min(records, key=lambda r: r.created_at)
        last_record = max(records, key=lambda r: r.created_at)
        repost_embed = embed(
            content=content,
            num_reposts=len(records),
            first_record=first_record,
            last_record=last_record,
        )
        await message.reply(embed=repost_embed)
