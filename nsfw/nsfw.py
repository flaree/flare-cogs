import discord
from redbot.core import commands, checks
import aiohttp
import asyncio
from redbot.core.utils.chat_formatting import pagify
BaseCog = getattr(commands, "Cog", object)


class NSFW(BaseCog):
    """nsfw Commands"""

    def __init__(self, bot):
        self.bot = bot
        self._session = aiohttp.ClientSession()

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json()

    @commands.command()
    @commands.guild_only()
    async def anal(self, ctx):
        """Anal pics"""
        if ctx.channel.is_nsfw():
            req = await self.get('https://nekobot.xyz/api/image?type=anal')
            image = req["message"]
            emb = discord.Embed(title="Anal")
            emb.set_image(url=image)
            await ctx.send(embed=emb)

    @commands.command()
    @commands.guild_only()
    async def hentai(self, ctx):
        """Hentai pics"""
        if ctx.channel.is_nsfw():
            req = await self.get('https://nekobot.xyz/api/image?type=hentai')
            image = req["message"]
            emb = discord.Embed(title="Hentai")
            emb.set_image(url=image)
            await ctx.send(embed=emb)

    @commands.command()
    @commands.guild_only()
    async def hentaianal(self, ctx):
        """Hentai Anal pics"""
        if ctx.channel.is_nsfw():
            req = await self.get('https://nekobot.xyz/api/image?type=hentai_anal')
            image = req["message"]
            emb = discord.Embed(title="Hentai Anal")
            emb.set_image(url=image)
            await ctx.send(embed=emb)

    @commands.command()
    @commands.guild_only()
    async def fourk(self, ctx):
        """4k pics"""
        if ctx.channel.is_nsfw():
            req = await self.get('https://nekobot.xyz/api/image?type=4k')
            image = req["message"]
            emb = discord.Embed(title="4k")
            emb.set_image(url=image)
            await ctx.send(embed=emb)

    @commands.command(aliases=["cock"])
    @commands.guild_only()
    async def penis(self, ctx):
        """Penis pics"""
        if ctx.channel.is_nsfw():
            req = await self.get('https://www.reddit.com/r/penis/random.json')
            image = req[0]["data"]["children"][0]["data"]["url"]
            emb = discord.Embed(title="Penis")
            emb.set_image(url=image)
            await ctx.send(embed=emb)

    @commands.command()
    @commands.guild_only()
    async def blackcock(self, ctx):
        """Black cock pics"""
        if ctx.channel.is_nsfw():
            req = await self.get('https://www.reddit.com/r/blackcock/random.json')
            image = req[0]["data"]["children"][0]["data"]["url"]
            emb = discord.Embed(title="Black Cock")
            emb.set_image(url=image)
            await ctx.send(embed=emb)