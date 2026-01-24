from asyncio import gather
from random import choice, random

from discord import Embed, Forbidden, Guild, Intents, Message, NotFound
from discord.abc import Messageable
from discord.ext.commands import Bot
from requests import Response

from quoth.data import ConnectionPriority, MessageRecord, QuothData
from quoth.utils.logging import get_logger, log_time

LOGGER = get_logger(__name__)


def embed_record(record: MessageRecord) -> Embed:
    content = record.content
    attachment_url = choice(record.attachment_urls) if record.attachment_urls else None

    if content is None and attachment_url is None:
        raise ValueError("Message has no content or attachments")

    if content and attachment_url:
        if random() < 0.5:
            attachment_url = None
        else:
            content = None

    embed = Embed(
        description=content,
        timestamp=record.created_at,
    ).set_author(
        name=record.display_name,
        icon_url=record.avatar_url,
        url=record.jump_url,
    )

    if attachment_url:
        embed.set_image(url=attachment_url)

    return embed


class QuothBot(Bot):
    def __init__(self, command_prefix: str) -> None:
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix, intents=intents)

        self.data = QuothData()

    async def initialize(self) -> None:
        with log_time(LOGGER, "Initializing bot"):
            await self.data.initialize(priority=ConnectionPriority.high)

    async def fetch_message(
        self,
        message_id: int,
        channel_id: int | None = None,
    ) -> Message:
        if channel_id is not None:
            messageable = self.get_partial_messageable(channel_id)
            return await messageable.fetch_message(message_id)

        for channel in self.get_all_channels():
            if not isinstance(channel, Messageable):
                continue
            try:
                return await channel.fetch_message(message_id)
            except (Forbidden, NotFound):
                continue

        raise NotFound(Response(), f"Message {message_id} not found")

    async def fetch_record(
        self,
        message_id: int,
        channel_id: int | None = None,
    ) -> MessageRecord:
        record = await self.data.fetch_record(
            message_id,
            priority=ConnectionPriority.high,
        )
        if record is not None:
            return record

        LOGGER.warning(f"Cache miss for {message_id=}")
        message = await self.fetch_message(message_id, channel_id)
        return MessageRecord.from_message(message)

    async def quoth(self, origin: MessageRecord) -> None:
        if origin.guild_id is None:
            raise ValueError(f"Message {origin.message_id} is not in a guild")

        record = await self.data.fetch_random(
            guild_id=origin.guild_id,
            priority=ConnectionPriority.high,
        )
        messageable = self.get_partial_messageable(origin.channel_id)
        await messageable.send(embed=embed_record(record))

    async def on_ready(self) -> None:
        LOGGER.info(f"Logged in as {self.user}")
        await self.tree.sync()
        with log_time(LOGGER, "Downloading data"):
            await gather(*map(self.data.add_guild, self.guilds))

    async def on_guild_join(self, guild: Guild) -> None:
        await self.data.add_guild(guild, priority=ConnectionPriority.low)

    async def on_message(self, message: Message) -> None:
        await gather(
            self.data.add_message(message, priority=ConnectionPriority.low),
            self.process_commands(message),
        )
