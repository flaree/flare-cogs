from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
import discord
import aiohttp
import typing


class Covid(commands.Cog):
    """Covid-19 (Novel Coronavirus Stats)."""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

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
                if response.status == 200:
                    if await response.text() == "Country not found":
                        return {"failed": "Country not found"}
                return {"failed": True}

    @commands.group(invoke_without_command=True)
    async def covid(self, ctx, *, country: typing.Optional[str]):
        """Stats about Covid-19."""
        if not country:
            data = await self.get("https://corona.lmao.ninja/all")
            if isinstance(data, dict):
                if data.get("failed") is True:
                    return await ctx.send("Country could not be found.")
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(color=ctx.author.color, title="Covid-19 Global Statistics")
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            await ctx.send(embed=embed)
        else:
            data = await self.get("https://corona.lmao.ninja/countries/{}".format(country))
            error = data.get("failed")
            if isinstance(error, str):
                return await ctx.send(
                    "That country was not found. Please try refining your search or that country is not infecte."
                )
            elif error:
                return await ctx.send("There's an issue with the API. Please try again later.")
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | {} Statistics".format(data["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def todaycases(self, ctx):
        """Show the highest cases from countrys today"""
        data = await self.get("https://corona.lmao.ninja/countries?sort=todayCases")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")

        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Cases Today | {}".format(data[len(data) - 1]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[len(data) - 1]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[len(data) - 1]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[len(data) - 1]["recovered"]))
        embed.add_field(
            name="Cases Today", value=humanize_number(data[len(data) - 1]["todayCases"])
        )
        embed.add_field(
            name="Deaths Today", value=humanize_number(data[len(data) - 1]["todayDeaths"])
        )
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[len(data) - 1]["critical"])
        )
        await ctx.send(embed=embed)

    @covid.command()
    async def today(self, ctx):
        """Statistics for today."""
        data = await self.get("https://corona.lmao.ninja/countries?sort=todayCases")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        todayDeaths = 0
        todayCases = 0
        for i in range(len(data)):
            todayDeaths += int(data[i]["todayDeaths"])
            todayCases += int(data[i]["todayCases"])
        embed = discord.Embed(title="Covid-19 Statistics for Today", color=ctx.author.color)
        embed.add_field(name="Cases Today", value=humanize_number(todayCases))
        embed.add_field(name="Deaths Today", value=humanize_number(todayDeaths))
        await ctx.send(embed=embed)

    @covid.command()
    async def todaydeaths(self, ctx):
        """Show the highest deaths from countrys today"""
        data = await self.get("https://corona.lmao.ninja/countries?sort=todayDeaths")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")

        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Deaths Today | {}".format(data[len(data) - 1]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[len(data) - 1]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[len(data) - 1]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[len(data) - 1]["recovered"]))
        embed.add_field(
            name="Cases Today", value=humanize_number(data[len(data) - 1]["todayCases"])
        )
        embed.add_field(
            name="Deaths Today", value=humanize_number(data[len(data) - 1]["todayDeaths"])
        )
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[len(data) - 1]["critical"])
        )
        await ctx.send(embed=embed)

    @covid.command()
    async def highestcases(self, ctx):
        """Show the highest cases from countrys overall"""
        data = await self.get("https://corona.lmao.ninja/countries?sort=cases")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Cases Overall | {}".format(data[len(data) - 1]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[len(data) - 1]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[len(data) - 1]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[len(data) - 1]["recovered"]))
        embed.add_field(
            name="Cases Today", value=humanize_number(data[len(data) - 1]["todayCases"])
        )
        embed.add_field(
            name="Deaths Today", value=humanize_number(data[len(data) - 1]["todayDeaths"])
        )
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[len(data) - 1]["critical"])
        )
        await ctx.send(embed=embed)

    @covid.command()
    async def highestdeaths(self, ctx):
        """Show the highest deaths from countrys overall"""
        data = await self.get("https://corona.lmao.ninja/countries?sort=deaths")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        embed = discord.Embed(
            color=ctx.author.color,
            title="Covid-19 | Highest Deaths Overall | {}".format(data[len(data) - 1]["country"]),
        )
        embed.add_field(name="Cases", value=humanize_number(data[len(data) - 1]["cases"]))
        embed.add_field(name="Deaths", value=humanize_number(data[len(data) - 1]["deaths"]))
        embed.add_field(name="Recovered", value=humanize_number(data[len(data) - 1]["recovered"]))
        embed.add_field(
            name="Cases Today", value=humanize_number(data[len(data) - 1]["todayCases"])
        )
        embed.add_field(
            name="Deaths Today", value=humanize_number(data[len(data) - 1]["todayDeaths"])
        )
        embed.add_field(
            name="Critical Condition", value=humanize_number(data[len(data) - 1]["critical"])
        )
        await ctx.send(embed=embed)

    @covid.command()
    async def topcases(self, ctx, amount: int = 5):
        """Show X countries with top amount of cases. Defaults to 5."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        """Show the highest cases from countrys overall"""
        data = await self.get("https://corona.lmao.ninja/countries?sort=cases")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        data.reverse()
        embed = discord.Embed(
            color=ctx.author.color, title="Covid-19 | Top {} Cases ".format(amount),
        )
        for i in range(amount):
            msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
            embed.add_field(name=data[i]["country"], value=msg)
        await ctx.send(embed=embed)

    @covid.command()
    async def topdeaths(self, ctx, amount: int = 5):
        """Show X countries with top amount of deaths. Defaults to 5."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        """Show the highest cases from countrys overall"""
        data = await self.get("https://corona.lmao.ninja/countries?sort=deaths")
        if isinstance(data, dict):
            if data.get("failed") is True:
                return await ctx.send("Oops, something went wrong. The API may be having issues.")
        if not data:
            return await ctx.send("No data available.")
        data.reverse()
        embed = discord.Embed(
            color=ctx.author.color, title="Covid-19 | Top {} Cases ".format(amount),
        )
        for i in range(amount):
            msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
            embed.add_field(name=data[i]["country"], value=msg)
        await ctx.send(embed=embed)
