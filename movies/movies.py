from redbot.core import commands, Config, checks
import discord
import random
import aiohttp
import asyncio

defaults_global = {"token": {"apikey": None}}


class Movies(commands.Cog):
    """Movie Related Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.database = Config.get_conf(
            self, identifier=2230559235, force_registration=True)
        self.database.register_global(**defaults_global)
        self._session = aiohttp.ClientSession()

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json()

    @checks.is_owner()
    @commands.command()
    async def movieset(self, ctx, api: int):
        """Set your OMDB Token.
        http://www.omdbapi.com/apikey.aspx"""
        async with self.database.token() as token:
            token['apikey'] = api
            await ctx.send("You have successfully set your token.")

    @commands.command(aliases=['movies'])
    async def movie(self, ctx, *, movie: str):
        """Movie Information Lookup"""
        async with self.database.token() as token:
            if token['apikey'] is None:
                await ctx.send("You have not set an OMDB Token, please set one up via [p]movieset <token>.")
                return
            else:
                apikey = token['apikey']
        movie = movie.replace(" ", "-")
        req = "http://omdbapi.com/?t={}?&apikey={}".format(movie, apikey)
        r = await self.get(req)
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        try:
            try:
                embed = discord.Embed(title="{}".format(r['Title']), colour=colour,
                                      description=r['Plot'])
                embed.set_thumbnail(url=r['Poster'])
                embed.add_field(name="Year:", value=r['Year'], inline=True)
                embed.add_field(name="Released:", value=r['Released'], inline=True)
                embed.add_field(name="Runtime:", value=r['Runtime'], inline=True)
                embed.add_field(name="Director", value=r['Director'], inline=True)
                embed.add_field(name="Rating:", value=r['Rated'], inline=True)
                for source in r.['Ratings']:
                    embed.add_field(name="{}:".format(
                        source['Source']), value=source['Value'], inline=True)
                embed.add_field(name="Genre:", value=r['Genre'], inline=True)
                await ctx.send(embed=embed)
            except Exception:
                embed = discord.Embed(title="{}".format(r['Title']), colour=colour,
                                      description=r['Plot'])
                embed.add_field(name="Year:", value=r['Year'], inline=True)
                embed.add_field(name="Released:", value=r['Released'], inline=True)
                embed.add_field(name="Runtime:", value=r['Runtime'], inline=True)
                embed.add_field(name="Director", value=r['Director'], inline=True)
                embed.add_field(name="Rating:", value=r.['Rated'], inline=True)
                for source in r['Ratings']:
                    embed.add_field(name="{}:".format(
                        source['Source']), value=source['Value'], inline=True)
                embed.add_field(name="Genre:", value=r['Genre'], inline=True)
                await ctx.send(embed=embed)
        except KeyError:
            await ctx.send("Ensure the title is valid along with your API Key.")
