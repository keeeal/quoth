from asyncio import gather
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, Optional, Union

from asyncpg import Connection, connect  # type: ignore[import]
from discord import Guild, Message, MessageType, TextChannel, Thread
from discord.errors import Forbidden
from pgvector.asyncpg import register_vector  # type: ignore[import]

from quoth.errors import NoGuild, NotFound
from quoth.model import QuothModel
from quoth.utils.config import read_from_env_var
from quoth.utils.logging import get_logger

LOGGER = get_logger(__name__)


class QuothData:
    def __init__(self, fetch_message: Callable[[int, int], Awaitable[Message]]) -> None:
        self.fetch_message = fetch_message
        self.model = QuothModel("BAAI/bge-small-en-v1.5")
        self.password = read_from_env_var("POSTGRES_PASSWORD_FILE")

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
                    channel_id bigint,
                    guild_id bigint,
                    embedding vector({384})
                )
                """,
            )

    async def add_message(self, message: Message) -> None:
        if message.author.bot:
            return

        if message.type not in [MessageType.default, MessageType.reply]:
            return

        if message.guild is None:
            return

        async with self.connect() as connection:
            if await connection.fetchval(
                """
                select exists (
                    select 1 from message
                    where message_id = $1
                )
                """,
                message.id,
            ):
                return

        embedding = await self.model.embed(message.content)

        async with self.connect() as connection:
            await connection.execute(
                """
                insert into message (
                    message_id,
                    channel_id,
                    guild_id,
                    embedding
                ) values ($1, $2, $3, $4)
                """,
                message.id,
                message.channel.id,
                message.guild.id,
                embedding,
            )

    async def add_channel(self, channel: Union[TextChannel, Thread]) -> None:
        try:
            async for message in channel.history(limit=None):
                await self.add_message(message)
        except Forbidden:
            LOGGER.warning(f"Channel forbidden: {channel.name}")
        else:
            LOGGER.info(f"Added channel: {channel.name}")
            # LOGGER.info(f"{await self.get_number_of_messages(channel.guild.id)} messages")

    async def add_guild(self, guild: Guild) -> None:
        await gather(*map(self.add_channel, guild.text_channels))
        await gather(*map(self.add_channel, guild.threads))
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

        return embedding or await self.model.embed(message.content)

    async def get_random_message(self, guild_id: int) -> Message:
        async with self.connect() as connection:
            record = await connection.fetchrow(
                """
                select (channel_id, message_id) from message
                where guild_id = $1
                order by random()
                limit 1
                """,
                guild_id,
            )

        if record is None:
            raise NotFound(f"No messages found for {guild_id = }")

        return await self.fetch_message(*record["row"])

    async def get_closest_message(self, message: Message) -> Message:
        if message.guild is None:
            raise NoGuild(f"No guild found for {message.id = }")

        embedding = await self.get_embedding(message)

        async with self.connect() as connection:
            record = await connection.fetchrow(
                """
                select (channel_id, message_id) from message
                where guild_id = $1
                order by embedding <-> $2
                limit 1
                """,
                message.guild.id,
                embedding,
            )

        if record is None:
            raise NotFound(f"No messages found for {message.guild.id = }")

        return await self.fetch_message(*record["row"])

    async def get_number_of_messages(self, guild_id: int) -> int:
        async with self.connect() as connection:
            return await connection.fetchval(
                """
                select count(*) from message
                where guild_id = $1
                """,
                guild_id,
            )
