from dataclasses import dataclass

from discord import RawReactionActionEvent
from discord.ext.commands import Cog

from ..bot import QuothBot


@dataclass
class Quoth(Cog):
    bot: QuothBot
    emoji: str

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent):
        if event.emoji.name == self.emoji:
            await self.bot.quoth(self.bot.get_channel(event.channel_id))
