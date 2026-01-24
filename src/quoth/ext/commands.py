from dataclasses import dataclass
from enum import Enum, auto

from discord import Interaction
from discord.abc import Messageable
from discord.app_commands import command, describe
from discord.ext.commands import Cog

from quoth.bot import QuothBot
from quoth.data import ConnectionPriority
from quoth.errors import NotMessageable
from quoth.utils.logging import get_logger

LOGGER = get_logger(__name__)


class MessagesIn(Enum):
    channel = auto()
    server = auto()


@dataclass
class Commands(Cog):
    bot: QuothBot

    @command(name="count", description="Count messages")
    @describe(messages_in="In this channel or the server?")
    async def count(self, interaction: Interaction, messages_in: MessagesIn):
        LOGGER.info(f"Count called by {interaction.user}")
        if not isinstance(interaction.channel, Messageable):
            raise NotMessageable(interaction.channel)

        await interaction.response.defer(ephemeral=True, thinking=True)
        guild_id = interaction.guild_id
        channel_id = (
            interaction.channel_id if messages_in == MessagesIn.channel else None
        )
        group = (
            interaction.channel
            if messages_in == MessagesIn.channel
            else interaction.guild
        )
        count = await self.bot.data.count(
            channel_id=channel_id,
            guild_id=guild_id,
            priority=ConnectionPriority.high,
        )
        await interaction.followup.send(f"{count} messages found in {group}")
