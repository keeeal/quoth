from asyncio import gather
from functools import partial
from random import choice, random
from typing import Callable, Coroutine

from discord import Embed, Guild, Intents, Message
from discord.abc import Messageable
from discord.ext.commands import Bot

from quoth.data import ConnectionPriority, MessageRecord, QuothData
from quoth.errors import NotMessageable
from quoth.model import SentenceTransformerModel
from quoth.utils.logging import get_logger

LOGGER = get_logger(__name__)

# Type alias for an async callback to be called when a quoth is created.
#
# Args:
#   1. (MessageRecord): The original message that triggered the quoth.
#   2. (MessageRecord): The message record that was selected to be quoted.
#   3. (Message): The message that was sent as the quoth.
#
# Returns:
#   Coroutine: A coroutine to be awaited.
#
QuothCallback = Callable[[MessageRecord, MessageRecord, Message], Coroutine]


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
    def __init__(self, command_prefix: str, model_name: str) -> None:
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix, intents=intents)

        self.model = SentenceTransformerModel(model_name)
        self.data = QuothData(model=self.model)
        self.callbacks: dict[int, QuothCallback] = {}

    async def initialize(self) -> None:
        LOGGER.info("Initializing bot")
        await self.data.initialize(priority=ConnectionPriority.high)

    def get_messageable(self, channel_id: int) -> Messageable:
        channel = self.get_channel(channel_id)
        if not isinstance(channel, Messageable):
            raise NotMessageable(channel)
        return channel

    async def get_record(self, message_id: int, channel_id: int) -> MessageRecord:
        record = await self.data.get_record(
            message_id, channel_id, priority=ConnectionPriority.high
        )
        if record is not None:
            return record

        LOGGER.warning(f"Cache miss for {message_id=}")
        channel = self.get_messageable(channel_id)
        message = await channel.fetch_message(message_id)
        return MessageRecord.from_message(message)

    def add_callback(self, callback: QuothCallback) -> int:
        callback_id = hash(callback)
        self.callbacks[callback_id] = callback
        return callback_id

    def pop_callback(self, callback_id: int) -> QuothCallback | None:
        return self.callbacks.pop(callback_id, None)

    async def quoth(self, origin: MessageRecord) -> None:
        if origin.guild_id is None:
            raise ValueError(f"Message {origin.message_id} is not in a guild")

        record = await self.data.get_random(
            origin.guild_id,
            priority=ConnectionPriority.high,
        )
        channel = self.get_messageable(origin.channel_id)
        quoth = await channel.send(embed=embed_record(record))
        await gather(
            *[callback(origin, record, quoth) for callback in self.callbacks.values()]
        )

    async def on_ready(self) -> None:
        LOGGER.info(f"Logged in as {self.user}")
        await self.tree.sync()
        _add_guild = partial(self.data.add_guild, priority=ConnectionPriority.low)
        await gather(*map(_add_guild, self.guilds))
        LOGGER.info("FINISHED DOWNLOAD")

    async def on_guild_join(self, guild: Guild) -> None:
        await self.data.add_guild(guild, priority=ConnectionPriority.low)

    async def on_message(self, message: Message) -> None:
        await gather(
            self.data.add_message(message, priority=ConnectionPriority.low),
            self.process_commands(message),
        )
