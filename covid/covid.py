from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number
import discord
import aiohttp
import typing


class Covid(commands.Cog):
    """Covid-19 (Novel Coronavirus Stats)."""

    __version__ = "0.0.4"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.api = "https://corona.lmao.ninja"
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def get(self, url):
        async with self.session.get(url) as response:
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                return {"failed": "Their appears to be an issue with the API. Please try again later."}
            if response.status == 200:
                try:
                    return data
                except aiohttp.ServerTimeoutError:
                    return {"failed": "Their appears to be an issue with the API. Please try again later."}
            else:
                return {"failed": data["message"]}

    @commands.group(invoke_without_command=True)
    async def covid(self, ctx, *, country: typing.Optional[str]):
        """Stats about Covid-19."""
        if not country:
            async with ctx.typing():
                data = await self.get(self.api + "/all")
            if isinstance(data, dict):
                if data.get("failed") is not None:
                    return await ctx.send(data.get("failed"))
            if not data:
                return await ctx.send("No data available.")
            embed = discord.Embed(color=ctx.author.color, title="Covid-19 Global Statistics")
            embed.add_field(name="Cases", value=humanize_number(data["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data["recovered"]))
            await ctx.send(embed=embed)
        else:
            async with ctx.typing():
                data = await self.get(self.api + "/countries/{}".format(country))
            error = data.get("failed")
            if error is not None:
                return await ctx.send(error)
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
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayCases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Cases Today | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def today(self, ctx):
        """Statistics for today."""
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
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
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayDeaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Deaths Today | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def highestcases(self, ctx):
        """Show the highest cases from countrys overall"""
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["cases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Cases Overall | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def highestdeaths(self, ctx):
        """Show the highest deaths from countrys overall"""
        async with ctx.typing():
            data = await self.get(self.api + "/countries?sort=deaths")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["deaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | Highest Deaths Overall | {}".format(data[0]["country"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[0]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[0]["deaths"]))
            embed.add_field(name="Recovered", value=humanize_number(data[0]["recovered"]))
            embed.add_field(name="Cases Today", value=humanize_number(data[0]["todayCases"]))
            embed.add_field(name="Deaths Today", value=humanize_number(data[0]["todayDeaths"]))
            embed.add_field(name="Critical Condition", value=humanize_number(data[0]["critical"]))
            await ctx.send(embed=embed)

    @covid.command()
    async def topcases(self, ctx, amount: int = 6):
        """Show X countries with top amount of cases. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["cases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Cases ".format(amount),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def topcasestoday(self, ctx, amount: int = 6):
        """Show X countries with top amount of cases today. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayCases"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Cases Today ".format(amount),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def topdeaths(self, ctx, amount: int = 6):
        """Show X countries with top amount of deaths. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["deaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Deaths ".format(amount),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def topdeathstoday(self, ctx, amount: int = 6):
        """Show X countries with top amount of deaths today. Defaults to 6."""
        if amount > 20 or amount < 0:
            return await ctx.send("Invalid amount. Please choose between an amount between 1-20.")
        async with ctx.typing():
            data = await self.get(self.api + "/countries")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            data = sorted(data, key=lambda x: x["todayDeaths"], reverse=True)
            embed = discord.Embed(
                color=ctx.author.color, title="Covid-19 | Top {} Deaths Today ".format(amount),
            )
            for i in range(amount):
                msg = f'**Cases**: {humanize_number(data[i]["cases"])}\n**Deaths**: {humanize_number(data[i]["deaths"])}\n**Recovered**: {humanize_number(data[i]["recovered"])}\n**Cases Today**: {humanize_number(data[i]["todayCases"])}\n**Deaths**: {humanize_number(data[i]["todayDeaths"])}\n**Critical**: {humanize_number(data[i]["critical"])}'
                embed.add_field(name=data[i]["country"], value=msg)
            await ctx.send(embed=embed)

    @covid.command()
    async def state(self, ctx, *, state: str):
        """Show stats for a specific state."""
        async with ctx.typing():
            data = await self.get(self.api + "/states")
            if isinstance(data, dict):
                error = data.get("failed")
                if error is not None:
                    return await ctx.send(error)
            if not data:
                return await ctx.send("No data available.")
            statedata = None
            for i in range(len(data)):
                if data[i]["state"].lower() == state.lower():
                    statedata = i
            if statedata is None:
                return await ctx.send("No statistics/State not found.")
            embed = discord.Embed(
                color=ctx.author.color,
                title="Covid-19 | USA | {} Statistics".format(data[statedata]["state"]),
            )
            embed.add_field(name="Cases", value=humanize_number(data[statedata]["cases"]))
            embed.add_field(name="Deaths", value=humanize_number(data[statedata]["deaths"]))
            embed.add_field(
                name="Cases Today", value=humanize_number(data[statedata]["todayCases"])
            )
            embed.add_field(
                name="Deaths Today", value=humanize_number(data[statedata]["todayDeaths"])
            )
            embed.add_field(name="Active Cases", value=humanize_number(data[statedata]["active"]))
            await ctx.send(embed=embed)
