from redbot.core import commands, Config, checks
import discord
import requests
import random

defaults_global = {"token": {"apikey": None}}


class Movies(commands.Cog):
    """Movie Related Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.database = Config.get_conf(self, identifier=2230559235, force_registration=True)
        self.database.register_global(**defaults_global)

    @checks.is_owner()
    @commands.command()
    async def movieset(self, ctx, api: int):
        """Set your OMDB Token.
        http://www.omdbapi.com/apikey.aspx"""
        async with self.database.token() as token:
            token["apikey"] = api
            await ctx.send("You have successfully set your token.")

    @commands.command()
    async def movie(self, ctx, *, movie: str):
        """Movie Information Lookup"""
        async with self.database.token() as token:
            if token["apikey"] is None:
                await ctx.send(
                    "You have not set an OMDB Token, please set one up via [p]movieset <token>."
                )
                return
            else:
                apikey = token["apikey"]
        movie = movie.replace(" ", "-")
        r = requests.get("http://omdbapi.com/?t={}?&apikey={}".format(movie, apikey))
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        try:
            try:
                embed = discord.Embed(
                    title="{}".format(r.json()["Title"]),
                    colour=colour,
                    description=r.json()["Plot"],
                )
                embed.set_thumbnail(url=r.json()["Poster"])
                embed.add_field(name="Year:", value=r.json()["Year"], inline=True)
                embed.add_field(name="Released:", value=r.json()["Released"], inline=True)
                embed.add_field(name="Runtime:", value=r.json()["Runtime"], inline=True)
                embed.add_field(name="Director", value=r.json()["Director"], inline=True)
                embed.add_field(name="Rating:", value=r.json()["Rated"], inline=True)
                for source in r.json()["Ratings"]:
                    embed.add_field(
                        name="{}:".format(source["Source"]), value=source["Value"], inline=True
                    )
                embed.add_field(name="Genre:", value=r.json()["Genre"], inline=True)
                await ctx.send(embed=embed)
            except Exception:
                embed = discord.Embed(
                    title="{}".format(r.json()["Title"]),
                    colour=colour,
                    description=r.json()["Plot"],
                )
                embed.add_field(name="Year:", value=r.json()["Year"], inline=True)
                embed.add_field(name="Released:", value=r.json()["Released"], inline=True)
                embed.add_field(name="Runtime:", value=r.json()["Runtime"], inline=True)
                embed.add_field(name="Director", value=r.json()["Director"], inline=True)
                embed.add_field(name="Rating:", value=r.json()["Rated"], inline=True)
                for source in r.json()["Ratings"]:
                    embed.add_field(
                        name="{}:".format(source["Source"]), value=source["Value"], inline=True
                    )
                embed.add_field(name="Genre:", value=r.json()["Genre"], inline=True)
                await ctx.send(embed=embed)
        except KeyError:
            await ctx.send("Ensure the title is valid along with your API Key.")
