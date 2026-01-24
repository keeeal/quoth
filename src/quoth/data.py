from asyncio import gather
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from functools import partial
from typing import AsyncGenerator, Self

from asyncpg import Connection, Pool, create_pool  # type: ignore[import-untyped]
from discord import Guild, Message, MessageType
from discord.abc import Messageable
from discord.errors import Forbidden
from numpy.typing import NDArray
from pgvector.asyncpg import register_vector  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from torch import Tensor

from quoth.model import QuothModel
from quoth.utils.config import read_from_env_var
from quoth.utils.logging import get_logger
from quoth.utils.message import get_content

LOGGER = get_logger(__name__)


class ConnectionPriority(Enum):
    high = 3
    medium = 2
    low = 1

    @classmethod
    def minimum(cls) -> Self:
        return min(cls, key=lambda i: i.value)

    @classmethod
    def sorted(cls, *, reverse: bool = False) -> list[Self]:
        return sorted(cls, key=lambda i: i.value, reverse=reverse)

    def or_lower(self) -> list[Self]:
        return [p for p in type(self).sorted(reverse=True) if p.value <= self.value]


class MessageRecord(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    message_id: int = Field(pg_type="bigint primary key")  # type: ignore
    channel_id: int = Field(pg_type="bigint not null")  # type: ignore
    guild_id: int | None = Field(pg_type="bigint")  # type: ignore
    content: str | None = Field(pg_type="text")  # type: ignore
    attachment_urls: list[str] = Field(pg_type="text[] not null")  # type: ignore
    created_at: datetime = Field(pg_type="timestamptz not null")  # type: ignore
    display_name: str = Field(pg_type="text not null")  # type: ignore
    avatar_url: str | None = Field(pg_type="text")  # type: ignore
    jump_url: str = Field(pg_type="text not null")  # type: ignore
    embedding: NDArray | None = Field(pg_type="vector({ndim})")  # type: ignore
    channel_ingest: bool = Field(pg_type="boolean not null")  # type: ignore

    @classmethod
    def field_types(cls) -> dict[str, str]:
        field_types: dict[str, str] = {}

        for field_name, field_info in cls.model_fields.items():
            if not isinstance(field_info.json_schema_extra, dict):
                raise ValueError(f"{field_name} is missing 'pg_type'")
            if "pg_type" not in field_info.json_schema_extra:
                raise KeyError(f"{field_name} is missing 'pg_type'")
            pg_type = field_info.json_schema_extra["pg_type"]
            if not isinstance(pg_type, str):
                raise TypeError(f"{field_name} invalid 'pg_type': {pg_type}")
            field_types[field_name] = pg_type

        return field_types

    @classmethod
    def from_message(
        cls,
        message: Message,
        embedding: NDArray | None = None,
        channel_ingest: bool = False,
    ) -> Self:
        author = message.author
        return cls(
            message_id=message.id,
            channel_id=message.channel.id,
            guild_id=message.guild.id if message.guild else None,
            content=get_content(message),
            attachment_urls=[attachment.url for attachment in message.attachments],
            created_at=message.created_at,
            display_name=author.display_name,
            avatar_url=author.avatar.url if author.avatar else None,
            jump_url=message.jump_url,
            embedding=embedding,
            channel_ingest=channel_ingest,
        )


class QuothData:
    def __init__(
        self,
        model: QuothModel,
        max_connections_per_priority: dict[ConnectionPriority, int] = {
            ConnectionPriority.high: 2,
            ConnectionPriority.low: 4,
        },
    ) -> None:
        self.model = model
        self.ndim: int = self.model.get_embedding_dimension()

        self.connection_kwargs = dict(
            host="data",
            user="postgres",
            password=read_from_env_var("POSTGRES_PASSWORD_FILE"),
            min_size=0,
        )
        self.max_connections_per_priority = max_connections_per_priority
        self.pools: dict[ConnectionPriority, Pool | None] = {
            priority: None for priority in ConnectionPriority
        }

    @asynccontextmanager
    async def connect(
        self, priority: ConnectionPriority
    ) -> AsyncGenerator[Connection, None]:
        for _priority in priority.or_lower():
            pool = self.pools.get(_priority)
            if pool is None:
                continue
            if pool._queue.empty():
                continue
            break
        else:
            pool = self.pools.get(_priority)
        if pool is None:
            raise ValueError("Connection pool is not initialized")

        async with pool.acquire() as connection:
            await connection.execute("create extension if not exists vector")
            await register_vector(connection)
            yield connection

    async def initialize(
        self,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> None:
        LOGGER.info("Initializing data")
        self.pools = {
            priority: (
                await create_pool(max_size=max_size, **self.connection_kwargs)
                if (max_size := self.max_connections_per_priority.get(priority, 0)) > 0
                else None
            )
            for priority in ConnectionPriority
        }
        query = f"""
            create table if not exists message (
                {", ".join(
                    f"{field} {pg_type.format(ndim=self.ndim)}"
                    for field, pg_type in MessageRecord.field_types().items()
                )}
            )
        """
        async with self.connect(priority) as connection:
            await connection.execute(query)

    async def exists(
        self,
        message_id: int | None = None,
        channel_id: int | None = None,
        guild_id: int | None = None,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> bool:
        query = """
            select exists (
                select 1 from message
                where (message_id = $1 or $1 is null)
                and (channel_id = $2 or $2 is null)
                and (guild_id = $3 or $3 is null)
                limit 1
            )
        """
        async with self.connect(priority) as connection:
            return await connection.fetchval(query, message_id, channel_id, guild_id)

    async def count(
        self,
        channel_id: int | None = None,
        guild_id: int | None = None,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> int:
        query = """
            select count(1) from message
            where (channel_id = $1 or $1 is null)
            and (guild_id = $2 or $2 is null)
        """
        async with self.connect(priority) as connection:
            return await connection.fetchval(query, channel_id, guild_id)

    async def add_record(
        self,
        record: MessageRecord,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> None:
        field_types = MessageRecord.field_types()
        query = f"""
            insert into message ({", ".join(field_types.keys())})
            values ({", ".join(f"${i + 1}" for i in range(len(field_types)))})
            on conflict (message_id) do nothing
        """
        async with self.connect(priority) as connection:
            await connection.execute(query, *record.model_dump().values())

    async def add_message(
        self,
        message: Message,
        channel_ingest: bool = False,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> None:
        if message.author.bot:
            return
        if message.type not in [MessageType.default, MessageType.reply]:
            return
        if await self.exists(message_id=message.id, priority=priority):
            return

        embedding = await self.get_embedding(message, priority=priority)
        await self.add_record(
            MessageRecord.from_message(message, embedding, channel_ingest),
            priority=priority,
        )

    async def add_channel(
        self,
        channel: Messageable,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> None:
        channel_id = (await channel._get_channel()).id
        after = await self.get_latest_ingest(channel_id)
        try:
            async for message in channel.history(
                after=after, limit=None, oldest_first=True
            ):
                await self.add_message(message, channel_ingest=True, priority=priority)
        except Forbidden:
            LOGGER.warning(f"Channel forbidden: {channel}")
        else:
            LOGGER.info(f"Added channel: {channel}")

    async def add_guild(
        self,
        guild: Guild,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> None:
        _add_channel = partial(self.add_channel, priority=priority)
        await gather(
            *map(_add_channel, guild.text_channels),
            *map(_add_channel, guild.threads),
        )
        LOGGER.info(f"Added guild: {guild}")

    async def get_record(
        self,
        message_id: int,
        channel_id: int | None = None,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> MessageRecord | None:
        query = """
            select * from message
            where message_id = $1
            and (channel_id = $2 or $2 is null)
            limit 1
        """
        async with self.connect(priority) as connection:
            record = await connection.fetchrow(query, message_id, channel_id)

        if record is None:
            return None

        return MessageRecord.model_validate(dict(record))

    async def get_embedding(
        self,
        message: Message,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> NDArray | None:
        query = """
            select embedding from message
            where message_id = $1
            limit 1
        """
        embedding: Tensor | NDArray | None = None
        async with self.connect(priority) as connection:
            embedding = await connection.fetchval(query, message.id)
        if embedding is None and (content := get_content(message)):
            embedding = self.model.embed_text(content)
        if isinstance(embedding, Tensor):
            embedding = embedding.numpy()

        return embedding

    async def get_latest_ingest(
        self,
        channel_id: int,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> datetime | None:
        query = """
            select created_at from message
            where channel_id = $1 and channel_ingest = true
            order by created_at desc
            limit 1
        """
        async with self.connect(priority) as connection:
            return await connection.fetchval(query, channel_id)

    async def get_random(
        self,
        guild_id: int,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> MessageRecord:
        query = """
            select * from message
            where guild_id = $1
            order by random()
            limit 1
        """
        async with self.connect(priority) as connection:
            record = await connection.fetchrow(query, guild_id)

        if record is None:
            raise IndexError(f"No messages found for {guild_id = }")

        return MessageRecord.model_validate(dict(record))

    async def get_closest(
        self,
        message: Message,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> MessageRecord:
        if message.guild is None:
            raise ValueError(f"No guild found for {message.id = }")

        embedding = await self.get_embedding(message, priority=priority)

        async with self.connect(priority) as connection:
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
