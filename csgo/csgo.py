from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
import discord
import typing


class Csgo(commands.Cog):
    """CSGO commands."""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.emoji = "\N{WHITE HEAVY CHECK MARK}"
        self.games = {}

    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.command()
    async def csgo(self, ctx):
        """Gather up 4 others"""
        role = discord.utils.get(ctx.guild.roles, name="CSGO")
        # await role.edit(mentionable=True)
        msg = await ctx.send(
            f"React to the \N{WHITE HEAVY CHECK MARK} below to join the 5-man.\n{role.mention}"
        )
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        # await role.edit(mentionable=False)
        self.games[msg.id] = []

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not str(payload.emoji) == self.emoji:
            return
        user = payload.member
        if user.bot:
            return
        if payload.message_id in self.games:
            channel = self.bot.get_channel(payload.channel_id)
            if user in self.games[payload.message_id]:
                return
            self.games[payload.message_id].append(user)
            if len(self.games[payload.message_id]) == 5:
                await self.confirmgame(channel, payload.message_id)

    async def confirmgame(self, channel, messageid):
        await channel.send(
            "**CSGO Team**:\n{}".format("\n".join([x.mention for x in self.games[messageid]]))
        )
        del self.games[messageid]
