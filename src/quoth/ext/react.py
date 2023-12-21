from dataclasses import dataclass

from discord import Message
from discord.ext.commands import Bot, Cog


@dataclass
class React(Cog):
    bot: Bot
    emoji: str

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return

        if "quoth" in "".join(c for c in message.content.lower() if c in "quoth"):
            await message.add_reaction(self.emoji)
