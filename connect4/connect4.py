import asyncio
from collections import Counter

import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import start_adding_reactions

from .core import Connect4Game, Connect4Menu


class Connect4(commands.Cog):
    """
    Play Connect 4!
    """
    EMOJI_MEDALS = {
        1: "\N{FIRST PLACE MEDAL}",
        2: "\N{SECOND PLACE MEDAL}",
        3: "\N{THIRD PLACE MEDAL}",
    }

    def __init__(self, bot):
        self.bot = bot
        defaults = {"stats": {"played": 0, "ties": 0, "wins": {}, "losses": {}, "draws": {}}}
        self.config = Config.get_conf(self, identifier=4268355870, force_registration=True)
        self.config.register_guild(**defaults)

    @staticmethod
    async def startgame(ctx: commands.Context, user: discord.Member) -> bool:
        """
		Whether to start the connect 4 game.
		"""
        await ctx.send(f"{user.mention}, {ctx.author.name} is challenging you to a game of Connect4. (y/n)")

        try:
            pred = MessagePredicate.yes_or_no(ctx, user=user)
            await ctx.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Game offer declined, cancelling.")
            return False

        if pred.result:
            return True

        await ctx.send("Game cancelled.")
        return False

    @commands.group(invoke_without_command=True)
    async def connect4(self, ctx: commands.Context, member: discord.Member):
        """
        Play Connect 4 with another player.
        """
        if member.bot:
            return await ctx.send("That's a bot, silly!")
        if ctx.author == member:
            return await ctx.send("You can't play yourself!")
        if not await self.startgame(ctx, member):
            return

        game = Connect4Game(ctx.author, member)
        menu = Connect4Menu(self, game)
        await menu.start(ctx)

    def create_field(self, stats: dict, key: str) -> dict:
        counter = Counter(stats[key])
        values = []
        total = sum(counter.values())
        for place, (user_id, win_count) in enumerate(counter.most_common(3), 1):
            medal = self.EMOJI_MEDALS[place]
            values.append(f"{medal} <@!{user_id}>: {win_count}")
        return {"name": f"{key.title()}: {total}", "value": "\n".join(values), "inline": True} if values else {}

    @connect4.command("stats")
    async def connect4_stats(self, ctx: commands.Context, member: discord.Member = None):
        """
        View Connect 4 stats.
        """
        stats = await self.config.guild(ctx.guild).stats()
        if member:
            member_id = str(member.id)
            wins = stats["wins"].get(member_id, 0)
            losses = stats["losses"].get(member_id, 0)
            draws = stats["draws"].get(member_id, 0)
            description = [
                f"Wins: {wins}",
                f"Losses: {losses}",
                f"Draws: {draws}",
            ]
            e = discord.Embed(color=member.color, description="\n".join(description))
            e.set_author(name=f"{ctx.author} Connect 4 Stats", icon_url=ctx.author.avatar_url)
        else:
            games_played = stats["played"]
            ties = stats["ties"]
            description = [
                f"Games played: {games_played}",
                f"Ties: {ties}",
            ]
            e = discord.Embed(color=await ctx.embed_color(), description="\n".join(description))
            if wins := self.create_field(stats, "wins"):
                e.add_field(**wins)
            if losses := self.create_field(stats, "losses"):
                e.add_field(**losses)
            if draws := self.create_field(stats, "draws"):
                e.add_field(**draws)
            e.set_author(name=f"{ctx.guild} Connect 4 Stats", icon_url=ctx.guild.icon_url)
        await ctx.send(embed=e)