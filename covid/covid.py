from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
import discord
import aiohttp
import typing


class Covid(commands.Cog):
    """Covid-19 (Novel Coronavirus Stats)."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def get(self, url):
        async with self.session.get(url) as response:
            return await response.json()

    @commands.group(invoke_without_command=True)
    async def covid(self, ctx, *, country: typing.Optional[str]):
        """Stats about Covid-19."""
        if not country:
            data = await self.get("https://corona.lmao.ninja/all")
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(color=ctx.author.color, title="Covid-19 Global Statistics")
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            await ctx.send(embed=embed)
        else:
            data = await self.get("https://corona.lmao.ninja/countries")
            if not data:
                return await ctx.send("No data available.")
            countrydata = None
            for i in range(len(data)):
                if data[i]["country"].lower() == country.lower():
                    countrydata = data[i]
            if countrydata is None:
                return await ctx.send("No statistics for {} available.".format(country))
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 {} Statistics".format(countrydata["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(countrydata["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(countrydata["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(countrydata["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(countrydata["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(countrydata["todayDeaths"]))
            embed.add_field(
                name="Critical Condition", value=humanize_number(countrydata["critical"])
            )
            await ctx.send(embed=embed)
