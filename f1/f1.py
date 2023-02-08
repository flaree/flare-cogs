import asyncio
import datetime
import logging

import aiohttp
import discord
import tabulate
from discord.mentions import AllowedMentions
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box, pagify

API_URL = "http://ergast.com/api/f1"
DATE_SUFFIX = {1: "st", 2: "nd", 3: "rd"}

log = logging.getLogger("red.flare.f1")


class F1(commands.Cog):
    """F1 data."""

    __version__ = "0.2.0"
    __author__ = "flare"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=95932766180343808)
        self.config.register_guild(channel=None, role=None)
        self.loop = self.bot.loop.create_task(self.race_loop())

    def cog_unload(self):
        self.loop.cancel()

    async def race_loop(self):
        await self.bot.wait_until_ready()
        while True:
            now = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            tomorrow = (now + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            await asyncio.sleep((tomorrow - now).total_seconds())
            await self.raceday_loop()

    async def raceday_loop(self):
        year = datetime.datetime.now().year
        data = await self.get(f"/{year}.json")
        if data.get("failed"):
            return
        circuits = data["MRData"]["RaceTable"]["Races"]
        if not circuits:
            return
        for circuit in circuits:
            time = datetime.datetime.fromisoformat(
                circuit["date"] + "T" + circuit["time"].replace("Z", "")
            ).replace(tzinfo=datetime.timezone.utc)
            if time.date() == datetime.datetime.now().date():
                data = await self.config.all_guilds()
                for guild_id in data:
                    try:
                        guild = self.bot.get_guild(int(guild_id))
                        if guild is None:
                            log.debug("Guild %d not found", guild)
                            continue
                        channel = guild.get_channel(data[guild_id]["channel"])
                        if channel is None:
                            log.debug("Channel %d not found", channel)
                            continue
                        msg = ""
                        if data[guild_id]["role"] is not None:
                            role = guild.get_role(data[guild_id]["role"])
                            if role is not None:
                                msg += f"{role.mention}, "
                        msg += f"**Race Day**!\n**{circuit['raceName']}** (Round {circuit['round']}) at **{circuit['Circuit']['circuitName']}** is starting today!\n**Race Start**:\n<t:{int(time.timestamp())}:F>\n<t:{int(time.timestamp())}:R>"
                        await channel.send(msg, allowed_mentions=AllowedMentions.all())
                    except Exception as e:
                        log.exception(e)

    async def get(self, endpoint):
        async with self.session.get(API_URL + endpoint) as response:
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                return {
                    "failed": "Their appears to be an issue with the API. Please try again later."
                }
            if response.status != 200:
                return {
                    "failed": f"An error occured processing your request and a returned a {response.status} status code."
                }
            try:
                return data
            except aiohttp.ServerTimeoutError:
                return {
                    "failed": "Their appears to be an issue with the API. Please try again later."
                }

    @commands.group()
    async def f1(self, ctx: commands.Context):
        """F1 Group Command"""

    @f1.command()
    async def drivers(self, ctx: commands.Context, year: int = None):
        """F1 drivers by season year."""
        if year is None:
            year = datetime.datetime.now().year
        elif year > datetime.datetime.now().year:
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
        msg = "".join(
            f'[{driver["givenName"]} {driver["familyName"]}]({driver["url"]}) - No. {driver.get("permanentNumber", "N/A")} - {driver["nationality"]}\n'
            for driver in sorted(drivers, key=lambda x: int(x.get("permanentNumber", 101)))
        )

        embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def constructors(self, ctx: commands.Context, year: int = None):
        """F1 constructors by season year."""
        if year is None:
            year = datetime.datetime.now().year
        elif year > datetime.datetime.now().year:
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
        msg = "".join(
            f'[{constructor["name"]}]({constructor["url"]}) - {constructor["nationality"]}\n'
            for constructor in constructors
        )

        embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def circuits(self, ctx: commands.Context, year: int = None):
        """F1 circuits by season year."""
        if year is None:
            year = datetime.datetime.now().year
        elif year > datetime.datetime.now().year:
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
        msg = "".join(
            f'[{circuit["circuitName"]}]({circuit["url"]}) - {circuit["Location"]["locality"]}, {circuit["Location"]["country"]}\n'
            for circuit in circuits
        )

        if len(msg) > 2048:
            for page in pagify(msg, page_length=1024):
                embed.add_field(name="-", value=page, inline=False)
        else:
            embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def recent(self, ctx: commands.Context):
        """F1 most recent race result."""
        data = await self.get("/current/last/results.json")
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
        msg = "".join(
            f'**{driver["position"]}**. {driver["Constructor"]["name"]} {driver["Driver"]["givenName"]} {driver["Driver"]["familyName"]} - {driver["status"]}\n'
            for driver in standings
        )

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
        results = data["MRData"]["RaceTable"]["Races"][0]
        if not results:
            await ctx.send("No data available.")
            return
        standings = results["Results"]

        embed = discord.Embed(
            color=await ctx.embed_colour(),
            title=f"F1 Race Information - {results['raceName']}",
            url=results.get("url", ""),
        )
        msg = "".join(
            f'**{driver["position"]}**. {driver["Constructor"]["name"]} {driver["Driver"]["givenName"]} {driver["Driver"]["familyName"]} - {driver["status"]}\n'
            for driver in standings
        )

        embed.description = msg

        await ctx.send(embed=embed)

    @f1.command()
    async def schedule(self, ctx: commands.Context, year: int = None):
        """F1 schedule by season year."""
        if year is None:
            year = datetime.datetime.now().year
        elif year > datetime.datetime.now().year:
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
            ).replace(tzinfo=datetime.timezone.utc)
            msg += f'Round {circuit["round"]}: [{circuit["raceName"]}]({circuit["url"]}) - {circuit["Circuit"]["circuitName"]} | **<t:{int(time.timestamp())}:F>**\n'
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
        data = await self.get("/current/driverStandings.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        results = data["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
        if not results:
            await ctx.send("No data available.")
            return
        data = [
            [
                driver["positionText"],
                driver["points"],
                driver["wins"],
                driver["Driver"]["givenName"] + " " + driver["Driver"]["familyName"],
                driver["Constructors"][0]["name"],
            ]
            for driver in results
        ]

        msg = tabulate.tabulate(
            data,
            headers=["Position", "Points", "Wins", "Name", "Constructor"],
            tablefmt="plainfmt",
        )
        await ctx.send(box(msg, lang="apache"))

    @standings.command(name="constructors")
    async def constructors_standings(self, ctx):
        data = await self.get("/current/constructorStandings.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        results = data["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]
        if not results:
            await ctx.send("No data available.")
            return
        data = [
            [
                driver["positionText"],
                driver["points"],
                driver["wins"],
                driver["Constructor"]["name"],
            ]
            for driver in results
        ]

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

    @f1.command(name="next")
    async def _next(self, ctx):
        """Find out when the next F1 Grand Prix is scheduled to take place."""
        year = datetime.datetime.now().year
        data = await self.get(f"/{year}.json")
        if data.get("failed"):
            await ctx.send(data["failed"])
            return
        circuits = data["MRData"]["RaceTable"]["Races"]
        if not circuits:
            await ctx.send("No data available.")
            return

        datetimes = []
        for circuit in circuits:
            time = datetime.datetime.fromisoformat(
                circuit["date"] + "T" + circuit["time"].replace("Z", "")
            ).replace(tzinfo=datetime.timezone.utc)
            circuit["datetime"] = time
            datetimes.append(time)
        try:
            next_date = min(
                (d for d in datetimes if str(d) > str(datetime.date.today())),
                key=lambda s: s - datetime.datetime.now().replace(tzinfo=datetime.timezone.utc),
            )

        except ValueError:
            return await ctx.send("I couldn't find the next F1 race available.")
        for circuit in circuits:
            if circuit["datetime"] == next_date:
                time = datetime.datetime.fromisoformat(
                    circuit["date"] + "T" + circuit["time"].replace("Z", "")
                ).replace(tzinfo=datetime.timezone.utc)
                embed = discord.Embed(
                    color=await ctx.embed_colour(),
                    title=f"F1 Next Race - {circuit['raceName']}",
                    timestamp=time,
                )
                embed.set_footer(text="Race Date:")
                embed.add_field(
                    name="Information",
                    value=f'Round {circuit["round"]}: [{circuit["raceName"]}]({circuit["url"]}) - {circuit["Circuit"]["circuitName"]}\n**Start**:\n<t:{int(time.timestamp())}:F>\n<t:{int(time.timestamp())}:R>',
                )
                await ctx.send(embed=embed)
                return

    @f1.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def subscribe(self, ctx, channel: discord.TextChannel = None):
        """Subscribe a channel to F1 Race Day notifications."""
        if channel is None:
            await self.config.guild(ctx.guild).channel.set(None)
            await ctx.send(
                "Your F1 race day notification channel has been reset. It will no longer post updates."
            )
            return
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Your F1 race day notification channel has been set to {channel.mention}.")

    @f1.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def notify(self, ctx, role: discord.Role = None):
        """Optionally, ping a role during the Race Day notifications."""
        if role is None:
            await self.config.guild(ctx.guild).role.set(None)
            await ctx.send(
                "You have reset the role ping, it will no longer ping a role during the notification."
            )
            return
        await self.config.guild(ctx.guild).role.set(role.id)
        await ctx.send(f"Your F1 race day notification ping role has been set to {role}.")

    def ord(self, n):
        return str(n) + (
            "th" if 4 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        )
