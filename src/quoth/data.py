from __future__ import annotations

from asyncio import gather
from contextlib import asynccontextmanager
from typing import Optional, Union

from asyncpg import Connection, connect  # type: ignore[import]
from discord import Guild, Message, MessageType, TextChannel, Thread
from discord.errors import Forbidden
from numpy.typing import NDArray
from pgvector.asyncpg import register_vector  # type: ignore[import]
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer  # type: ignore[import]

from quoth.utils.config import read_from_env_var
from quoth.utils.logging import get_logger
from quoth.utils.message import get_content

LOGGER = get_logger(__name__)


class MessageRecord(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    message_id: int
    channel_id: int
    guild_id: int
    embedding: Optional[NDArray]

    @classmethod
    def from_message(
        cls, message: Message, embedding: Optional[NDArray] = None
    ) -> MessageRecord:
        return cls(
            message_id=message.id,
            channel_id=message.channel.id,
            guild_id=message.guild.id,
            embedding=embedding,
        )


class QuothData:
    def __init__(self, model_name: str) -> None:
        self.password = read_from_env_var("POSTGRES_PASSWORD_FILE")
        self.model = SentenceTransformer(model_name)
        self.ndim: int = self.model.get_sentence_embedding_dimension() or 0
        if self.ndim == 0:
            raise ValueError("Invalid embedding dimension")

    @asynccontextmanager
    async def connect(self) -> Connection:
        connection: Connection = await connect(
            host="data",
            user="postgres",
            password=self.password,
        )

        await connection.execute("create extension if not exists vector")
        await register_vector(connection)

        try:
            yield connection
        finally:
            await connection.close()

    async def initialize(self) -> None:
        async with self.connect() as connection:
            await connection.execute(
                f"""
                create table if not exists message (
                    message_id bigint primary key,
                    channel_id bigint not null,
                    guild_id bigint not null,
                    embedding vector({self.ndim})
                )
                """,
            )

    async def message_id_exists(self, message_id: int) -> bool:
        async with self.connect() as connection:
            return await connection.fetchval(
                """
                select exists (
                    select 1 from message
                    where message_id = $1
                    limit 1
                )
                """,
                message_id,
            )

    async def add_record(self, record: MessageRecord) -> None:
        async with self.connect() as connection:
            await connection.execute(
                """
                insert into message (
                    message_id,
                    channel_id,
                    guild_id,
                    embedding
                ) values ($1, $2, $3, $4)
                on conflict do nothing
                """,
                record.message_id,
                record.channel_id,
                record.guild_id,
                record.embedding,
            )

    async def add_message(self, message: Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:
            return
        if message.type not in [MessageType.default, MessageType.reply]:
            return
        if not (content := get_content(message)) and len(message.attachments) == 0:
            return
        if await self.message_id_exists(message.id):
            return

        embedding = self.model.encode(content) if content else None
        await self.add_record(MessageRecord.from_message(message, embedding))

    async def add_channel(self, channel: Union[TextChannel, Thread]) -> None:
        try:
            async for message in channel.history(limit=None):
                await self.add_message(message)
        except Forbidden:
            LOGGER.warning(f"Channel forbidden: {channel.name}")
        else:
            LOGGER.info(f"Added channel: {channel.name}")

    async def add_guild(self, guild: Guild) -> None:
        await gather(
            *map(self.add_channel, guild.text_channels),
            *map(self.add_channel, guild.threads),
        )
        LOGGER.info(f"Added guild: {guild.name}")

    async def get_embedding(self, message: Message) -> list[float]:
        async with self.connect() as connection:
            embedding = await connection.fetchval(
                """
                select embedding from message
                where message_id = $1
                limit 1
                """,
                message.id,
            )

        return embedding or self.model.encode(message.content)

    async def get_random_message_record(self, guild_id: int) -> MessageRecord:
        async with self.connect() as connection:
            record = await connection.fetchrow(
                """
                select * from message
                where guild_id = $1
                order by random()
                limit 1
                """,
                guild_id,
            )

        if record is None:
            raise IndexError(f"No messages found for {guild_id = }")

        return MessageRecord.model_validate(dict(record))

    async def get_closest_message_record(self, message: Message) -> MessageRecord:
        if message.guild is None:
            raise ValueError(f"No guild found for {message.id = }")

        embedding = await self.get_embedding(message)

        async with self.connect() as connection:
            record = await connection.fetchrow(
                """
                select * from message
                where guild_id = $1
                order by embedding <-> $2
                limit 1
                """,
                message.guild.id,
                embedding,
            )

        if record is None:
            raise IndexError(f"No messages found for {message.guild.id = }")

        return MessageRecord.model_validate(dict(record))

    async def get_number_of_messages(self, guild_id: int) -> int:
        async with self.connect() as connection:
            return await connection.fetchval(
                """
                select count(*) from message
                where guild_id = $1
                """,
                guild_id,
            )
