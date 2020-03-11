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
            try:
                return await response.json()
            except aiohttp.ContentTypeError:
                return {"failed": True}

    @commands.group(invoke_without_command=True)
    async def covid(self, ctx, *, country: typing.Optional[str]):
        """Stats about Covid-19."""
        if not country:
            data = await self.get("https://corona.lmao.ninja/all")
            if isinstance(data, dict):
                if data.get("failed") is True:
                    return await ctx.send(
                        "Oops, something went wrong. The API may be having issues."
                    )
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(color=ctx.author.color, title="Covid-19 Global Statistics")
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            await ctx.send(embed=embed)
        else:
            data = await self.get("https://corona.lmao.ninja/countries")
            if isinstance(data, dict):
                if data.get("failed") is True:
                    return await ctx.send(
                        "Oops, something went wrong. The API may be having issues."
                    )
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
                title="Covid-19 | {} Statistics".format(countrydata["country"]),
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

    @covid.command()
    async def todaycases(self, ctx):
        """Show the highest cases from countrys today"""
        data = await self.get("https://corona.lmao.ninja/countries")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        highest = -1
        for i in range(len(data)):
            if data[i]["todayCases"] > data[highest]["todayCases"]:
                highest = i
        if highest == -1:
            return await ctx.send("No cases have been recorded today so far.")
        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Cases Today | {}".format(data[highest]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[highest]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[highest]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[highest]["recovered"]))
        embed.add_field(name="Cases Today", value=humanize_number(data[highest]["todayCases"]))
        embed.add_field(name="Deaths Today", value=humanize_number(data[highest]["todayDeaths"]))
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[highest]["critical"])
        )
        await ctx.send(embed=embed)

    @covid.command()
    async def todaydeaths(self, ctx):
        """Show the highest deaths from countrys today"""
        data = await self.get("https://corona.lmao.ninja/countries")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        highest = -1
        for i in range(len(data)):
            if data[i]["todayDeaths"] > data[highest]["todayDeaths"]:
                highest = i
        if highest == -1:
            return await ctx.send("No cases have been recorded today so far.")
        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Deaths Today | {}".format(data[highest]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[highest]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[highest]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[highest]["recovered"]))
        embed.add_field(name="Cases Today", value=humanize_number(data[highest]["todayCases"]))
        embed.add_field(name="Deaths Today", value=humanize_number(data[highest]["todayDeaths"]))
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[highest]["critical"])
        )
        await ctx.send(embed=embed)

    @covid.command()
    async def highestcases(self, ctx):
        """Show the highest cases from countrys overall"""
        data = await self.get("https://corona.lmao.ninja/countries")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        highest = -1
        for i in range(len(data)):
            if data[i]["cases"] > data[highest]["cases"]:
                highest = i
        if highest == -1:
            return await ctx.send("No cases have been recorded today so far.")
        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Cases Overall | {}".format(data[highest]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[highest]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[highest]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[highest]["recovered"]))
        embed.add_field(name="Cases Today", value=humanize_number(data[highest]["todayCases"]))
        embed.add_field(name="Deaths Today", value=humanize_number(data[highest]["todayDeaths"]))
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[highest]["critical"])
        )
        await ctx.send(embed=embed)

    @covid.command()
    async def highestdeaths(self, ctx):
        """Show the highest deaths from countrys overall"""
        data = await self.get("https://corona.lmao.ninja/countries")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        highest = -1
        for i in range(len(data)):
            if data[i]["deaths"] > data[highest]["deaths"]:
                highest = i
        if highest == -1:
            return await ctx.send("No cases have been recorded today so far.")
        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Deaths Overall | {}".format(data[highest]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[highest]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[highest]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[highest]["recovered"]))
        embed.add_field(name="Cases Today", value=humanize_number(data[highest]["todayCases"]))
        embed.add_field(name="Deaths Today", value=humanize_number(data[highest]["todayDeaths"]))
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[highest]["critical"])
        )
        await ctx.send(embed=embed)
