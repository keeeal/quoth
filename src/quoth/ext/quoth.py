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
    cooldown_seconds: float

    def __post_init__(self):
        self.last_quoth_time = 0.0

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent):
        if event.emoji.name != self.emoji:
            return
        user = (
            await self.bot.fetch_user(event.user_id)
            if event.member is None
            else event.member
        )
        LOGGER.info(f"Quoth reaction by {user}")

        cooldown_time = self.cooldown_seconds - (
            self.bot.loop.time() - self.last_quoth_time
        )
        if cooldown_time > 0:
            LOGGER.warning(f"Quoth cooldown: {cooldown_time:.2f} seconds")
            return

        self.last_quoth_time = self.bot.loop.time()
        with log_time(LOGGER, "Quoth response"):
            origin = await self.bot.fetch_record(
                message_id=event.message_id,
                channel_id=event.channel_id,
            )
            await self.bot.quoth(origin=origin)
