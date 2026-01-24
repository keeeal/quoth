from dataclasses import dataclass

from discord import Message
from discord.ext.commands import Cog

from quoth.bot import QuothBot


@dataclass
class React(Cog):
    bot: QuothBot
    emoji: str
    trigger_word: str

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return

        if self.trigger_word in "".join(
            c for c in message.content.lower() if c in self.trigger_word
        ):
            await message.add_reaction(self.emoji)
