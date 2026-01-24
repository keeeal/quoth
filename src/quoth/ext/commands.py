from asyncio import gather
from collections import Counter
from dataclasses import dataclass
from enum import Enum, auto

from discord import Embed, Interaction, Member
from discord.abc import Messageable
from discord.app_commands import command, describe
from discord.ext.commands import Cog
from termplotlib.hist import hist_vertical  # type: ignore[import-untyped]

from quoth.bot import QuothBot
from quoth.data import ConnectionPriority, MessageRecord
from quoth.utils.logging import get_logger

LOGGER = get_logger(__name__)


def histogram(records: list[MessageRecord], max_months: int = 36) -> str:
    def get_key(record: MessageRecord) -> int:
        return 12 * record.created_at.year + record.created_at.month - 1

    def month_label(key: int) -> str:
        month = key % 12
        return "JFMAMJJASOND"[month]

    def year_label(key: int) -> str:
        year, month = divmod(key, 12)
        if month == 11:
            return "'"
        if month == 0:
            return str(year)[-2]
        if month == 1:
            return str(year)[-1]
        return " "

    counts = Counter(get_key(record) for record in records)
    start, stop = min(counts), max(counts) + 1
    start = max(start, stop - max_months)
    lines: list[str] = hist_vertical(
        [counts[key] for key in range(start, stop)],
        bar_width=1,
    )
    lines.append("".join(map(month_label, range(start, stop))))
    lines.append("".join(map(year_label, range(start, stop))))
    return "\n".join(lines)


class MessagesIn(Enum):
    channel = auto()
    server = auto()


@dataclass
class Commands(Cog):
    bot: QuothBot

    @command(name="stats", description="Print message statistics")
    @describe(messages_in="In this channel or the server?")
    async def stats(
        self,
        interaction: Interaction,
        messages_in: MessagesIn,
        by: Member | None = None,
    ):
        LOGGER.info(f"Stats called by {interaction.user}")
        if not isinstance(interaction.channel, Messageable):
            raise ValueError(interaction.channel)

        defer = interaction.response.defer(ephemeral=True, thinking=True)
        guild_id = interaction.guild_id
        channel_id = (
            interaction.channel_id if messages_in == MessagesIn.channel else None
        )
        author_id = by.id if by is not None else None

        records = await self.bot.data.fetch_records(
            channel_id=channel_id,
            guild_id=guild_id,
            author_id=author_id,
            priority=ConnectionPriority.high,
        )
        mean_length = (
            sum(len(record.content or "") for record in records) / len(records)
            if records
            else 0
        )
        favourite_day = (
            Counter(record.created_at.strftime("%A") for record in records).most_common(
                1
            )[0][0]
            if records
            else "Unknown"
        )

        channel_or_guild = (
            interaction.channel
            if messages_in == MessagesIn.channel
            else interaction.guild
        )
        send_response = interaction.channel.send(
            embed=Embed(
                title=f"{len(records)} messages"
                + ("" if by is None else f" by {by}")
                + f" in {channel_or_guild}",
                description=f"```{histogram(records)}```",
            )
            .add_field(
                name="Average message length",
                value=f"{mean_length:.1f} characters",
            )
            .add_field(
                name="Favourite day to message",
                value=favourite_day,
            )
        )
        await defer
        await gather(
            send_response,
            interaction.delete_original_response(),
        )
