from dataclasses import dataclass
from typing import Union

from discord import RawReactionActionEvent, TextChannel, Thread
from discord.ext.commands import Cog

from quoth.bot import QuothBot


@dataclass
class Quoth(Cog):
    bot: QuothBot
    emoji: str

    @Cog.listener()
    async def on_raw_reaction_add(self, event: RawReactionActionEvent):
        if event.emoji.name != self.emoji:
            return

        message = await self.bot.fetch_message(
            channel_id=event.channel_id,
            message_id=event.message_id,
        )
        await self.bot.quoth(origin=message)
