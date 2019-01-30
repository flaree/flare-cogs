import discord
from redbot.core import commands, checks, Config
import random

BaseCog = getattr(commands, "Cog", object)


class Staff(BaseCog):
    """WC-RP's Commands"""

    @commands.command()
    async def staff(self, ctx):
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        embed = discord.Embed(
            title="WC-RP Staff Team", colour=colour)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="Management", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        for member in ctx.guild.members:
            if member.top_role.name == "Server Owner":
                embed.add_field(name="Server Owner", value=member.display_name, inline=True)
        for member in ctx.guild.members:
            if member.top_role.name == "Server Management":
                embed.add_field(name="Server Manager", value=member.display_name, inline=True)
        for member in ctx.guild.members:
            if member.top_role.name == "Scripter":
                embed.add_field(name="Scripter", value=member.display_name, inline=True)
        for member in ctx.guild.members:
            if member.top_role.name == "Lead Administrator":
                embed.add_field(name="Lead Admin", value=member.display_name, inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="Administration Team", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}", inline=True)
        embed.add_field(name="Senior Administrator", value="Jamie", inline=True)
        for member in ctx.guild.members:
            if member.top_role.name == "Senior Administrator":
                embed.add_field(name="Senior Admin", value=member.display_name, inline=True)
        for member in ctx.guild.members:
            if member.top_role.name == "Administrator":
                embed.add_field(name="Administrator", value=member.display_name, inline=True)
        for member in ctx.guild.members:
            if member.top_role.name == "IG Moderator":
                embed.add_field(name="Moderator", value=member.display_name, inline=True)

        await ctx.send(embed=embed)



