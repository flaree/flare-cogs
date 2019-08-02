import asyncio
import random
import string
import time
from io import BytesIO
from typing import Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps
from prettytable import PrettyTable
from pymongo import MongoClient
from redbot.core import Config, bank, checks, commands
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

client = MongoClient()
db = client["leveler"]


# THANKS TO https://code.sololearn.com/ci42wd5h0UQX/#py FOR THE SIMULATION AND FIXATOR/AIKATERNA/STEVY FOR THE PILLOW HELP/LEVELER


class SimLeague(commands.Cog):
    __version__ = "2.5.2"

    def __init__(self, bot):
        defaults = {
            "levels": {},
            "teams": {},
            "fixtures": [],
            "standings": {},
            "stats": {
                "goals": {},
                "yellows": {},
                "reds": {},
                "penalties": {},
                "assists": {},
                "motm": {},
            },
            "users": [],
            "resultchannel": [],
            "gametime": 1,
            "bettime": 90,
            "htbreak": 5,
            "bettoggle": True,
            "betmax": 10000,
            "betmin": 10,
            "pageamount": 5,
            "mee6": False,
            "probability": {
                "goalchance": 96,
                "yellowchance": 98,
                "redchance": 299,
                "penaltychance": 249,
                "penaltyblock": 0.6,
            },
            "maxplayers": 4,
            "active": False,
            "started": False,
            "betteams": [],
        }
        defaults_user = {"notify": True}
        self.config = Config.get_conf(self, identifier=4268355870, force_registration=True)
        self.config.register_guild(**defaults)
        self.config.register_user(**defaults_user)
        self.bot = bot
        self.bets = {}
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.cache = time.time()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command()
    async def notify(self, ctx, toggle: bool):
        """Set wheter to recieve notifications of matches and results."""
        if toggle:
            await self.config.user(ctx.author).notify.set(toggle)
            await ctx.send("You will recieve a notification on matches and results.")
        else:
            await self.config.user(ctx.author).notify.set(toggle)
            await ctx.send("You will no longer recieve a notification on matches and results.")

    @checks.mod()
    @commands.group(autohelp=True)
    async def simset(self, ctx):
        """Simulation Settings."""
        if ctx.invoked_subcommand is None:
            guild = ctx.guild
            # Display current settings
            gametime = await self.config.guild(guild).gametime()
            htbreak = await self.config.guild(guild).htbreak()
            results = await self.config.guild(guild).resultchannel()
            bettoggle = await self.config.guild(guild).bettoggle()
            mee6 = await self.config.guild(guild).mee6()
            maxplayers = await self.config.guild(guild).maxplayers()
            msg = ""
            msg += "Game Time: 1m for every {}s.\n".format(gametime)
            msg += "Team Limit: {} players.\n".format(maxplayers)
            msg += "HT Break: {}s.\n".format(htbreak)
            msg += "Posting Results: {}.\n".format("Yes" if results else "No")
            msg += "Accepting Bets: {}.\n".format("Yes" if bettoggle else "No")
            if bettoggle:
                bettime = await self.config.guild(guild).bettime()
                betmax = await self.config.guild(guild).betmax()
                betmin = await self.config.guild(guild).betmin()
                msg += "Bet Time: {}s.\n".format(bettime)
                msg += "Max Bet: {}.\n".format(betmax)
                msg += "Min Bet: {}.\n".format(betmin)
            if mee6:
                pages = await self.config.guild(guild).pageamount()
                msg += "Using MEE6 Levels: {}.\n".format("Yes" if mee6 else "No")
                msg += "Mee6 API Pages: {}.\n".format(pages)
            await ctx.send(box(msg))

    @checks.mod()
    @commands.group(autohelp=True)
    async def teamset(self, ctx):
        """Team Settings."""
        pass

    @checks.admin()
    @simset.group(autohelp=True)
    async def bet(self, ctx):
        """Simulation Betting Settings."""
        pass

    @checks.guildowner()
    @simset.group(autohelp=True)
    async def probability(self, ctx):
        """Simulation Probability Settings. May break the cog if changed."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                box("This has the chance to break the game completely, no support is offered.")
            )

    @checks.guildowner()
    @probability.command()
    async def goals(self, ctx, amount: int = 96):
        """Goal probability. Default = 96"""
        if amount > 100 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 100.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["goalchance"] = amount
        await ctx.tick()

    @checks.guildowner()
    @probability.command()
    async def yellow(self, ctx, amount: int = 98):
        """Yellow Card probability. Default = 98"""
        if amount > 100 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 100.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["yellowchance"] = amount
        await ctx.tick()

    @checks.guildowner()
    @simset.command()
    async def maxplayers(self, ctx, amount: int):
        """Set the max team players."""
        if amount < 3 or amount > 7:
            return await ctx.send("Amount must be between 3 and 5.")
        await self.config.guild(ctx.guild).maxplayers.set(amount)
        await ctx.tick()

    @checks.guildowner()
    @probability.command()
    async def red(self, ctx, amount: int = 299):
        """Red Card probability. Default = 299"""
        if amount > 300 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 300.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["redchance"] = amount
        await ctx.tick()

    @checks.guildowner()
    @probability.command()
    async def penalty(self, ctx, amount: int = 249):
        """Penalty Chance probability. Default = 249"""
        if amount > 250 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 250.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["penaltychance"] = amount
        await ctx.tick()

    @checks.guildowner()
    @probability.command()
    async def penaltyblock(self, ctx, amount: float = 0.6):
        """Penalty Block probability. Default = 0.6"""
        if amount > 1 or amount < 0:
            return await ctx.send("Amount must be greater than 0 and less than 1.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["penaltyblock"] = amount
        await ctx.tick()

    @commands.group(autohelp=True)
    async def stats(self, ctx):
        """Sim League Statistics."""
        if ctx.invoked_subcommand is None:
            stats = await self.config.guild(ctx.guild).stats()
            goalscorer = sorted(stats["goals"], key=stats["goals"].get, reverse=True)
            assists = sorted(stats["assists"], key=stats["assists"].get, reverse=True)
            yellows = sorted(stats["yellows"], key=stats["yellows"].get, reverse=True)
            reds = sorted(stats["reds"], key=stats["reds"].get, reverse=True)
            penscored = sorted(
                stats["penalties"], key=lambda x: stats["penalties"][x]["scored"], reverse=True
            )
            penmissed = sorted(
                stats["penalties"], key=lambda x: stats["penalties"][x]["missed"], reverse=True
            )
            msg = ""
            msg += "**Top Goalscorer**: {}\n".format(goalscorer[0] if goalscorer else "None")
            msg += "**Most Assists**: {}\n".format(assists[0] if assists else "None")
            msg += "**Most Yellow Cards**: {}\n".format(yellows[0] if yellows else "None")
            msg += "**Most Red Cards**: {}\n".format(reds[0] if reds else "None")
            msg += "**Penalties Scored**: {}\n".format(penscored[0] if penscored else "None")
            msg += "**Penalties Missed**: {}\n".format(penmissed[0] if penmissed else "None")
            await ctx.maybe_send_embed(msg)

    @checks.admin()
    @bet.command()
    async def time(self, ctx, time: int = 90):
        """Set the time allowed for betting - 120 seconds is the max."""
        if time < 0 or time > 120:
            time = 90
        await self.config.guild(ctx.guild).bettime.set(time)
        await ctx.tick()

    @checks.admin()
    @bet.command()
    async def max(self, ctx, amount: int):
        """Set the max amount for betting."""
        if amount < 1:
            return await ctx.send("Amount must be greater than 0.")
        await self.config.guild(ctx.guild).betmax.set(amount)
        await ctx.tick()

    @checks.admin()
    @bet.command()
    async def min(self, ctx, amount: int):
        """Set the min amount for betting."""
        if amount < 1:
            return await ctx.send("Amount must be greater than 0.")
        await self.config.guild(ctx.guild).betmin.set(amount)
        await ctx.tick()

    @checks.admin()
    @bet.command()
    async def toggle(self, ctx, toggle: bool):
        """Set if betting is enabled or not.
            Toggle must be a valid bool."""
        await self.config.guild(ctx.guild).bettoggle.set(toggle)
        await ctx.tick()

    @checks.admin()
    @simset.command()
    async def gametime(self, ctx, time: float = 1):
        """Set the time each minute takes - 5 seconds is the max. 1 is default."""
        if time < 0 or time > 5:
            time = 90
        await self.config.guild(ctx.guild).gametime.set(time)
        await ctx.tick()

    @checks.admin()
    @simset.command()
    async def halftimebreak(self, ctx, time: int = 1):
        """Set the half time break - 20 seconds is the max. 5 is default."""
        if time < 0 or time > 20:
            time = 5
        await self.config.guild(ctx.guild).htbreak.set(time)
        await ctx.tick()

    @checks.admin()
    @simset.command()
    async def resultchannel(self, ctx, channel: discord.TextChannel):
        """Add a channel for automatic result posting."""
        async with self.config.guild(ctx.guild).resultchannel() as result:
            result.append(channel.id)
        await ctx.tick()

    @checks.admin()
    @simset.command(name="updatecache")
    async def levels_updatecache(self, ctx):
        """Update the level cache."""
        async with ctx.typing():
            mee6 = await self.config.guild(ctx.guild).mee6()
            if mee6:
                await self.update(ctx.guild)
            await self.updatecacheall(ctx.guild)
        await ctx.tick()

    @checks.admin()
    @simset.command(name="mee6", hidden=True)
    async def levels_mee6(self, ctx, true_or_false: bool):
        """Enable mee6 rankings."""
        if true_or_false:
            await self.config.guild(ctx.guild).mee6.set(True)
            await ctx.tick()
        else:
            await self.config.guild(ctx.guild).mee6.set(False)
            await ctx.send("Now using Pikachus rankings.")

    @checks.admin()
    @simset.command(name="pages", hidden=True)
    async def levels_mee6pages(self, ctx, amount: int):
        """Update the amount of mee6 API pages to use. Default is 5, Max is 20."""
        if amount > 20:
            amount = 20
        if amount > 1:
            return await ctx.send("Invalid amount.")
        await self.config.guild(ctx.guild).pages.set(amount)
        await ctx.tick()

    @checks.admin()
    @teamset.command()
    async def role(self, ctx, team: str, *, role: str):
        """Set a teams role."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["role"] = role
        await ctx.tick()

    @checks.admin()
    @teamset.command()
    async def logo(self, ctx, team: str, *, logo: str):
        """Set a teams logo."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["logo"] = logo
        await ctx.tick()

    @checks.admin()
    @teamset.command(usage="<current name> <new name>")
    async def name(self, ctx, team: str, *, newname: str):
        """Set a teams name. Try keep names to one word if possible."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[newname] = teams[team]
            del teams[team]
        async with self.config.guild(ctx.guild).standings() as teams:
            teams[newname] = teams[team]
            del teams[team]
        await ctx.tick()

    @checks.admin()
    @teamset.command()
    async def fullname(self, ctx, team: str, *, fullname: str):
        """Set a teams full name."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["fullname"] = fullname
        await ctx.tick()

    @checks.admin()
    @teamset.group(autohelp=True)
    async def kits(self, ctx):
        """Kit Settings."""
        pass

    @checks.admin()
    @kits.command()
    async def home(self, ctx, team: str, *, kiturl: str):
        """Set a teams home kit."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["kits"]["home"] = kiturl
        await ctx.tick()

    @checks.admin()
    @kits.command()
    async def away(self, ctx, team: str, *, kiturl: str):
        """Set a teams away kit."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["kits"]["away"] = kiturl
        await ctx.tick()

    @checks.admin()
    @kits.command()
    async def third(self, ctx, team: str, *, kiturl: str):
        """Set a teams third kit."""
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Not a valid team.")
            teams[team]["kits"]["third"] = kiturl
        await ctx.tick()

    @checks.mod()
    @commands.command()
    async def register(
        self,
        ctx,
        teamname: str,
        members: commands.Greedy[discord.Member],
        logo: Optional[str] = None,
        *,
        role: str = None,
    ):
        """Register a team.
            Try keep team names to one word if possible."""
        maxplayers = await self.config.guild(ctx.guild).maxplayers()
        if len(members) != maxplayers:
            return await ctx.send(f"You must provide {maxplayers} members.")
        mee6 = await self.config.guild(ctx.guild).mee6()
        if mee6:
            await self.update(ctx.guild)
        names = {x.name: x.id for x in members}
        ids = [x.id for x in members]
        a = []
        memids = await self.config.guild(ctx.guild).users()
        for uid in ids:
            if uid in memids:
                a.append(uid)
        if a:
            b = []
            for ids in a:
                user = self.bot.get_user(ids)
                if user is None:
                    user = await self.bot.fetch_user(ids)
                b.append(user.name)
            return await ctx.send(", ".join(b) + " is/are on a team.")
        await self.config.guild(ctx.guild).users.set(memids + ids)

        async with self.config.guild(ctx.guild).teams() as teams:
            a = []
            teams[teamname] = {
                "members": names,
                "captain": {members[0].name: members[0].id},
                "ids": ids,
                "logo": logo,
                "role": role,
                "cachedlevel": 0,
                "fullname": None,
                "kits": {"home": None, "away": None, "third": None},
            }
        async with self.config.guild(ctx.guild).standings() as standings:
            standings[teamname] = {
                "played": 0,
                "wins": 0,
                "losses": 0,
                "points": 0,
                "gd": 0,
                "gf": 0,
                "ga": 0,
                "draws": 0,
            }
        for uid in ids:
            await self.addrole(ctx, uid, role)
        await ctx.tick()

    @commands.command(name="teams", aliases=["list"])
    async def _list(self, ctx, updatecache: bool = False, mobilefriendly: bool = True):
        """List current teams."""
        if updatecache:
            await self.updatecacheall(ctx.guild)
        teams = await self.config.guild(ctx.guild).teams()
        if not teams:
            return await ctx.send("No teams have been registered.")
        if mobilefriendly:
            embed = discord.Embed(colour=ctx.author.colour)
            msg = await ctx.send(
                "This may take some time depending on the amount of teams currently registered."
            )
            if time.time() - self.cache >= 86400:
                await msg.edit(
                    content="Updating the level cache, please wait. This may take some time."
                )
                await self.updatecacheall(ctx.guild)
                self.cache = time.time()
            async with ctx.typing():
                for team in teams:
                    mems = [x for x in teams[team]["members"].keys()]
                    lvl = teams[team]["cachedlevel"]
                    embed.add_field(
                        name="Team {}".format(team),
                        value="{}**Members**:\n{}\n**Captain**: {}\n**Team Level**: ~{}{}".format(
                            "**Full Name**:\n{}\n".format(teams[team]["fullname"])
                            if teams[team]["fullname"] is not None
                            else "",
                            "\n".join(mems),
                            list(teams[team]["captain"].keys())[0],
                            lvl,
                            "\n**Role**: {}".format(teams[team]["role"])
                            if teams[team]["role"] is not None
                            else "",
                        ),
                        inline=True,
                    )
            await msg.edit(embed=embed, content=None)
        else:
            teamlen = max(*[len(str(i)) for i in teams], 5) + 3
            rolelen = max(*[len(str(teams[i]["role"])) for i in teams], 5) + 3
            caplen = max(*[len(list(teams[i]["captain"].keys())[0]) for i in teams], 5) + 3
            lvllen = 6

            msg = f"{'Team':{teamlen}} {'Level':{lvllen}} {'Captain':{caplen}} {'Role':{rolelen}} {'Members'}\n"
            for team in teams:
                lvl = teams[team]["cachedlevel"]
                captain = list(teams[team]["captain"].keys())[0]
                role = teams[team]["role"]
                non = "None"
                msg += (
                    f"{f'{team}': <{teamlen}} "
                    f"{f'{lvl}': <{lvllen}} "
                    f"{f'{captain}': <{caplen}} "
                    f"{f'{role if role is not None else non}': <{rolelen}}"
                    f"{', '.join(teams[team]['members'])} \n"
                )

            msg = await ctx.send(box(msg, lang="ini"))

    @commands.command()
    async def team(self, ctx, *, team: str):
        """List a team."""
        teams = await self.config.guild(ctx.guild).teams()
        if not teams:
            return await ctx.send("No teams have been registered.")
        if team not in teams:
            return await ctx.send("Team does not exist, ensure that it is correctly capitilized.")
        async with ctx.typing():
            embeds = []
            embed = discord.Embed(
                title="{} {}".format(
                    team,
                    "- {}".format(teams[team]["fullname"])
                    if teams[team]["fullname"] is not None
                    else "",
                ),
                colour=ctx.author.colour,
            )
            embed.add_field(name="Members:", value="\n".join(teams[team]["members"]), inline=True)
            embed.add_field(name="Captain:", value=list(teams[team]["captain"].keys())[0])
            embed.add_field(name="Level:", value=teams[team]["cachedlevel"], inline=True)
            if teams[team]["role"] is not None:
                embed.add_field(name="Role:", value=teams[team]["role"], inline=True)
            if teams[team]["logo"] is not None:
                embed.set_thumbnail(url=teams[team]["logo"])
            embeds.append(embed)
            for kit in teams[team]["kits"]:
                if teams[team]["kits"][kit] is not None:
                    embed = discord.Embed(title=f"{kit.title()} Kit", colour=ctx.author.colour)
                    embed.set_image(url=teams[team]["kits"][kit])
                    embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @checks.mod()
    @simset.command()
    async def createfixtures(self, ctx):
        """Create the fixtures for the current teams."""
        teams = await self.config.guild(ctx.guild).teams()
        teams = list(teams.keys())
        if len(teams) % 2:
            teams.append("DAY OFF")
        n = len(teams)
        matchs = []
        fixtures = []
        return_matchs = []
        for fixture in range(1, n):
            for i in range(n // 2):
                matchs.append((teams[i], teams[n - 1 - i]))
                return_matchs.append((teams[n - 1 - i], teams[i]))
            teams.insert(1, teams.pop())
            fixtures.insert(len(fixtures) // 2, matchs)
            fixtures.append(return_matchs)
            matchs = []
            return_matchs = []

        a = []
        for k, fixture in enumerate(fixtures, 1):
            a.append(f"Week {k}\n----------")
            for i, game in enumerate(fixture, 1):
                a.append(f"Game {i}: {game[0]} vs {game[1]}")
            a.append("----------")
        await self.config.guild(ctx.guild).fixtures.set(fixtures)
        await ctx.tick()

    @commands.command()
    async def fixtures(self, ctx, week: int = None):
        """Show all fixtures."""
        fixtures = await self.config.guild(ctx.guild).fixtures()
        if not fixtures:
            return await ctx.send("No fixtures have been made.")
        if week is None:
            embed = discord.Embed(color=0xFF0000)
            for i, fixture in enumerate(fixtures[:25]):
                a = []
                for game in fixture:
                    a.append(f"{game[0]} vs {game[1]}")
                embed.add_field(name="Week {}".format(i + 1), value="\n".join(a))
            await ctx.send(embed=embed)
            if len(fixtures) > 25:
                embed = discord.Embed(color=0xFF0000)
                for i, fixture in enumerate(fixtures[25:], 25):
                    a = []
                    for game in fixture:
                        a.append(f"{game[0]} vs {game[1]}")
                    embed.add_field(name="Week {}".format(i + 1), value="\n".join(a))
                await ctx.send(embed=embed)
        else:
            try:
                games = fixtures
                games.reverse()
                games.append("None")
                games.reverse()
                games = games[week]
            except IndexError:
                return await ctx.send("Invalid gameweek.")
            a = []
            for fixture in games:
                a.append(f"{fixture[0]} vs {fixture[1]}")
            await ctx.maybe_send_embed("\n".join(a))

    @commands.command()
    async def standings(self, ctx, verbose: bool = False):
        """Current sim standings."""
        standings = await self.config.guild(ctx.guild).standings()
        if standings is None:
            return await ctx.send("The table is empty.")
        if not verbose:
            t = PrettyTable(["Team", "Wins", "Losses", "Played", "Points"])
            for x in sorted(
                standings,
                key=lambda x: (standings[x]["points"], standings[x]["gd"], standings[x]["gf"]),
                reverse=True,
            ):
                t.add_row(
                    [
                        x,
                        standings[x]["wins"],
                        standings[x]["losses"],
                        standings[x]["played"],
                        standings[x]["points"],
                    ]
                )
            await ctx.send("```" + str(t) + "```")
        else:
            t = PrettyTable(
                ["Team", "Wins", "Losses", "Draws", "Played", "Points", "GD", "GF", "GA"]
            )
            for x in sorted(
                standings,
                key=lambda x: (standings[x]["points"], standings[x]["gd"], standings[x]["gf"]),
                reverse=True,
            ):
                t.add_row(
                    [
                        x,
                        standings[x]["wins"],
                        standings[x]["losses"],
                        standings[x]["draws"],
                        standings[x]["played"],
                        standings[x]["points"],
                        standings[x]["gd"],
                        standings[x]["gf"],
                        standings[x]["ga"],
                    ]
                )
            await ctx.send("```" + str(t) + "```")

    @checks.guildowner()
    @simset.group()
    async def clear(self, ctx):
        """SimLeague Clear Settings"""
        pass

    @checks.guildowner()
    @clear.command(name="all")
    async def clear_all(self, ctx):
        """Clear all teams, stats etc."""
        await self.config.guild(ctx.guild).clear()
        await self.config.guild(ctx.guild).standings.set({})
        await self.config.guild(ctx.guild).stats.set({})
        await ctx.tick()

    @checks.guildowner()
    @clear.command(name="stats")
    async def clear_stats(self, ctx):
        """Clear standings and player stats."""
        await self.config.guild(ctx.guild).standings.set({})
        teams = await self.config.guild(ctx.guild).teams()
        async with self.config.guild(ctx.guild).standings() as standings:
            for team in teams:
                standings[team] = {
                    "played": 0,
                    "wins": 0,
                    "losses": 0,
                    "points": 0,
                    "gd": 0,
                    "gf": 0,
                    "ga": 0,
                    "draws": 0,
                }
        await self.config.guild(ctx.guild).stats.set({})
        await ctx.tick()

    @stats.command(name="goals", alias=["topscorer", "topscorers"])
    async def _goals(self, ctx):
        """Players with the most goals."""
        stats = await self.config.guild(ctx.guild).stats()
        stats = stats["goals"]
        if stats:
            a = []
            for k in sorted(stats, key=stats.get, reverse=True):
                a.append(f"{k} - {stats[k]}")
            embed = discord.Embed(
                title="Top Scorers", description="\n".join(a[:10]), colour=0xFF0000
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No stats available.")

    @stats.command(aliases=["yellowcards"])
    async def yellows(self, ctx):
        """Players with the most yellow cards."""
        stats = await self.config.guild(ctx.guild).stats()
        stats = stats["yellows"]
        if stats:
            a = []
            for k in sorted(stats, key=stats.get, reverse=True):
                a.append(f"{k} - {stats[k]}")
            embed = discord.Embed(
                title="Most Yellow Cards", description="\n".join(a[:10]), colour=0xFF0000
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No stats available.")

    @stats.command(alies=["redcards"])
    async def reds(self, ctx):
        """Players with the most red cards."""
        stats = await self.config.guild(ctx.guild).stats()
        stats = stats["reds"]
        if stats:
            a = []
            for k in sorted(stats, key=stats.get, reverse=True):
                a.append(f"{k} - {stats[k]}")
            embed = discord.Embed(
                title="Most Red Cards", description="\n".join(a[:10]), colour=0xFF0000
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No stats available.")

    @stats.command(alies=["motms"])
    async def motm(self, ctx):
        """Players with the most MOTMs."""
        stats = await self.config.guild(ctx.guild).stats()
        stats = stats["motm"]
        if stats:
            a = []
            for k in sorted(stats, key=stats.get, reverse=True):
                user = self.bot.get_user(k)
                if user is None:
                    user = await self.bot.fetch_user(k)
                a.append(f"{user.name} - {stats[k]}")
            embed = discord.Embed(
                title="Most MOTMs", description="\n".join(a[:10]), colour=0xFF0000
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No stats available.")

    @stats.command()
    async def penalties(self, ctx):
        """Penalties scored and missed statistics."""
        stats = await self.config.guild(ctx.guild).stats()
        stats = stats["penalties"]
        if stats:
            a = []
            b = []
            for k in sorted(stats, key=lambda x: stats[x]["scored"], reverse=True):
                a.append(f"{k} - {stats[k]['scored']}")
            for k in sorted(stats, key=lambda x: stats[x]["missed"], reverse=True):
                b.append(f"{k} - {stats[k]['missed']}")
            embed = discord.Embed(title="Penalty Statistics", colour=0xFF0000)
            embed.add_field(name="Penalties Scored", value="\n".join(a))
            embed.add_field(name="Penalties Missed", value="\n".join(b))
            await ctx.send(embed=embed)
        else:
            await ctx.send("No stats available.")

    @stats.command()
    async def assists(self, ctx):
        """Players with the most assists."""
        stats = await self.config.guild(ctx.guild).stats()
        stats = stats["assists"]
        if stats:
            a = []
            for k in sorted(stats, key=stats.get, reverse=True):
                a.append(f"{k} - {stats[k]}")
            embed = discord.Embed(
                title="Assist Statistics", description="\n".join(a), colour=0xFF0000
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No stats available.")

    @checks.mod()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.guild)
    @commands.bot_has_permissions(manage_roles=True, manage_messages=True)
    @commands.command(aliases=["playsim", "simulate"])
    async def sim(self, ctx, team1: str, team2: str):
        """Manually sim a game."""
        uff = await self.config.guild(ctx.guild).mee6()

        teams = await self.config.guild(ctx.guild).teams()
        if team1 not in teams or team2 not in teams:
            return await ctx.send("One of those teams do not exist.")
        if team1 == team2:
            return await ctx.send("You can't sim two of the same teams silly.")
        if uff:
            msg = await ctx.send("Updating levels. Please wait...")
            await self.update(ctx.guild)
            await msg.delete()
        msg = await ctx.send("Updating cached levels...")
        await self.updatecachegame(ctx.guild, team1, team2)
        await msg.delete()
        teams = await self.config.guild(ctx.guild).teams()
        await asyncio.sleep(2)
        lvl1 = teams[team1]["cachedlevel"]
        lvl2 = teams[team2]["cachedlevel"]
        homewin = lvl2 / lvl1
        awaywin = lvl1 / lvl2
        try:
            draw = homewin / awaywin
        except ZeroDivisionError:
            draw = 0.5
        await self.config.guild(ctx.guild).active.set(True)
        await self.config.guild(ctx.guild).betteams.set([team1, team2])
        goals = {}
        assists = {}
        reds = {team1: 0, team2: 0}
        bettime = await self.config.guild(ctx.guild).bettime()

        await self.matchnotif(ctx, team1, team2)
        bet = await ctx.send(
            "Betting is now open, game will commence in {} seconds.\nUsage: {}bet <amount> <team>".format(
                bettime, ctx.prefix
            )
        )
        for i in range(1, bettime):
            if i % 5 == 0:
                await bet.edit(
                    content="Betting is now open, game will commence in {} seconds.\nUsage: {}bet <amount> <team>".format(
                        bettime - i, ctx.prefix
                    )
                )
            await asyncio.sleep(1)
        await bet.delete()
        probability = await self.config.guild(ctx.guild).probability()
        await self.config.guild(ctx.guild).started.set(True)
        team1players = list(teams[team1]["members"].keys())
        team2players = list(teams[team2]["members"].keys())
        logos = ["sky", "bt", "bein", "bbc"]
        yellowcards = []
        logo = random.choice(logos)
        motm = {}
        events = False

        yC_team1 = []
        rC_team1 = []
        injury_team1 = []
        sub_in_team1 = []
        sub_out_team1 = []
        sub_count1 = 0
        rc_count1 = 0
        score_count1 = 0
        injury_count1 = 0
        team1Stats = [
            team1,
            yC_team1,
            rC_team1,
            injury_team1,
            sub_in_team1,
            sub_out_team1,
            sub_count1,
            rc_count1,
            score_count1,
            injury_count1,
        ]

        yC_team2 = []
        rC_team2 = []
        injury_team2 = []
        sub_in_team2 = []
        sub_out_team2 = []
        sub_count2 = 0
        rc_count2 = 0
        score_count2 = 0
        injury_count2 = 0
        team2Stats = [
            team2,
            yC_team2,
            rC_team2,
            injury_team2,
            sub_in_team2,
            sub_out_team2,
            sub_count2,
            rc_count2,
            score_count2,
            injury_count2,
        ]

        async def TeamWeightChance(ctx, t1totalxp, t2totalxp, reds1: int, reds2: int):
            if t1totalxp < 2:
                t1totalxp = 1
            if t2totalxp < 2:
                t2totalxp = 1
            redst1 = reds1 / 10
            redst2 = reds2 / 10
            if redst1 == 0:
                redst1 = 1
            if redst2 == 0:
                redst2 = 1
            total = ["A"] * int((t1totalxp // redst1)) + ["B"] * int((t2totalxp // redst2))
            rdmint = random.choice(total)
            if rdmint == "A":
                return team1Stats
            else:
                return team2Stats

        async def TeamChance():
            rndint = random.randint(1, 10)
            if rndint >= 5:
                return team1Stats
            else:
                return team2Stats

        async def PlayerGenerator(event, team, yc, rc):
            random.shuffle(team1players)
            random.shuffle(team2players)
            output = []
            if team == team1:
                fs_players = team1players
                yc = yC_team1
                rc = rC_team1
            elif team == team2:
                fs_players = team2players
                yc = yC_team2
                rc = rC_team2
            if event == 0:
                rosterUpdate = [i for i in fs_players if i not in rc]
                if len(rosterUpdate) == 0:
                    return await ctx.send(
                        "Game abandoned, no score recorded due to no players remaining."
                    )
                isassist = False
                assist = random.randint(0, 100)
                if assist > 20:
                    isassist = True
                if len(rosterUpdate) < 3:
                    isassist = False
                if isassist:
                    player = random.choice(rosterUpdate)
                    rosterUpdate.remove(player)
                    assister = random.choice(rosterUpdate)
                    output = [team, player, assister]
                else:
                    player = random.choice(rosterUpdate)
                    output = [team, player]
                return output
            elif event == 1:
                rosterUpdate = [i for i in fs_players if i not in rc]
                if len(rosterUpdate) == 0:
                    return await ctx.send(
                        "Game abandoned, no score recorded due to no players remaining."
                    )
                player = random.choice(rosterUpdate)
                if player in yc or player in yellowcards:
                    output = [team, player, 2]
                    return output
                else:
                    output = [team, player]
                    return output
            elif event == 2 or event == 3:
                rosterUpdate = [i for i in fs_players if i not in rc]
                if len(rosterUpdate) == 0:
                    return await ctx.send(
                        "Game abandoned, no score recorded due to no players remaining."
                    )
                player_out = random.choice(rosterUpdate)
                output = [team, player_out]
                return output

        # Start of Simulation!
        im = await self.walkout(ctx, team1, "home")
        im2 = await self.walkout(ctx, team2, "away")
        await ctx.send("Teams:", file=im)
        await ctx.send(file=im2)
        timemsg = await ctx.send("Kickoff!")
        gametime = await self.config.guild(ctx.guild).gametime()
        for min in range(1, 91):
            await asyncio.sleep(gametime)
            if min % 5 == 0:
                await timemsg.edit(content="Minute: {}".format(min))
            if events is False:
                gC = await self.goalChance(ctx.guild, probability)
                if gC is True:
                    teamStats = await TeamWeightChance(ctx, lvl1, lvl2, reds[team1], reds[team2])
                    playerGoal = await PlayerGenerator(0, teamStats[0], teamStats[1], teamStats[2])
                    teamStats[8] += 1
                    async with self.config.guild(ctx.guild).stats() as stats:
                        if playerGoal[1] not in stats["goals"]:
                            stats["goals"][playerGoal[1]] = 1
                        else:
                            stats["goals"][playerGoal[1]] += 1
                        if len(playerGoal) == 3:
                            if playerGoal[2] not in stats["assists"]:
                                stats["assists"][playerGoal[2]] = 1
                            else:
                                stats["assists"][playerGoal[2]] += 1
                    events = True
                    uid = teams[str(playerGoal[0])]["members"][playerGoal[1]]
                    if len(playerGoal) == 3:
                        assister = teams[str(playerGoal[0])]["members"][playerGoal[2]]
                        user2 = self.bot.get_user(assister)
                        if user2 is None:
                            user2 = await self.bot.fetch_user(uid)
                        if user2 not in motm:
                            motm[user2] = 1
                        else:
                            motm[user2] += 1
                        if user2.id not in assists:
                            assists[user2.id] = 1
                        else:
                            assists[user2.id] += 1
                    user = self.bot.get_user(uid)
                    if user is None:
                        user = await self.bot.fetch_user(uid)
                    if user not in motm:
                        motm[user] = 2
                    else:
                        motm[user] += 2
                    if user.id not in goals:
                        goals[user.id] = 1
                    else:
                        goals[user.id] += 1
                    if len(playerGoal) == 3:
                        image = await self.simpic(
                            ctx,
                            str(min),
                            "goal",
                            user,
                            team1,
                            team2,
                            str(playerGoal[0]),
                            str(team1Stats[8]),
                            str(team2Stats[8]),
                            user2,
                        )
                    else:
                        image = await self.simpic(
                            ctx,
                            str(min),
                            "goal",
                            user,
                            team1,
                            team2,
                            str(playerGoal[0]),
                            str(team1Stats[8]),
                            str(team2Stats[8]),
                        )
                    await ctx.send(file=image)
            if events is False:
                pC = await self.penaltyChance(ctx.guild, probability)
                if pC is True:
                    teamStats = await TeamWeightChance(ctx, lvl1, lvl2, reds[team1], reds[team2])
                    playerPenalty = await PlayerGenerator(
                        3, teamStats[0], teamStats[1], teamStats[2]
                    )
                    image = await self.penaltyimg(
                        ctx, str(playerPenalty[0]), str(min), playerPenalty[1]
                    )
                    await ctx.send(file=image)
                    pB = await self.penaltyBlock(ctx.guild, probability)
                    if pB is True:
                        events = True
                        uid = teams[str(playerPenalty[0])]["members"][playerPenalty[1]]
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerPenalty[1] not in stats["penalties"]:
                                stats["penalties"][playerPenalty[1]] = {"scored": 0, "missed": 1}
                            else:
                                stats["penalties"][playerPenalty[1]]["missed"] += 1
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
                        image = await self.simpic(
                            ctx,
                            str(min),
                            "penmiss",
                            user,
                            team1,
                            team2,
                            str(playerPenalty[0]),
                            str(team1Stats[8]),
                            str(team2Stats[8]),
                        )
                        await ctx.send(file=image)
                    else:
                        teamStats[8] += 1
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerPenalty[1] not in stats["goals"]:
                                stats["goals"][playerPenalty[1]] = 1
                            else:
                                stats["goals"][playerPenalty[1]] += 1
                            if playerPenalty[1] not in stats["penalties"]:
                                stats["penalties"][playerPenalty[1]] = {"scored": 1, "missed": 0}
                            else:
                                stats["penalties"][playerPenalty[1]]["scored"] += 1
                        events = True
                        uid = teams[str(playerPenalty[0])]["members"][playerPenalty[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
                        if user not in motm:
                            motm[user] = 2
                        else:
                            motm[user] += 2
                        if user.id not in goals:
                            goals[user.id] = 1
                        else:
                            goals[user.id] += 1
                        image = await self.simpic(
                            ctx,
                            str(min),
                            "penscore",
                            user,
                            team1,
                            team2,
                            str(playerPenalty[0]),
                            str(team1Stats[8]),
                            str(team2Stats[8]),
                        )
                        await ctx.send(file=image)
            if events is False:
                yC = await self.yCardChance(ctx.guild, probability)
                if yC is True:
                    teamStats = await TeamChance()
                    playerYellow = await PlayerGenerator(
                        1, teamStats[0], teamStats[1], teamStats[2]
                    )
                    if len(playerYellow) == 3:
                        teamStats[7] += 1
                        teamStats[2].append(playerYellow[1])
                        async with self.config.guild(ctx.guild).stats() as stats:
                            reds[str(playerYellow[0])] += 1
                            if playerYellow[1] not in stats["reds"]:
                                stats["reds"][playerYellow[1]] = 1
                                stats["yellows"][playerYellow[1]] += 1
                            else:

                                stats["yellows"][playerYellow[1]] += 1
                                stats["reds"][playerYellow[1]] += 1
                        events = True
                        uid = teams[str(playerYellow[0])]["members"][playerYellow[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
                        if user not in motm:
                            motm[user] = -2
                        else:
                            motm[user] += -2
                        image = await self.simpic(
                            ctx,
                            str(min),
                            "2yellow",
                            user,
                            team1,
                            team2,
                            str(playerYellow[0]),
                            str(team1Stats[8]),
                            str(team2Stats[8]),
                            None,
                            str(
                                len(teams[str(str(playerYellow[0]))]["ids"]) - (int(teamStats[7]))
                            ),
                        )
                        await ctx.send(file=image)
                    else:
                        teamStats[1].append(playerYellow[1])
                        yellowcards.append(str(playerYellow[1]))
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerYellow[1] not in stats["yellows"]:
                                stats["yellows"][playerYellow[1]] = 1
                            else:
                                stats["yellows"][playerYellow[1]] += 1
                        events = True
                        uid = teams[str(playerYellow[0])]["members"][playerYellow[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
                        if user not in motm:
                            motm[user] = -1
                        else:
                            motm[user] += -1
                        image = await self.simpic(
                            ctx,
                            str(min),
                            "yellow",
                            user,
                            team1,
                            team2,
                            str(playerYellow[0]),
                            str(team1Stats[8]),
                            str(team2Stats[8]),
                        )
                        await ctx.send(file=image)
            if events is False:
                rC = await self.rCardChance(ctx.guild, probability)
                if rC is True:
                    teamStats = await TeamChance()
                    playerRed = await PlayerGenerator(2, teamStats[0], teamStats[1], teamStats[2])
                    teamStats[7] += 1
                    async with self.config.guild(ctx.guild).stats() as stats:
                        if playerRed[1] not in stats["reds"]:
                            stats["reds"][playerRed[1]] = 1
                        else:
                            stats["reds"][playerRed[1]] += 1
                    reds[str(playerRed[0])] += 1
                    teamStats[2].append(playerRed[1])
                    events = True
                    uid = teams[str(playerRed[0])]["members"][playerRed[1]]
                    user = self.bot.get_user(uid)
                    if user is None:
                        user = await self.bot.fetch_user(uid)
                    if user not in motm:
                        motm[user] = -2
                    else:
                        motm[user] += -2
                    image = await self.simpic(
                        ctx,
                        str(min),
                        "red",
                        user,
                        team1,
                        team2,
                        str(playerRed[0]),
                        str(team1Stats[8]),
                        str(team2Stats[8]),
                        None,
                        str(len(teams[str(str(playerRed[0]))]["ids"]) - (int(teamStats[7]))),
                    )
                    await ctx.send(file=image)
            if events is False:
                pass
            events = False
            if min == 45:
                added = random.randint(1, 5)
                im = await self.extratime(ctx, added)
                await ctx.send(file=im)
                s = 45
                for i in range(added):
                    s += 1
                    gC = await self.goalChance(ctx.guild, probability)
                    if gC is True:
                        teamStats = await TeamWeightChance(
                            ctx, lvl1, lvl2, reds[team1], reds[team2]
                        )
                        playerGoal = await PlayerGenerator(
                            0, teamStats[0], teamStats[1], teamStats[2]
                        )
                        teamStats[8] += 1
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerGoal[1] not in stats["goals"]:
                                stats["goals"][playerGoal[1]] = 1
                            else:
                                stats["goals"][playerGoal[1]] += 1
                            if len(playerGoal) == 3:
                                if playerGoal[2] not in stats["assists"]:
                                    stats["assists"][playerGoal[2]] = 1
                                else:
                                    stats["assists"][playerGoal[2]] += 1
                        if len(playerGoal) == 3:
                            assister = teams[str(playerGoal[0])]["members"][playerGoal[2]]
                            user2 = self.bot.get_user(assister)
                            if user2 is None:
                                user2 = await self.bot.fetch_user(uid)
                            if user2 not in motm:
                                motm[user2] = 1
                            else:
                                motm[user2] += 1
                            if user2.id not in assists:
                                assists[user2.id] = 1
                            else:
                                assists[user2.id] += 1
                        events = True
                        uid = teams[str(playerGoal[0])]["members"][playerGoal[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
                        if user not in motm:
                            motm[user] = 2
                        else:
                            motm[user] += 2
                        if user.id not in goals:
                            goals[user.id] = 1
                        else:
                            goals[user.id] += 1
                        if len(playerGoal) == 3:
                            image = await self.simpic(
                                ctx,
                                str(min) + "+" + str(i + 1),
                                "goal",
                                user,
                                team1,
                                team2,
                                str(playerGoal[0]),
                                str(team1Stats[8]),
                                str(team2Stats[8]),
                                user2,
                            )
                        else:
                            image = await self.simpic(
                                ctx,
                                str(min) + "+" + str(i + 1),
                                "goal",
                                user,
                                team1,
                                team2,
                                str(playerGoal[0]),
                                str(team1Stats[8]),
                                str(team2Stats[8]),
                            )
                        await ctx.send(file=image)
                    await asyncio.sleep(gametime)
                    events = False
                    ht = await self.config.guild(ctx.guild).htbreak()
                im = await self.timepic(
                    ctx, team1, team2, str(team1Stats[8]), str(team2Stats[8]), "HT", logo
                )
                await ctx.send(file=im)
                await asyncio.sleep(ht)
                await timemsg.delete()
                timemsg = await ctx.send("Second Half!")

            if min == 90:
                added = random.randint(1, 5)
                im = await self.extratime(ctx, added)
                await ctx.send(file=im)
                s = 90
                for i in range(added):
                    s += 1
                    gC = await self.goalChance(ctx.guild, probability)
                    if gC is True:
                        teamStats = await TeamWeightChance(
                            ctx, lvl1, lvl2, reds[team1], reds[team2]
                        )
                        playerGoal = await PlayerGenerator(
                            0, teamStats[0], teamStats[1], teamStats[2]
                        )
                        teamStats[8] += 1
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerGoal[1] not in stats["goals"]:
                                stats["goals"][playerGoal[1]] = 1
                            else:
                                stats["goals"][playerGoal[1]] += 1
                            if len(playerGoal) == 3:
                                if playerGoal[2] not in stats["assists"]:
                                    stats["assists"][playerGoal[2]] = 1
                                else:
                                    stats["assists"][playerGoal[2]] += 1
                        if len(playerGoal) == 3:
                            assister = teams[str(playerGoal[0])]["members"][playerGoal[2]]
                            user2 = self.bot.get_user(assister)
                            if user2 is None:
                                user2 = await self.bot.fetch_user(uid)
                            if user2 not in motm:
                                motm[user2] = 1
                            else:
                                motm[user2] += 1
                            if user2.id not in assists:
                                assists[user2.id] = 1
                            else:
                                assists[user2.id] += 1
                        events = True
                        uid = teams[str(playerGoal[0])]["members"][playerGoal[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
                        if user not in motm:
                            motm[user] = 2
                        else:
                            motm[user] += 2
                        if user.id not in goals:
                            goals[user.id] = 1
                        else:
                            goals[user.id] += 1
                        if len(playerGoal) == 3:
                            image = await self.simpic(
                                ctx,
                                str(min) + "+" + str(i + 1),
                                "goal",
                                user,
                                team1,
                                team2,
                                str(playerGoal[0]),
                                str(team1Stats[8]),
                                str(team2Stats[8]),
                                user2,
                            )
                        else:
                            image = await self.simpic(
                                ctx,
                                str(min) + "+" + str(i + 1),
                                "goal",
                                user,
                                team1,
                                team2,
                                str(playerGoal[0]),
                                str(team1Stats[8]),
                                str(team2Stats[8]),
                            )
                        await ctx.send(file=image)
                    await asyncio.sleep(gametime)
                    events = False
                im = await self.timepic(
                    ctx, team1, team2, str(team1Stats[8]), str(team2Stats[8]), "FT", logo
                )
                await timemsg.delete()
                await ctx.send(file=im)
                if team1Stats[8] > team2Stats[8]:
                    async with self.config.guild(ctx.guild).standings() as standings:
                        standings[team1]["wins"] += 1
                        standings[team1]["points"] += 3
                        standings[team1]["played"] += 1
                        standings[team2]["losses"] += 1
                        standings[team2]["played"] += 1
                        t = await self.payout(ctx.guild, team1, homewin)
                if team1Stats[8] < team2Stats[8]:
                    async with self.config.guild(ctx.guild).standings() as standings:
                        standings[team2]["points"] += 3
                        standings[team2]["wins"] += 1
                        standings[team2]["played"] += 1
                        standings[team1]["losses"] += 1
                        standings[team1]["played"] += 1
                        t = await self.payout(ctx.guild, team2, awaywin)
                if team1Stats[8] == team2Stats[8]:
                    async with self.config.guild(ctx.guild).standings() as standings:
                        standings[team1]["played"] += 1
                        standings[team2]["played"] += 1
                        standings[team1]["points"] += 1
                        standings[team2]["points"] += 1
                        standings[team2]["draws"] += 1
                        standings[team1]["draws"] += 1
                        t = await self.payout(ctx.guild, "draw", draw)
                team1gd = team1Stats[8] - team2Stats[8]
                team2gd = team2Stats[8] - team1Stats[8]
                async with self.config.guild(ctx.guild).standings() as standings:
                    if team1gd != 0:
                        standings[team1]["gd"] += team1gd
                    if team2gd != 0:
                        standings[team2]["gd"] += team2gd
                    if team2Stats[8] != 0:
                        standings[team2]["gf"] += team2Stats[8]
                        standings[team1]["ga"] += team2Stats[8]
                    if team1Stats[8] != 0:
                        standings[team1]["gf"] += team1Stats[8]
                        standings[team2]["ga"] += team1Stats[8]
        await self.postresults(ctx, team1, team2, team1Stats[8], team2Stats[8])
        await self.config.guild(ctx.guild).active.set(False)
        await self.config.guild(ctx.guild).started.set(False)
        await self.config.guild(ctx.guild).betteams.set([])
        self.bets = {}
        if motm:
            motmwinner = sorted(motm, key=motm.get, reverse=True)[0]
            if motmwinner.id in goals:
                motmgoals = goals[motmwinner.id]
            else:
                motmgoals = 0
            if motmwinner.id in assists:
                motmassists = assists[motmwinner.id]
            else:
                motmassists = 0
            try:
                await bank.deposit_credits(
                    self.bot.get_user(motmwinner.id), (25 * motmgoals) + (10 * motmassists)
                )
            except AttributeError:
                pass
            im = await self.motmpic(
                ctx,
                motmwinner,
                team1 if motmwinner.id in teams[team1]["ids"] else team2,
                motmgoals,
                motmassists,
            )
            async with self.config.guild(ctx.guild).stats() as stats:
                if playerGoal[1] not in stats["motm"]:
                    stats["motm"][motmwinner.id] = 1
                else:
                    stats["motm"][motmwinner.id] += 1
            await ctx.send(file=im)
        if t is not None:
            await ctx.send("Bet Winners:\n" + t)

    async def bet_conditions(self, ctx, bet, team):
        bettoggle = await self.config.guild(ctx.guild).bettoggle()
        active = await self.config.guild(ctx.guild).active()
        started = await self.config.guild(ctx.guild).started()
        if not bettoggle:
            return await ctx.send("Betting is currently disabled.")
        if not active:
            await ctx.send("There isn't a game onright now.")
            return False
        elif started:
            try:
                await ctx.author.send("You can't place a bet after the game has started.")
            except discord.HTTPException:
                await ctx.send(
                    "Maybe you should unblock me or turn off privacy settings if you want to bet ¯\\_(ツ)_/¯. {}".format(
                        ctx.author.mention
                    )
                )
            return False
        elif ctx.author.id in self.bets:
            await ctx.send("You have already entered a bet for the game.")
            return False
        teams = await self.config.guild(ctx.guild).teams()
        if team not in teams and team != "draw":
            await ctx.send("That team isn't currently playing.")
            return False

        minbet = await self.config.guild(ctx.guild).betmin()
        if bet < minbet:
            await ctx.send("The minimum bet is {}".format(minbet))
            return False
        maxbet = await self.config.guild(ctx.guild).betmax()
        if bet > maxbet:
            await ctx.send("The maximum bet is {}".format(maxbet))
            return False

        if not await bank.can_spend(ctx.author, bet):
            await ctx.send("You do not have enough money to cover the bet.")
            return False
        else:
            return True

    @commands.command(name="bet")
    async def _bet(self, ctx, bet: int, *, team: str):
        """Bet on a team or a draw."""
        if await self.bet_conditions(ctx, bet, team):
            self.bets[ctx.author] = {"Bets": [(team, bet)]}
            currency = await bank.get_currency_name(ctx.guild)
            await bank.withdraw_credits(ctx.author, bet)
            await ctx.send(f"{ctx.author.mention} placed a {bet} {currency} bet on {str(team)}.")

    async def payout(self, guild, winner, odds):
        if winner is None:
            return None
        if odds > 2.5:
            odds = 2.5
        bet_winners = []
        for better in self.bets:
            for team, bet in self.bets[better]["Bets"]:
                if team == winner:
                    bet_winners.append(f"{better.mention} - Winnings: {int(bet + (bet * odds))}")
                    await bank.deposit_credits(better, int(bet + (bet * odds)))
        return "\n".join(bet_winners) if bet_winners else None

    async def simpic(
        self,
        ctx,
        time,
        event,
        player,
        team1,
        team2,
        teamevent,
        score1,
        score2,
        assister=None,
        men: int = None,
    ):
        maps = {
            "goal": "GOALLLLL!",
            "yellow": "YELLOW CARD!",
            "red": "RED CARD! ({} Men!)".format(men),
            "2yellow": "2nd YELLOW! RED!",
            "penscore": "GOALLLLL! (PENALTY)",
            "penmiss": "PENALTY MISSED!",
        }
        font_bold_file = f"{bundled_data_path(self)}/font_bold.ttf"
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        font_unicode_file = f"{bundled_data_path(self)}/unicode.ttf"
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        general_info_fnt = ImageFont.truetype(font_bold_file, 15, encoding="utf-8")
        level_label_fnt = ImageFont.truetype(font_bold_file, 22, encoding="utf-8")
        rank_avatar = BytesIO()
        await player.avatar_url.save(rank_avatar, seek_begin=True)
        teams = await self.config.guild(ctx.guild).teams()
        if event != "yellow" or event != "goal":
            server_icon = await self.getimg(
                teams[teamevent]["logo"]
                if teams[teamevent]["logo"] is not None
                else "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/A_blank_black_picture.jpg/1536px-A_blank_black_picture.jpg"
            )
        if event == "yellow":
            server_icon = await self.getimg(
                "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Yellow_card.svg/788px-Yellow_card.svg.png"
            )
        if event == "red":
            server_icon = await self.getimg(
                "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Red_card.svg/788px-Red_card.svg.png"
            )
        if event == "2yellow":
            server_icon = await self.getimg(
                "https://cdn.imgbin.com/16/2/12/imgbin-penalty-card-red-card-yellow-card-football-7QjpVbCPUywdmmVAh8MH2aSv6.jpg"
            )

        profile_image = Image.open(rank_avatar).convert("RGBA")
        server_icon_image = Image.open(server_icon).convert("RGBA")

        # set canvas
        width = 360
        if assister is not None:
            height = 120
        else:
            height = 100
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (width, height), bg_color)
        process = Image.new("RGBA", (width, height), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # draw transparent overlay
        vert_pos = 5
        left_pos = 135
        right_pos = width - vert_pos
        title_height = 22
        gap = 3

        draw.rectangle(
            [(left_pos - 20, vert_pos), (right_pos, vert_pos + title_height)],
            fill=(230, 230, 230, 230),
        )  # title box

        content_top = vert_pos + title_height + gap
        content_bottom = 100 - vert_pos

        info_color = (30, 30, 30, 160)

        # draw level circle
        multiplier = 6
        lvl_circle_dia = 94
        circle_left = 15
        circle_top = int((height - lvl_circle_dia) / 2)
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new("L", (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

        # draws mask
        total_gap = 10
        border = int(total_gap / 2)
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier
        # put in profile picture
        output = ImageOps.fit(profile_image, (raw_length, raw_length), centering=(0.5, 0.5))
        output.resize((profile_size, profile_size), Image.ANTIALIAS)
        mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)
        profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
        process.paste(profile_image, (circle_left + border, circle_top + border), mask)

        # put in server picture
        server_size = content_bottom - content_top - 10
        server_border_size = server_size + 4
        radius = 20
        light_border = (150, 150, 150, 180)
        dark_border = (90, 90, 90, 180)
        border_color = self._contrast(info_color, light_border, dark_border)

        draw_server_border = Image.new(
            "RGBA",
            (server_border_size * multiplier, server_border_size * multiplier),
            border_color,
        )
        draw_server_border = self._add_corners(draw_server_border, int(radius * multiplier / 2))
        draw_server_border = draw_server_border.resize(
            (server_border_size, server_border_size), Image.ANTIALIAS
        )
        server_icon_image = server_icon_image.resize(
            (server_size * multiplier, server_size * multiplier), Image.ANTIALIAS
        )
        server_icon_image = self._add_corners(server_icon_image, int(radius * multiplier / 2) - 10)
        server_icon_image = server_icon_image.resize((server_size, server_size), Image.ANTIALIAS)
        process.paste(
            draw_server_border,
            (circle_left + profile_size + 2 * border + 8, content_top + 3),
            draw_server_border,
        )
        process.paste(
            server_icon_image,
            (circle_left + profile_size + 2 * border + 10, content_top + 5),
            server_icon_image,
        )

        def _write_unicode(text, init_x, y, font, unicode_font, fill):
            write_pos = init_x

            for char in text:
                if char.isalnum() or char in string.punctuation or char in string.whitespace:
                    draw.text((write_pos, y), char, font=font, fill=fill)
                    write_pos += font.getsize(char)[0]
                else:
                    draw.text((write_pos, y), "{}".format(char), font=unicode_font, fill=fill)
                    write_pos += unicode_font.getsize(char)[0]

        # draw level box
        level_left = 290
        level_right = right_pos
        draw.rectangle(
            [(level_left, vert_pos), (level_right, vert_pos + title_height)], fill="#AAA"
        )  # box
        lvl_text = "'" + str(time)
        draw.text(
            (self._center(level_left, level_right, lvl_text, level_label_fnt), vert_pos + 3),
            lvl_text,
            font=level_label_fnt,
            fill=(110, 110, 110, 255),
        )  # Level #
        left_text_align = 130
        grey_color = (110, 110, 110, 255)
        # goal text
        _write_unicode(
            maps[event], left_text_align - 12, vert_pos + 3, name_fnt, header_u_fnt, grey_color
        )
        white_text = (240, 240, 240, 255)
        dark_text = (35, 35, 35, 230)
        label_align = 200
        label_text_color = self._contrast(info_color, white_text, dark_text)
        if assister is None:
            draw.text(
                (label_align, 38),
                "Player: {}".format(player.name),
                font=general_info_fnt,
                fill=label_text_color,
            )
            draw.text(
                (label_align, 58),
                "Team: {}".format(teamevent.upper()),
                font=general_info_fnt,
                fill=label_text_color,
            )
            draw.text(
                (label_align, 78),
                "{} {} : {} {}".format(team1.upper()[:3], score1, score2, team2.upper()[:3]),
                font=general_info_fnt,
                fill=label_text_color,
            )
        else:
            draw.text(
                (label_align, 38),
                "Player: {}".format(player.name),
                font=general_info_fnt,
                fill=label_text_color,
            )
            draw.text(
                (label_align, 58),
                "Assisted By: {}".format(assister.name),
                font=general_info_fnt,
                fill=label_text_color,
            )
            draw.text(
                (label_align, 78),
                "Team: {}".format(teamevent.upper()),
                font=general_info_fnt,
                fill=label_text_color,
            )
            draw.text(
                (label_align, 98),
                "{} {} : {} {}".format(team1.upper()[:3], score1, score2, team2.upper()[:3]),
                font=general_info_fnt,
                fill=label_text_color,
            )

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "PNG", quality=100)
        file.seek(0)
        image = discord.File(file, filename="pikaleague.png")
        return image

    def _contrast(self, bg_color, color1, color2):
        color1_ratio = self._contrast_ratio(bg_color, color1)
        color2_ratio = self._contrast_ratio(bg_color, color2)
        if color1_ratio >= color2_ratio:
            return color1
        else:
            return color2

    def _luminance(self, color):
        # convert to greyscale
        luminance = float((0.2126 * color[0]) + (0.7152 * color[1]) + (0.0722 * color[2]))
        return luminance

    def _contrast_ratio(self, bgcolor, foreground):
        f_lum = float(self._luminance(foreground) + 0.05)
        bg_lum = float(self._luminance(bgcolor) + 0.05)

        if bg_lum > f_lum:
            return bg_lum / f_lum
        else:
            return f_lum / bg_lum

    def _add_corners(self, im, rad, multiplier=6):
        raw_length = rad * 2 * multiplier
        circle = Image.new("L", (raw_length, raw_length), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, raw_length, raw_length), fill=255)
        circle = circle.resize((rad * 2, rad * 2), Image.ANTIALIAS)

        alpha = Image.new("L", im.size, 255)
        w, h = im.size
        alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
        alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
        alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
        alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
        im.putalpha(alpha)
        return im

    def _truncate_text(self, text, max_length):
        if len(text) > max_length:
            if text.strip("$").isdigit():
                text = int(text.strip("$"))
                return "${:.2E}".format(text)
            return text[: max_length - 3] + "..."
        return text

    def _center(self, start, end, text, font):
        dist = end - start
        width = font.getsize(text)[0]
        start_pos = start + ((dist - width) / 2)
        return int(start_pos)

    async def timepic(self, ctx, team1, team2, score1, score2, time, logo):
        font_bold_file = f"{bundled_data_path(self)}/LeagueSpartan-Bold.otf"
        name_fnt = ImageFont.truetype(font_bold_file, 20)
        # set canvas
        width = 360
        height = 100
        bg_color = (255, 255, 255, 0)
        logos = {
            "bbc": "https://i.imgur.com/eCPpheL.png",
            "bein": "https://i.imgur.com/VTzMuKv.png",
            "sky": "https://i.imgur.com/sdTk0lW.png",
            "bt": "https://i.imgur.com/RFWiSfK.png",
        }
        scorebg = Image.open(await self.getimg(logos[logo]))
        result = Image.new("RGBA", (width, height), bg_color)
        process = Image.new("RGBA", (width, height), bg_color)
        process.paste(scorebg, (0, 0))
        draw = ImageDraw.Draw(process)
        team1 = team1[:3].upper()
        team2 = team2[:3].upper()
        score = f"{score1} - {score2}"
        draw.text((115, 40), team1, font=name_fnt, fill=(0, 0, 0, 0))
        draw.text((195, 40), score, font=name_fnt, fill=(255, 255, 255, 255))
        draw.text((205, 5), time, font=name_fnt, fill=(255, 255, 255, 255))
        draw.text((295, 40), team2, font=name_fnt, fill=(0, 0, 0, 0))

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "PNG", quality=100)
        file.seek(0)
        image = discord.File(file, filename="score.png")
        return image

    async def penaltyimg(self, ctx, teamevent, time, player):
        font_bold_file = f"{bundled_data_path(self)}/font_bold.ttf"
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        font_unicode_file = f"{bundled_data_path(self)}/unicode.ttf"
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        general_info_fnt = ImageFont.truetype(font_bold_file, 18, encoding="utf-8")
        level_label_fnt = ImageFont.truetype(font_bold_file, 22, encoding="utf-8")
        teams = await self.config.guild(ctx.guild).teams()
        server_icon = await self.getimg(
            teams[teamevent]["logo"]
            if teams[teamevent]["logo"] is not None
            else "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/A_blank_black_picture.jpg/1536px-A_blank_black_picture.jpg"
        )

        server_icon_image = Image.open(server_icon).convert("RGBA")

        # set canvas
        width = 360
        height = 100
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (width, height), bg_color)
        process = Image.new("RGBA", (width, height), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # draw transparent overlay
        vert_pos = 5
        left_pos = 13
        right_pos = width - vert_pos
        title_height = 22
        gap = 3

        draw.rectangle(
            [(left_pos - 20, vert_pos), (right_pos, vert_pos + title_height)],
            fill=(230, 230, 230, 230),
        )  # title box

        content_top = vert_pos + title_height + gap
        content_bottom = 100 - vert_pos

        info_color = (30, 30, 30, 160)

        # draw level circle
        multiplier = 6
        lvl_circle_dia = 94
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new("L", (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

        # draws mask
        total_gap = 10
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier
        # put in profile picture

        # put in server picture
        server_size = content_bottom - content_top - 10
        server_border_size = server_size + 4
        radius = 20
        light_border = (150, 150, 150, 180)
        dark_border = (90, 90, 90, 180)
        border_color = self._contrast(info_color, light_border, dark_border)

        draw_server_border = Image.new(
            "RGBA",
            (server_border_size * multiplier, server_border_size * multiplier),
            border_color,
        )
        draw_server_border = self._add_corners(draw_server_border, int(radius * multiplier / 2))
        draw_server_border = draw_server_border.resize(
            (server_border_size, server_border_size), Image.ANTIALIAS
        )
        server_icon_image = server_icon_image.resize(
            (server_size * multiplier, server_size * multiplier), Image.ANTIALIAS
        )
        server_icon_image = self._add_corners(server_icon_image, int(radius * multiplier / 2) - 10)
        server_icon_image = server_icon_image.resize((server_size, server_size), Image.ANTIALIAS)
        process.paste(draw_server_border, (8, content_top + 3), draw_server_border)
        process.paste(server_icon_image, (10, content_top + 5), server_icon_image)

        def _write_unicode(text, init_x, y, font, unicode_font, fill):
            write_pos = init_x

            for char in text:
                if char.isalnum() or char in string.punctuation or char in string.whitespace:
                    draw.text((write_pos, y), char, font=font, fill=fill)
                    write_pos += font.getsize(char)[0]
                else:
                    draw.text((write_pos, y), "{}".format(char), font=unicode_font, fill=fill)
                    write_pos += unicode_font.getsize(char)[0]

        # draw level box
        level_left = 180
        level_right = right_pos
        draw.rectangle(
            [(level_left, vert_pos), (level_right, vert_pos + title_height)], fill="#AAA"
        )  # box
        lvl_text = "'" + str(time)
        draw.text(
            (self._center(level_left, level_right, lvl_text, level_label_fnt), vert_pos + 3),
            lvl_text,
            font=level_label_fnt,
            fill=(110, 110, 110, 255),
        )  # Level #
        left_text_align = 13
        grey_color = (110, 110, 110, 255)
        # goal text
        _write_unicode(
            "PENALTY!   ({})".format(teamevent[:3].upper()),
            left_text_align - 12,
            vert_pos + 3,
            name_fnt,
            header_u_fnt,
            grey_color,
        )
        white_text = (240, 240, 240, 255)
        dark_text = (35, 35, 35, 230)
        label_align = 70
        label_text_color = self._contrast(info_color, white_text, dark_text)
        draw.text(
            (label_align, 38),
            "Team: {}".format(teamevent.upper()),
            font=general_info_fnt,
            fill=label_text_color,
        )
        draw.text(
            (label_align, 58),
            "{} takes up position to shoot!".format(player),
            font=general_info_fnt,
            fill=label_text_color,
        )

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "PNG", quality=100)
        file.seek(0)
        image = discord.File(file, filename="pikaleague.png")
        return image

    async def extratime(self, ctx, time):
        time = str(time)
        font_bold_file = f"{bundled_data_path(self)}/LeagueSpartan-Bold.otf"
        svn = f"{bundled_data_path(self)}/Seven-Segment.ttf"
        name_fnt = ImageFont.truetype(font_bold_file, 20)
        name_fnt2 = ImageFont.truetype(svn, 160)
        # set canvas
        width = 745
        height = 387
        bg_color = (255, 255, 255, 0)
        scorebg = Image.open(await self.getimg("https://i.imgur.com/k8U1wdt.png"))
        result = Image.new("RGBA", (width, height), bg_color)
        process = Image.new("RGBA", (width, height), bg_color)
        process.paste(scorebg, (0, 0))
        draw = ImageDraw.Draw(process)
        if time != "1":
            draw.text((330, 90), time, font=name_fnt2, fill=(255, 0, 0, 255))
        else:
            draw.text((360, 90), time, font=name_fnt2, fill=(255, 0, 0, 255))
        draw.text((290, 295), f"{time} added minute(s)", font=name_fnt, fill=(255, 255, 255, 255))

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "PNG", quality=100)
        file.seek(0)
        image = discord.File(file, filename="extratime.png")
        return image

    async def motmpic(self, ctx, user, team, goals, assists):
        font_bold_file = f"{bundled_data_path(self)}/font_bold.ttf"
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        font_unicode_file = f"{bundled_data_path(self)}/unicode.ttf"
        general_info_fnt = ImageFont.truetype(font_bold_file, 15, encoding="utf-8")
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        rank_avatar = BytesIO()
        await user.avatar_url.save(rank_avatar, seek_begin=True)
        teams = await self.config.guild(ctx.guild).teams()
        server_icon = await self.getimg(
            teams[team]["logo"]
            if teams[team]["logo"] is not None
            else "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/A_blank_black_picture.jpg/1536px-A_blank_black_picture.jpg"
        )

        profile_image = Image.open(rank_avatar).convert("RGBA")
        server_icon_image = Image.open(server_icon).convert("RGBA")

        # set canvas
        width = 300
        height = 100
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (width, height), bg_color)
        process = Image.new("RGBA", (width, height), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # draw transparent overlay
        vert_pos = 5
        left_pos = 135
        right_pos = width - vert_pos
        title_height = 22
        gap = 3

        draw.rectangle(
            [(left_pos - 20, vert_pos), (right_pos, vert_pos + title_height)],
            fill=(230, 230, 230, 230),
        )  # title box

        content_top = vert_pos + title_height + gap
        content_bottom = 100 - vert_pos

        info_color = (30, 30, 30, 160)

        # draw level circle
        multiplier = 6
        lvl_circle_dia = 94
        circle_left = 15
        circle_top = int((height - lvl_circle_dia) / 2)
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new("L", (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

        # draws mask
        total_gap = 10
        border = int(total_gap / 2)
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier
        # put in profile picture
        output = ImageOps.fit(profile_image, (raw_length, raw_length), centering=(0.5, 0.5))
        output.resize((profile_size, profile_size), Image.ANTIALIAS)
        mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)
        profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
        process.paste(profile_image, (circle_left + border, circle_top + border), mask)

        # put in server picture
        server_size = content_bottom - content_top - 10
        server_border_size = server_size + 4
        radius = 20
        light_border = (150, 150, 150, 180)
        dark_border = (90, 90, 90, 180)
        border_color = self._contrast(info_color, light_border, dark_border)

        draw_server_border = Image.new(
            "RGBA",
            (server_border_size * multiplier, server_border_size * multiplier),
            border_color,
        )
        draw_server_border = self._add_corners(draw_server_border, int(radius * multiplier / 2))
        draw_server_border = draw_server_border.resize(
            (server_border_size, server_border_size), Image.ANTIALIAS
        )
        server_icon_image = server_icon_image.resize(
            (server_size * multiplier, server_size * multiplier), Image.ANTIALIAS
        )
        server_icon_image = self._add_corners(server_icon_image, int(radius * multiplier / 2) - 10)
        server_icon_image = server_icon_image.resize((server_size, server_size), Image.ANTIALIAS)
        process.paste(
            draw_server_border,
            (circle_left + profile_size + 2 * border + 8, content_top + 3),
            draw_server_border,
        )
        process.paste(
            server_icon_image,
            (circle_left + profile_size + 2 * border + 10, content_top + 5),
            server_icon_image,
        )

        def _write_unicode(text, init_x, y, font, unicode_font, fill):
            write_pos = init_x

            for char in text:
                if char.isalnum() or char in string.punctuation or char in string.whitespace:
                    draw.text((write_pos, y), char, font=font, fill=fill)
                    write_pos += font.getsize(char)[0]
                else:
                    draw.text((write_pos, y), "{}".format(char), font=unicode_font, fill=fill)
                    write_pos += unicode_font.getsize(char)[0]

        left_text_align = 130
        grey_color = (110, 110, 110, 255)
        white_text = (240, 240, 240, 255)
        dark_text = (35, 35, 35, 230)
        # goal text
        name = user.name
        if len(name) > 15:
            name = name[:13] + "..."
        _write_unicode(
            "MOTM: {}".format(name),
            left_text_align - 12,
            vert_pos + 3,
            name_fnt,
            header_u_fnt,
            grey_color,
        )
        label_align = 200
        label_text_color = self._contrast(info_color, white_text, dark_text)
        draw.text(
            (label_align, 38),
            "Team: {}".format(team),
            font=general_info_fnt,
            fill=label_text_color,
        )
        draw.text(
            (label_align, 58),
            "Goals: {}".format(goals),
            font=general_info_fnt,
            fill=label_text_color,
        )
        draw.text(
            (label_align, 78),
            "Assists: {}".format(assists),
            font=general_info_fnt,
            fill=label_text_color,
        )

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "PNG", quality=100)
        file.seek(0)
        image = discord.File(file, filename="pikaleague.png")
        return image

    async def walkout(self, ctx, team1, home_or_away):

        font_bold_file = f"{bundled_data_path(self)}/font_bold.ttf"
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        font_unicode_file = f"{bundled_data_path(self)}/unicode.ttf"
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        general_info_fnt = ImageFont.truetype(font_bold_file, 15, encoding="utf-8")
        teams = await self.config.guild(ctx.guild).teams()
        teamplayers = len(teams[team1]["ids"])
        # set canvas
        if teams[team1]["kits"][home_or_away] is None:
            width = 105 * teamplayers
        else:
            width = (105 * teamplayers) + 150
        height = 200
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (width, height), bg_color)
        process = Image.new("RGBA", (width, height), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # draw transparent overlay
        vert_pos = 5
        right_pos = width - vert_pos
        title_height = 22

        draw.rectangle(
            [(0, vert_pos), (right_pos, vert_pos + title_height)], fill=(230, 230, 230, 230)
        )  # title box

        # draw level circle
        multiplier = 6
        lvl_circle_dia = 94
        circle_left = 15
        circle_top = int((height - lvl_circle_dia) / 2)
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new("L", (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

        # draws mask
        total_gap = 10
        border = int(total_gap / 2)
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier
        x = 40
        for player in teams[team1]["ids"]:
            player = await self.bot.fetch_user(player)
            rank_avatar = BytesIO()
            await player.avatar_url.save(rank_avatar, seek_begin=True)
            profile_image = Image.open(rank_avatar).convert("RGBA")
            # put in profile picture
            output = ImageOps.fit(profile_image, (raw_length, raw_length), centering=(0.5, 0.5))
            output.resize((profile_size, profile_size), Image.ANTIALIAS)
            mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)
            profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
            process.paste(profile_image, (circle_left + border, circle_top + border), mask)
            circle_left += 90
            if len(player.name) > 7:
                name = player.name[:6] + "..."
            else:
                name = player.name
            draw.text((x, 160), name, font=general_info_fnt, fill=(255, 255, 255, 255))
            x += 90

        def _write_unicode(text, init_x, y, font, unicode_font, fill):
            write_pos = init_x

            for char in text:
                if char.isalnum() or char in string.punctuation or char in string.whitespace:
                    draw.text((write_pos, y), char, font=font, fill=fill)
                    write_pos += font.getsize(char)[0]
                else:
                    draw.text((write_pos, y), "{}".format(char), font=unicode_font, fill=fill)
                    write_pos += unicode_font.getsize(char)[0]

        grey_color = (110, 110, 110, 255)
        level = teams[team1]["cachedlevel"]
        _write_unicode(
            "Team: {} | Total Level: {} ".format(team1, level),
            10,
            vert_pos + 3,
            name_fnt,
            header_u_fnt,
            grey_color,
        )
        if teams[team1]["kits"][home_or_away] is not None:
            vert_pos = 5
            right_pos = width - vert_pos
            title_height = 22
            gap = 3

            content_top = vert_pos + title_height + gap
            content_bottom = 100 - vert_pos
            info_color = (30, 30, 30, 160)
            server_icon = await self.getimg(teams[team1]["kits"][home_or_away])
            server_icon_image = Image.open(server_icon).convert("RGBA")
            server_size = content_bottom - content_top - 10
            server_border_size = server_size + 4
            radius = 20
            light_border = (150, 150, 150, 180)
            dark_border = (90, 90, 90, 180)
            border_color = self._contrast(info_color, light_border, dark_border)

            draw_server_border = Image.new(
                "RGBA",
                (server_border_size * multiplier, server_border_size * multiplier),
                border_color,
            )
            draw_server_border = self._add_corners(
                draw_server_border, int(radius * multiplier / 2)
            )
            draw_server_border = draw_server_border.resize((140, 140), Image.ANTIALIAS)
            server_icon_image = server_icon_image.resize(
                (server_size * multiplier, server_size * multiplier), Image.ANTIALIAS
            )
            server_icon_image = self._add_corners(
                server_icon_image, int(radius * multiplier / 2) - 10
            )
            server_icon_image = server_icon_image.resize((136, 136), Image.ANTIALIAS)
            process.paste(draw_server_border, (x, 45), draw_server_border)
            process.paste(server_icon_image, (x + 2, 47), server_icon_image)

        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "PNG", quality=100)
        file.seek(0)
        image = discord.File(file, filename="pikaleague.png")
        return image

    async def get(self, url):
        async with self.session.get(url) as response:
            resp = await response.json(content_type=None)
            return resp

    async def getimg(self, img):
        async with self.session.get(img) as response:
            buffer = BytesIO(await response.read())
            buffer.name = "picture.png"
            return buffer

    async def addrole(self, ctx, user, rolename):
        role_obj = discord.utils.get(ctx.guild.roles, name=rolename)
        if role_obj is not None:
            member = ctx.guild.get_member(user)
            if member is not None:
                try:
                    await member.add_roles(role_obj)
                except discord.Forbidden:
                    print("Failed to remove role from {}".format(member.name))

    async def matchnotif(self, ctx, team1, team2):
        teams = await self.config.guild(ctx.guild).teams()
        teamone = teams[team1]["ids"]
        teamtwo = teams[team2]["ids"]
        role1 = False
        role2 = False
        msg = ""
        if teams[team1]["role"]:
            role_obj = discord.utils.get(ctx.guild.roles, name=str(teams[team1]["role"]))
            if role_obj is not None:
                await role_obj.edit(mentionable=True)
                msg += role_obj.mention
                role1 = True
                roleone = role_obj
                mem1 = []
                for memberid in teamone:
                    member = ctx.guild.get_member(memberid)
                    if member is not None:
                        notif = await self.config.user(member).notify()
                        if role_obj in member.roles:
                            try:
                                if not notif:
                                    await member.remove_roles(role_obj)
                                    mem1.append(member.id)
                            except discord.Forbidden:
                                print("Failed to remove role from {}".format(member.name))
        else:
            msg += team1
        msg += " VS "
        if teams[team2]["role"]:
            role_obj = discord.utils.get(ctx.guild.roles, name=str(teams[team2]["role"]))
            if role_obj is not None:
                await role_obj.edit(mentionable=True)
                msg += role_obj.mention
                role2 = True
                roletwo = role_obj
                mem2 = []
                for memberid in teamtwo:
                    member = ctx.guild.get_member(memberid)
                    if member is not None:
                        notif = await self.config.user(member).notify()
                        if role_obj in member.roles:
                            try:
                                if not notif:
                                    await member.remove_roles(role_obj)
                                    mem2.append(member.id)
                            except discord.Forbidden:
                                print("Failed to remove role from {}".format(member.name))
        else:
            msg += team2
        await ctx.send(msg)
        if role1:
            await roleone.edit(mentionable=False)
            if mem1:
                for memberid in mem1:
                    member = ctx.guild.get_member(memberid)
                    if member is not None:
                        try:
                            await member.add_roles(roleone)
                        except discord.Forbidden:
                            print("Failed to remove role from {}".format(member.name))
        if role2:
            await roletwo.edit(mentionable=False)
            if mem2:
                for memberid in mem2:
                    member = ctx.guild.get_member(memberid)
                    if member is not None:
                        try:
                            await member.add_roles(roletwo)
                        except discord.Forbidden:
                            print("Failed to remove role from {}".format(member.name))

    async def postresults(self, ctx, team1, team2, score1, score2):
        results = await self.config.guild(ctx.guild).resultchannel()
        role1 = False
        role2 = False
        if results:
            result = ""
            teams = await self.config.guild(ctx.guild).teams()
            teamone = teams[team1]["ids"]
            teamtwo = teams[team2]["ids"]
            if teams[team1]["role"]:
                role_obj = discord.utils.get(ctx.guild.roles, name=str(teams[team1]["role"]))
                if role_obj is not None:
                    await role_obj.edit(mentionable=True)
                    result += role_obj.mention
                    role1 = True
                    roleone = role_obj
                    mem1 = []
                    for memberid in teamone:
                        member = ctx.guild.get_member(memberid)
                        if member is not None:
                            notif = await self.config.user(member).notify()
                            if role_obj in member.roles:
                                try:
                                    if not notif:
                                        await member.remove_roles(role_obj)
                                        mem1.append(member.id)
                                except discord.Forbidden:
                                    print("Failed to remove role from {}".format(member.name))
            else:
                result += team1
            result += f" {score1}:{score2} "
            if teams[team2]["role"]:
                role_obj = discord.utils.get(ctx.guild.roles, name=str(teams[team2]["role"]))
                if role_obj is not None:
                    await role_obj.edit(mentionable=True)
                    result += role_obj.mention
                    role2 = True
                    roletwo = role_obj
                    mem2 = []
                    for memberid in teamtwo:
                        member = ctx.guild.get_member(memberid)
                        if member is not None:
                            notif = await self.config.user(member).notify()
                            if role_obj in member.roles:
                                try:
                                    if not notif:
                                        await member.remove_roles(role_obj)
                                        mem2.append(member.id)
                                except discord.Forbidden:
                                    print("Failed to remove role from {}".format(member.name))
            else:
                result += team2
            for channel in results:
                channel = self.bot.get_channel(channel)
                await channel.send(result)
            if role1:
                role_obj = discord.utils.get(ctx.guild.roles, name=teams[team1]["role"])
                if role_obj is not None:
                    await role_obj.edit(mentionable=False)
                    if mem1:
                        for memberid in mem1:
                            member = ctx.guild.get_member(memberid)
                            if member is not None:
                                try:
                                    await member.add_roles(roleone)
                                except discord.Forbidden:
                                    print("Failed to remove role from {}".format(member.name))

            if role2:
                role_obj = discord.utils.get(ctx.guild.roles, name=teams[team2]["role"])
                if role_obj is not None:
                    await role_obj.edit(mentionable=False)
                    if mem2:
                        for memberid in mem2:
                            member = ctx.guild.get_member(memberid)
                            if member is not None:
                                try:
                                    await member.add_roles(roletwo)
                                except discord.Forbidden:
                                    print("Failed to remove role from {}".format(member.name))

    async def yCardChance(self, guild, probability):
        rdmint = random.randint(0, 100)
        if rdmint > probability["yellowchance"]:  # 98 default
            return True

    async def rCardChance(self, guild, probability):
        rdmint = random.randint(0, 300)
        if rdmint > probability["redchance"]:  # 299 default
            return True

    async def goalChance(self, guild, probability):
        rdmint = random.randint(0, 100)
        if rdmint > probability["goalchance"]:  # 96 default
            return True

    async def penaltyChance(self, guild, probability):
        rdmint = random.randint(0, 250)
        if rdmint > probability["penaltychance"]:  # 249 probability
            return True

    async def penaltyBlock(self, guild, probability):
        rdmint = random.randint(0, 1)
        if rdmint > probability["penaltyblock"]:  # 0.6 default
            return True

    async def update(self, guild):
        a = {}
        pageamount = await self.config.guild(guild).pageamount()
        for i in range(pageamount):
            data = await self.get(
                f"https://mee6.xyz/api/plugins/levels/leaderboard/{guild.id}??page={i}&?limit=999"
            )
            for player in data["players"]:
                a[player["id"]] = str(player["level"])
        await self.config.guild(guild).levels.set(a)

    async def updatecacheall(self, guild):
        print("Updating CACHE.")
        mee6 = await self.config.guild(guild).mee6()
        async with self.config.guild(guild).teams() as teams:
            for team in teams:
                t1totalxp = 0
                teams[team]
                team1pl = teams[team]["ids"]

                if mee6:
                    xp = await self.config.guild(guild).levels()
                    for memberid in team1pl:
                        try:
                            t1totalxp += int(xp[str(memberid)])
                        except KeyError:
                            t1totalxp += 1
                    teams[team]["cachedlevel"] = t1totalxp
                else:
                    for memberid in team1pl:
                        user = await self.bot.fetch_user(memberid)
                        try:
                            userinfo = db.users.find_one({"user_id": str(user.id)})
                            level = userinfo["servers"][str(guild.id)]["level"]
                            t1totalxp += int(level)
                        except (KeyError, TypeError):
                            t1totalxp += 1
                    teams[team]["cachedlevel"] = t1totalxp

    async def updatecachegame(self, guild, team1, team2):
        t1totalxp = 0
        t2totalxp = 0
        mee6 = await self.config.guild(guild).mee6()
        async with self.config.guild(guild).teams() as teams:
            team1pl = teams[team1]["ids"]
            if mee6:
                xp = await self.config.guild(guild).levels()
                for memberid in team1pl:
                    try:
                        t1totalxp += int(xp[str(memberid)])
                    except KeyError:
                        t1totalxp += 1
                teams[team1]["cachedlevel"] = t1totalxp
                team2pl = teams[team2]["ids"]
                for memberid in team2pl:
                    try:
                        t2totalxp += int(xp[str(memberid)])
                    except KeyError:
                        t2totalxp += 1
                teams[team2]["cachedlevel"] = t2totalxp
            else:
                for memberid in team1pl:
                    user = await self.bot.fetch_user(memberid)
                    try:
                        userinfo = db.users.find_one({"user_id": str(user.id)})
                        level = userinfo["servers"][str(guild.id)]["level"]
                        t1totalxp += int(level)
                    except (KeyError, TypeError):
                        t1totalxp += 1
                teams[team1]["cachedlevel"] = t1totalxp

                team2pl = teams[team2]["ids"]
                for memberid in team2pl:
                    user = await self.bot.fetch_user(memberid)
                    try:
                        userinfo = db.users.find_one({"user_id": str(user.id)})
                        level = userinfo["servers"][str(guild.id)]["level"]
                        t2totalxp += int(level)
                    except (KeyError, TypeError):
                        t2totalxp += 1
                teams[team2]["cachedlevel"] = t2totalxp

    async def transfer(
        self, ctx, guild, team1, member1: discord.Member, team2, member2: discord.Member
    ):
        async with self.config.guild(guild).teams() as teams:
            if member1.id not in teams[team1]["ids"]:
                return await ctx.send(f"{member1.name} is not on {team1}.")
            if member2.id not in teams[team2]["ids"]:
                return await ctx.send(f"{member2.name} is not on {team2}.")
            if member1.id in list(teams[team1]["captain"].values()):
                teams[team1]["captain"] = {}
                teams[team1]["captain"][member2.name] = member2.id
            if member2.id in list(teams[team2]["captain"].values()):
                teams[team2]["captain"] = {}
                teams[team2]["captain"][member1.name] = member1.id
            teams[team1]["members"][member2.name] = member2.id
            del teams[team1]["members"][member1.name]
            teams[team2]["members"][member1.name] = member1.id
            del teams[team2]["members"][member2.name]
            teams[team1]["ids"].remove(member1.id)
            teams[team2]["ids"].remove(member2.id)
            teams[team1]["ids"].append(member2.id)
            teams[team2]["ids"].append(member1.id)

    async def sign(self, ctx, guild, team1, member1: discord.Member, member2: discord.Member):
        users = await self.config.guild(guild).users()
        if member2.id in users:
            return await ctx.send("User is currently not a free agent.")
        async with self.config.guild(guild).teams() as teams:
            if member1.id not in teams[team1]["ids"]:
                return await ctx.send(f"{member1.name} is not on {team1}.")
            if member1.name in list(teams[team1]["captain"].values()):
                teams[team1]["captain"] = {}
                teams[team1]["captain"] = {member2.name: member2.id}
            teams[team1]["members"][member2.name] = member2.id
            del teams[team1]["members"][member1.name]
            teams[team1]["ids"].remove(member1.id)
            teams[team1]["ids"].append(member2.id)
        async with self.config.guild(guild).users() as users:
            users.remove(member1.id)

    @checks.admin()
    @teamset.command(name="transfer")
    async def _transfer(self, ctx, team1, player1: discord.Member, team2, player2: discord.Member):
        """Transfer two players."""
        await self.transfer(ctx, ctx.guild, team1, player1, team2, player2)
        await ctx.tick()

    @checks.admin()
    @teamset.command(name="sign")
    async def _sign(self, ctx, team1, player1: discord.Member, player2: discord.Member):
        """Release a player and sign a free agent."""
        await self.sign(ctx, ctx.guild, team1, player1, player2)
        await ctx.tick()

    async def team_delete(self, ctx, team):
        async with self.config.guild(ctx.guild).teams() as teams:
            if team not in teams:
                return await ctx.send("Team was not found, ensure capitilization is correct.")
            async with self.config.guild(ctx.guild).users() as users:
                for uid in teams[team]["ids"]:
                    users.remove(uid)
            del teams[team]
            async with self.config.guild(ctx.guild).standings() as standings:
                del standings[team]
            return await ctx.send("Team successfully removed.")

    @checks.admin()
    @teamset.command(name="delete")
    async def _delete(self, ctx, *, team):
        """Delete a team."""
        await self.team_delete(ctx, team)
