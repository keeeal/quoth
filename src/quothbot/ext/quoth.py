from discord import RawReactionActionEvent
from discord.ext.commands import Cog

from ..bot import QuothBot


class Quoth(Cog):
    def __init__(self, bot: QuothBot, emoji: str) -> None:
        self.bot = bot
        self.emoji = emoji

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent):
        if event.emoji.name == self.emoji:
            await self.bot.quoth(self.bot.get_channel(event.channel_id))
