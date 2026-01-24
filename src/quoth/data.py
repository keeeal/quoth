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
from pydantic import BaseModel, Field

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
    message_id: int = Field(pg_type="bigint primary key")  # type: ignore
    channel_id: int = Field(pg_type="bigint not null")  # type: ignore
    guild_id: int | None = Field(pg_type="bigint")  # type: ignore
    author_id: int = Field(pg_type="bigint not null")  # type: ignore
    content: str | None = Field(pg_type="text")  # type: ignore
    attachment_urls: list[str] = Field(pg_type="text[] not null")  # type: ignore
    created_at: datetime = Field(pg_type="timestamptz not null")  # type: ignore
    display_name: str = Field(pg_type="text not null")  # type: ignore
    avatar_url: str | None = Field(pg_type="text")  # type: ignore
    jump_url: str = Field(pg_type="text not null")  # type: ignore

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
    def from_message(cls, message: Message) -> Self:
        author = message.author
        return cls(
            message_id=message.id,
            channel_id=message.channel.id,
            guild_id=message.guild.id if message.guild else None,
            author_id=author.id,
            content=get_content(message),
            attachment_urls=[attachment.url for attachment in message.attachments],
            created_at=message.created_at,
            display_name=author.display_name,
            avatar_url=author.avatar.url if author.avatar else None,
            jump_url=message.jump_url,
        )


class QuothData:
    def __init__(
        self,
        max_connections_per_priority: dict[ConnectionPriority, int] = {
            ConnectionPriority.high: 2,
            ConnectionPriority.low: 4,
        },
    ) -> None:
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
                    f"{field} {pg_type}"
                    for field, pg_type in MessageRecord.field_types().items()
                )}
            )
        """
        async with self.connect(priority) as connection:
            await connection.execute(query)

    async def exists(
        self,
        *,
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
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> None:
        if message.author.bot:
            return
        if message.type not in [MessageType.default, MessageType.reply]:
            return
        if await self.exists(message_id=message.id, priority=priority):
            return

        await self.add_record(
            MessageRecord.from_message(message),
            priority=priority,
        )

    async def add_channel(
        self,
        channel: Messageable,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> None:
        try:
            async for message in channel.history(limit=None, oldest_first=True):
                await self.add_message(message, priority=priority)
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

    async def fetch_record(
        self,
        message_id: int,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> MessageRecord | None:
        query = """
            select * from message
            where message_id = $1
            limit 1
        """
        async with self.connect(priority) as connection:
            record = await connection.fetchrow(query, message_id)

        if record is None:
            return None

        return MessageRecord.model_validate(dict(record))

    async def fetch_records(
        self,
        *,
        channel_id: int | None = None,
        guild_id: int | None = None,
        author_id: int | None = None,
        content: str | None = None,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> list[MessageRecord]:
        query = """
            select * from message
            where (channel_id = $1 or $1 is null)
            and (guild_id = $2 or $2 is null)
            and (author_id = $3 or $3 is null)
            and (lower(content) = lower($4) or $4 is null)
        """
        async with self.connect(priority) as connection:
            records = await connection.fetch(
                query, channel_id, guild_id, author_id, content
            )

        return [MessageRecord.model_validate(dict(record)) for record in records]

    async def fetch_random(
        self,
        *,
        channel_id: int | None = None,
        guild_id: int | None = None,
        author_id: int | None = None,
        content: str | None = None,
        priority: ConnectionPriority = ConnectionPriority.minimum(),
    ) -> MessageRecord:
        query = """
            select * from message
            where (channel_id = $1 or $1 is null)
            and (guild_id = $2 or $2 is null)
            and (author_id = $3 or $3 is null)
            and (content = $4 or $4 is null)
            order by random()
            limit 1
        """
        async with self.connect(priority) as connection:
            record = await connection.fetchrow(
                query, channel_id, guild_id, author_id, content
            )

        if record is None:
            raise IndexError(
                "No messages found for"
                f" {channel_id=}"
                f" {guild_id=}"
                f" {author_id=}"
                f" {content=}"
            )

        return MessageRecord.model_validate(dict(record))
