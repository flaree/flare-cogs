from redbot.core import commands
import discord
import aiohttp
import asyncio
import random


class Samp(commands.Cog):
    """SA:MP Related Commands"""

    def __init__(self, bot):
        self.bot = bot
        self._session = aiohttp.ClientSession()

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json(content_type=None)

    @commands.command()
    async def samp(self, ctx, ip: str):
        """SA:MP Server Lookup"""
        serv_ip = ip
        if ip[len(ip) - 5] == ":":
            ips = ip.split(":")
            port = ips[1]
            serv_ip = ips[0]
        else:
            port = "7777"
        try:
            req = "https://api.samp-servers.net/v2/server/{}:{}".format(serv_ip, port)
            r = await self.get(req)
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(title="SA:MP Server Information", colour=colour)
            embed.add_field(name="Server:", value=r["core"]["hn"], inline=True)
            embed.add_field(name="IP:", value="{}".format(ip), inline=True)
            embed.add_field(
                name="Players:", value=f"{r['core']['pc']}/{r['core']['pm']}", inline=True
            )
            embed.add_field(name="Server Version:", value=r["core"]["gm"], inline=True)
            embed.add_field(name="SA-MP Version:", value=r["core"]["vn"], inline=True)
            await ctx.send(embed=embed)
        except ValueError:
            await ctx.send(
                "Please ensure that the IP is correct and that it is monitored by samp-servers.net"
            )
