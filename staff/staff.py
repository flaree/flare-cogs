import discord
from redbot.core import commands, checks, Config
import random

BaseCog = getattr(commands, "Cog", object)


class Staff(BaseCog):
    """WC-RP's Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.database = Config.get_conf(
            self, identifier=1230598123, force_registration=True)
        defaults_global = {"staff": {}, "management": {}}
        self.database.register_global(**defaults_global)

    @commands.has_any_role("Lead Administrator", "Server Manager", "Server Owner")
    @commands.command()
    async def addstaff(self, ctx, name: str, *, rank: str):
        """Add staff members"""
        async with self.database.staff() as staff:
            key = name
            staff[key] = rank
        await ctx.send("Done.")

    @commands.has_any_role("Lead Administrator", "Server Manager", "Server Owner")
    @commands.command()
    async def addmanagement(self, ctx, name: str, *, rank: str):
        """Add Management members"""
        async with self.database.management() as management:
            key = name
            management[key] = rank
        await ctx.send("Done.")

    @commands.command()
    async def staff(self, ctx):
        """List WC-RP Staff"""
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        embed = discord.Embed(
            title="WC-RP Staff Team", colour=colour)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="Management", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        async with self.database.management() as management:
            for name in management:
                embed.add_field(name=management[name], value=name, inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="Administration Team", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)

        async with self.database.staff() as staff:
            for name in staff:
                embed.add_field(name=staff[name], value=name, inline=True)
        await ctx.send(embed=embed)

    @commands.has_any_role("Lead Administrator", "Server Manager", "Server Owner")
    @commands.command()
    async def remstaff(self, ctx, name: str):
        """Remove staff members"""
        async with self.database.staff() as staff:
            if name in staff:
                del staff[name]
            await ctx.send("done")

    @commands.has_any_role("Lead Administrator", "Server Manager", "Server Owner")
    @commands.command()
    async def remmanagement(self, ctx, name: str):
        """Remove management members"""
        async with self.database.management() as management:
            if name in management:
                del management[name]
            await ctx.send("done")
