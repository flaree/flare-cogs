import discord
import validators
from redbot.core import checks, commands

from .abc import MixinMeta


class TeamsetMixin(MixinMeta):
    """Teamset Settings"""

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(autohelp=True)
    async def teamset(self, ctx):
        """Team Settings."""

    @teamset.command()
    async def role(self, ctx, team: str, *, role: discord.Role):
        """Set a teams role."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["role"] = role.id
        await ctx.tick()

    @teamset.command()
    async def stadium(self, ctx, team: str, *, stadium: str):
        """Set a teams stadium."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["stadium"] = stadium
        await ctx.tick()

    @teamset.command()
    async def logo(self, ctx, team: str, *, logo: str):
        """Set a teams logo."""
        if not validators.url(logo):
            await ctx.send("This doesn't seem to be a valid URL.")
        if not logo.endswith(".png"):
            await ctx.send("URL must be a png.")
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["logo"] = logo
        await ctx.tick()

    @teamset.command(hidden=True)
    async def bonus(self, ctx, team: str, *, amount: int):
        """Set a teams bonus multiplier."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["bonus"] = amount
        await ctx.tick()

    @teamset.command(usage="<current name> <new name>")
    async def name(self, ctx, team: str, *, newname: str):
        """Set a teams name. Try keep names to one word if possible."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[newname] = teams[team]
            if teams[team]["role"] is not None:
                role = ctx.guild.get_role(teams[team]["role"])
                await role.edit(name=newname)
            del teams[team]
        async with self.config.guild(ctx.guild).standings() as teams:
            teams[newname] = teams[team]
            del teams[team]
        await ctx.tick()

    @teamset.command()
    async def fullname(self, ctx, team: str, *, fullname: str):
        """Set a teams full name."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["fullname"] = fullname
        await ctx.tick()

    @teamset.command()
    async def captain(self, ctx, team: str, captain: discord.Member):
        """Set a teams captain."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            if captain.id not in teams[team]["members"]:
                return await ctx.send("He is not a member of that team.")
            teams[team]["captain"] = {}
            teams[team]["captain"] = {str(captain.id): captain.name}

        await ctx.tick()

    @teamset.group(autohelp=True)
    async def kits(self, ctx):
        """Kit Settings."""

    @kits.command()
    async def home(self, ctx, team: str, *, kiturl: str):
        """Set a teams home kit."""
        if not validators.url(kiturl):
            await ctx.send("This doesn't seem to be a valid URL.")
        if not kiturl.endswith(".png"):
            await ctx.send("URL must be a png.")
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["kits"]["home"] = kiturl
        await ctx.tick()

    @kits.command()
    async def away(self, ctx, team: str, *, kiturl: str):
        """Set a teams away kit."""
        if not validators.url(kiturl):
            await ctx.send("This doesn't seem to be a valid URL.")
            return
        if not kiturl.endswith(".png"):
            await ctx.send("URL must be a png.")
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["kits"]["away"] = kiturl
        await ctx.tick()

    @kits.command()
    async def third(self, ctx, team: str, *, kiturl: str):
        """Set a teams third kit."""
        if not validators.url(kiturl):
            await ctx.send("This doesn't seem to be a valid URL.")
        if not kiturl.endswith(".png"):
            await ctx.send("URL must be a png.")
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["kits"]["third"] = kiturl
        await ctx.tick()

    @teamset.command(name="transfer")
    async def _transfer(self, ctx, team1, player1: discord.Member, team2, player2: discord.Member):
        """Transfer two players."""
        if not await self.config.guild(ctx.guild).transferwindow():
            return await ctx.send("The transfer window is currently closed.")
        await self.transfer(ctx, ctx.guild, team1, player1, team2, player2)
        await ctx.tick()

    @teamset.command(name="sign")
    async def _sign(self, ctx, team1, player1: discord.Member, player2: discord.Member):
        """Release a player and sign a free agent."""
        if not await self.config.guild(ctx.guild).transferwindow():
            return await ctx.send("The transfer window is currently closed.")
        await self.sign(ctx, ctx.guild, team1, player1, player2)
        await ctx.tick()

    @teamset.command(name="delete")
    async def _delete(self, ctx, *, team):
        """Delete a team."""
        await self.team_delete(ctx, team)
