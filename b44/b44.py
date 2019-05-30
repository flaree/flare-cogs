from redbot.core import commands, Config, checks
import discord
import aiohttp
from io import BytesIO


class B44(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.maps = {
            "coastal": "https://steamuserimages-a.akamaihd.net/ugc/797613650482816143/F5FD58D6395763BE5E21587ED793D8E267661402/",
            "derailed": "https://steamuserimages-a.akamaihd.net/ugc/797613650482834800/7E0E9DF86E2E6DF0B08F4FA82E30FDF9C13D93E6/",
            "liberation": "https://steamuserimages-a.akamaihd.net/ugc/797613650483430477/81990734D6C40FB0BDD7D9741151495CA17040C5/",
            "manorhouse": "https://steamuserimages-a.akamaihd.net/ugc/797613650483487212/2461F1492D5DEEB65036FC83EC95CEF66C93106B/",
            "invasion": "https://steamuserimages-a.akamaihd.net/ugc/788606529604715254/76A59A564B0F352B86634032182CEEFD32767BD0/",
            "savoia": "https://steamuserimages-a.akamaihd.net/ugc/788606529607778839/7724CF76A02B1BDBE051FF3F56678126B99FDA73/",
        }
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def getimg(self, map):
        async with self.session.get(self.maps[map]) as response:
            buffer = BytesIO(await response.read())
            buffer.name = "picture.png"
            return buffer
    async def get(self, url):
        async with self.session.get(url) as response:
            return await response.json()


    @commands.command()
    async def b44(self, ctx, *, map_name:str):
        """b44 map callouts"""
        if map_name not in self.maps:
            return await ctx.send("Map is currently not available or your input was wrong.\nCurrent available maps: {}".format(", ".join(self.maps.keys())))
        mapimg = await self.getimg(map_name.lower())
        await ctx.send(file=discord.File(mapimg))
        await ctx.send("<{}> for the direct link".format(self.maps[map_name.lower()]))

    @commands.command()
    async def players(self, ctx):
        """b44 current players"""
        resp = await self.get("http://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v0001/?appid=489940")
        await ctx.send("{} recently played!".format(resp["response"]["player_count"]))

