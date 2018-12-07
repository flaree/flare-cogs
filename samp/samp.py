from redbot.core import commands
import discord
import requests
import random


class Samp(commands.Cog):
    """SA:MP Related Commands"""

    @commands.command()
    async def samp(self, ctx, ip: str):
        """SA:MP Server Lookup"""
        ip = ip.split(":")
        if ip[1] == "":
            ip[1] = 7777
        r = requests.post("http://monitor.sacnr.com/api/?IP={}&Port={}&Action=info&Format=json".format(ip[0], ip[1]))
        colour = discord.Color.from_hsv(random.random(), 1, 1)  # Random Hex Value for embed colour.
        embed = discord.Embed(title="SA:MP Server Information", colour=colour)
        embed.add_field(name="Server:", value=r.json()['Hostname'], inline=True)
        embed.add_field(name="IP:", value='{}'.format(":".join(ip)), inline=True)
        embed.add_field(name="Players:", value=r.json()['Players'], inline=True)
        embed.add_field(name="Version:", value=r.json()['Version'], inline=True)
        embed.add_field(name="Website:", value=r.json()['WebURL'], inline=True)
        await ctx.send(embed=embed)
