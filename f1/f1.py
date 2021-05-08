import datetime

import aiohttp
import discord
import tabulate
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, pagify

API_URL = "http://ergast.com/api/f1"
DATE_SUFFIX = {1: "st", 2: "nd", 3: "rd"}


class F1(commands.Cog):
    """F1 data."""

    __version__ = "0.0.3"
    __author__ = "flare"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def get(self, endpoint):
        async with self.session.get(API_URL + endpoint) as response:
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                return {
                    "failed": "Their appears to be an issue with the API. Please try again later."
                }
            if response.status == 200:
                try:
                    return data
                except aiohttp.ServerTimeoutError:
                    return {
                        "failed": "Their appears to be an issue with the API. Please try again later."
                    }
            else:
                return {
                    "failed": f"An error occured processing your request and a returned a {response.status} status code."
                }

    @commands.group()
    async def f1(self, ctx: commands.Context):
        """F1 Group Command"""

    @f1.command()
    async def drivers(self, ctx: commands.Context, year: int = None):
        """F1 drivers by season year."""
        if year is None:
            year = datetime.datetime.now().year
        else:
            if year > datetime.datetime.now().year:
                await ctx.send("You cannot view data from the future silly.")
                return
        data = await self.get(f"/{year}/drivers.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        drivers = data["MRData"]["DriverTable"]["Drivers"]
        if not drivers:
            await ctx.send("No data available.")
            return

        embed = discord.Embed(
            color=await ctx.embed_colour(), title=f"F1 Driver Information - {year}"
        )
        msg = ""
        for driver in sorted(drivers, key=lambda x: int(x["permanentNumber"])):
            msg += f'[{driver["givenName"]} {driver["familyName"]}]({driver["url"]}) - No. {driver["permanentNumber"]} - {driver["nationality"]}\n'
        embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def constructors(self, ctx: commands.Context, year: int = None):
        """F1 constructors by season year."""
        if year is None:
            year = datetime.datetime.now().year
        else:
            if year > datetime.datetime.now().year:
                await ctx.send("You cannot view data from the future silly.")
                return
        data = await self.get(f"/{year}/constructors.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        constructors = data["MRData"]["ConstructorTable"]["Constructors"]
        if not constructors:
            await ctx.send("No data available.")
            return

        embed = discord.Embed(
            color=await ctx.embed_colour(), title=f"F1 Constructor Information - {year}"
        )
        msg = ""
        for constructor in constructors:
            msg += (
                f'[{constructor["name"]}]({constructor["url"]}) - {constructor["nationality"]}\n'
            )
        embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def circuits(self, ctx: commands.Context, year: int = None):
        """F1 circuits by season year."""
        if year is None:
            year = datetime.datetime.now().year
        else:
            if year > datetime.datetime.now().year:
                await ctx.send("You cannot view data from the future silly.")
                return
        data = await self.get(f"/{year}/circuits.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        circuits = data["MRData"]["CircuitTable"]["Circuits"]
        if not circuits:
            await ctx.send("No data available.")
            return

        embed = discord.Embed(
            color=await ctx.embed_colour(), title=f"F1 Circuit Information - {year}"
        )
        msg = ""
        for circuit in circuits:
            msg += f'[{circuit["circuitName"]}]({circuit["url"]}) - {circuit["Location"]["locality"]}, {circuit["Location"]["country"]}\n'
        if len(msg) > 2048:
            for page in pagify(msg, page_length=1024):
                embed.add_field(name="-", value=page, inline=False)
        else:
            embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def recent(self, ctx: commands.Context):
        """F1 most recent race result."""
        data = await self.get(f"/current/last/results.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        results = data["MRData"]["RaceTable"]["Races"][0]
        if not results:
            await ctx.send("No data available.")
            return
        standings = results["Results"]

        embed = discord.Embed(
            color=await ctx.embed_colour(),
            title=f"F1 Race Information - {results['raceName']}",
            url=results["url"],
        )
        msg = ""
        for driver in standings:
            msg += f'**{driver["position"]}**. {driver["Constructor"]["name"]} {driver["Driver"]["givenName"]} {driver["Driver"]["familyName"]} - {driver["status"]}\n'
        embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def race(self, ctx: commands.Context, year: int, round: int):
        """F1 race result."""
        if year > datetime.datetime.now().year:
            await ctx.send("You cannot view data from the future silly.")
            return
        data = await self.get(f"/{year}/{round}/results.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        results = data["MRData"]["RaceTable"]["Races"]
        if not results:
            await ctx.send("No data available.")
            return
        standings = results[0]["Results"]

        embed = discord.Embed(
            color=await ctx.embed_colour(),
            title=f"F1 Race Information - {results['raceName']}",
            url=results["url"],
        )
        msg = ""
        for driver in standings:
            msg += f'**{driver["position"]}**. {driver["Constructor"]["name"]} {driver["Driver"]["givenName"]} {driver["Driver"]["familyName"]} - {driver["status"]}\n'
        embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def schedule(self, ctx: commands.Context, year: int = None):
        """F1 schedule by season year."""
        if year is None:
            year = datetime.datetime.now().year
        else:
            if year > datetime.datetime.now().year:
                await ctx.send("You cannot view data from the future silly.")
                return
        data = await self.get(f"/{year}.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        circuits = data["MRData"]["RaceTable"]["Races"]
        if not circuits:
            await ctx.send("No data available.")
            return

        embed = discord.Embed(
            color=await ctx.embed_colour(), title=f"F1 Circuit Information - {year}"
        )
        msg = ""
        for circuit in circuits:
            time = datetime.datetime.fromisoformat(
                circuit["date"] + "T" + circuit["time"].replace("Z", "")
            )
            date = time.strftime(f"%B {self.ord(time.day)} - %I:%M %p")
            msg += f'Round {circuit["round"]}: [{circuit["raceName"]}]({circuit["url"]}) - {circuit["Circuit"]["circuitName"]} | **{date}**\n'
        if len(msg) > 2048:
            for page in pagify(msg, page_length=1024):
                embed.add_field(name="-", value=page, inline=False)
        else:
            embed.description = msg

        await ctx.send(embed=embed)

    @f1.group()
    async def standings(self, ctx):
        """F1 Standings"""

    @standings.command(name="drivers")
    async def drivers_standings(self, ctx):
        data = await self.get(f"/current/driverStandings.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        results = data["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
        if not results:
            await ctx.send("No data available.")
            return
        data = []
        for driver in results:
            data.append(
                [
                    driver["positionText"],
                    driver["points"],
                    driver["wins"],
                    driver["Driver"]["givenName"] + " " + driver["Driver"]["familyName"],
                    driver["Constructors"][0]["name"],
                ]
            )

        msg = tabulate.tabulate(
            data,
            headers=["Position", "Points", "Wins", "Name", "Constructor"],
            tablefmt="plainfmt",
        )
        await ctx.send(box(msg, lang="apache"))

    @standings.command(name="constructors")
    async def constructors_standings(self, ctx):
        data = await self.get(f"/current/constructorStandings.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        results = data["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]
        if not results:
            await ctx.send("No data available.")
            return
        data = []
        for driver in results:
            data.append(
                [
                    driver["positionText"],
                    driver["points"],
                    driver["wins"],
                    driver["Constructor"]["name"],
                ]
            )

        msg = tabulate.tabulate(
            data, headers=["Position", "Points", "Wins", "Constructor"], tablefmt="plainfmt"
        )
        await ctx.send(box(msg, lang="apache"))

    @f1.command(aliases=["quali", "qualify"])
    async def qualifying(self, ctx: commands.Context, year: int, round: int):
        """F1 race result."""
        if year > datetime.datetime.now().year:
            await ctx.send("You cannot view data from the future silly.")
            return
        data = await self.get(f"/{year}/{round}/qualifying.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        results = data["MRData"]["RaceTable"]["Races"]
        if not results:
            await ctx.send("No data available.")
            return
        standings = results[0]
        drivers = standings["QualifyingResults"]

        embed = discord.Embed(
            color=await ctx.embed_colour(),
            title=f"F1 Qualifying Information - {standings['raceName']}",
            url=standings["url"],
        )
        for driver in drivers:
            embed.add_field(
                name=f'**{driver["position"]}**. {driver["Constructor"]["name"]} {driver["Driver"]["givenName"]} {driver["Driver"]["familyName"]}\n',
                value=f'**Q1**: {driver.get("Q1", "N/A")}\n**Q2**: {driver.get("Q2", "N/A")}\n**Q3**: {driver.get("Q3", "N/A")}',
            )

        await ctx.send(embed=embed)

    def ord(self, n):
        return str(n) + (
            "th" if 4 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        )
