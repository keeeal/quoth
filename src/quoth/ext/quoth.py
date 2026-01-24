from dataclasses import dataclass

from discord import RawReactionActionEvent
from discord.ext.commands import Cog

from quoth.bot import QuothBot
from quoth.utils.logging import get_logger, log_time

LOGGER = get_logger(__name__)


@dataclass
class Quoth(Cog):
    bot: QuothBot
    emoji: str

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent):
        if event.emoji.name != self.emoji:
            return
        if event.member:
            LOGGER.info(f"Quoth reaction by {event.member}")

        with log_time(LOGGER, "Quoth response"):
            origin = await self.bot.get_record(
                message_id=event.message_id,
                channel_id=event.channel_id,
            )
            await self.bot.quoth(origin=origin)
