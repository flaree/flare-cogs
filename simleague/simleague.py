import asyncio
import logging
import random
import time
from abc import ABC
from typing import Literal, Optional

import aiohttp
import discord
from redbot.core import Config, bank, checks, commands
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from tabulate import tabulate

from .core import SimHelper
from .functions import WEATHER
from .simset import SimsetMixin
from .stats import StatsMixin
from .teamset import TeamsetMixin

# THANKS TO https://code.sololearn.com/ci42wd5h0UQX/#py FOR THE SIMULATION AND FIXATOR/AIKATERNA/STEVY FOR THE PILLOW HELP/LEVELER


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """This allows the metaclass used for proper type detection to coexist with discord.py's
    metaclass."""


class SimLeague(
    SimHelper, TeamsetMixin, StatsMixin, SimsetMixin, commands.Cog, metaclass=CompositeMetaClass
):
    """SimLeague"""

    __version__ = "3.1.0"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.log = logging.getLogger("red.flarecogs.SimLeague")
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
                "cleansheets": {},
            },
            "users": [],
            "resultchannel": [],
            "gametime": 1,
            "bettime": 180,
            "htbreak": 5,
            "bettoggle": True,
            "betmax": 10000,
            "betmin": 10,
            "mentions": True,
            "redcardmodifier": 22,
            "probability": {
                "goalchance": 96,
                "yellowchance": 98,
                "redchance": 398,
                "penaltychance": 249,
                "penaltyblock": 0.6,
            },
            "maxplayers": 4,
            "active": False,
            "started": False,
            "betteams": [],
            "transferwindow": False,
            "cupmode": False,
        }
        defaults_user = {"notify": True}
        self.config = Config.get_conf(self, identifier=4268355870, force_registration=True)
        self.config.register_guild(**defaults)
        self.config.register_user(**defaults_user)
        self.bot = bot
        self.bets = {}
        self.cache = time.time()
        self.session = aiohttp.ClientSession()

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):

        await self.config.user_from_id(user_id).clear()

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

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command()
    async def register(
        self,
        ctx,
        teamname: str,
        members: commands.Greedy[discord.Member],
        logo: Optional[str] = None,
        *,
        role: discord.Role = None,
    ):
        """Register a team.
        Try keep team names to one word if possible."""
        maxplayers = await self.config.guild(ctx.guild).maxplayers()
        if len(members) != maxplayers:
            return await ctx.send(f"You must provide {maxplayers} members.")

        names = {str(x.id): x.name for x in members}
        a = []
        memids = await self.config.guild(ctx.guild).users()
        for uid in names:
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

        async with self.config.guild(ctx.guild).teams() as teams:
            if teamname in teams:
                return await ctx.send("{} is already a team!".format(teamname))
            a = []
            teams[teamname] = {
                "members": names,
                "captain": {str(members[0].id): members[0].name},
                "logo": logo,
                "role": role.name if role is not None else None,
                "cachedlevel": 0,
                "fullname": None,
                "kits": {"home": None, "away": None, "third": None},
                "stadium": None,
                "bonus": 0,
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
        await self.config.guild(ctx.guild).users.set(memids + list(names.keys()))
        for uid in list(names.keys()):
            await self.addrole(ctx, uid, role)
        await ctx.tick()

    @commands.command(name="teams")
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
                    mems = [x for x in teams[team]["members"].values()]
                    lvl = teams[team]["cachedlevel"]
                    embed.add_field(
                        name="Team {}".format(team),
                        value="{}**Members**:\n{}\n**Captain**: {}\n**Team Level**: ~{}{}{}".format(
                            "**Full Name**:\n{}\n".format(teams[team]["fullname"])
                            if teams[team]["fullname"] is not None
                            else "",
                            "\n".join(mems),
                            list(teams[team]["captain"].values())[0],
                            lvl,
                            "\n**Role**: {}".format(
                                ctx.guild.get_role(teams[team]["role"]).mention
                            )
                            if teams[team]["role"] is not None
                            else "",
                            "\n**Stadium**: {}".format(teams[team]["stadium"])
                            if teams[team]["stadium"] is not None
                            else "",
                        ),
                        inline=True,
                    )
            await msg.edit(embed=embed, content=None)
        else:
            teamlen = max(*[len(str(i)) for i in teams], 5) + 3
            rolelen = max(*[len(str(teams[i]["role"])) for i in teams], 5) + 3
            caplen = max(*[len(list(teams[i]["captain"].values())[0]) for i in teams], 5) + 3
            lvllen = 6

            msg = f"{'Team':{teamlen}} {'Level':{lvllen}} {'Captain':{caplen}} {'Role':{rolelen}} {'Members'}\n"
            for team in teams:
                lvl = teams[team]["cachedlevel"]
                captain = list(teams[team]["captain"].values())[0]
                role = teams[team]["role"]
                non = "None"
                msg += (
                    f"{f'{team}': <{teamlen}} "
                    f"{f'{lvl}': <{lvllen}} "
                    f"{f'{captain}': <{caplen}} "
                    f"{f'{role.name if role is not None else non}': <{rolelen}}"
                    f"{', '.join(list(teams[team]['members'].values()))} \n"
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
            embed.add_field(
                name="Members:",
                value="\n".join(list(teams[team]["members"].values())),
                inline=True,
            )
            embed.add_field(name="Captain:", value=list(teams[team]["captain"].values())[0])
            embed.add_field(name="Level:", value=teams[team]["cachedlevel"], inline=True)
            embed.add_field(name="Bonus %:", value=f"{teams[team]['bonus'] * 15}%", inline=True)
            if teams[team]["role"] is not None:
                embed.add_field(
                    name="Role:",
                    value=ctx.guild.get_role(teams[team]["role"]).mention,
                    inline=True,
                )
            if teams[team]["stadium"] is not None:
                embed.add_field(name="Stadium:", value=teams[team]["stadium"], inline=True)
            if teams[team]["logo"] is not None:
                embed.set_thumbnail(url=teams[team]["logo"])
            embeds.append(embed)
            for kit in teams[team]["kits"]:
                if teams[team]["kits"][kit] is not None:
                    embed = discord.Embed(title=f"{kit.title()} Kit", colour=ctx.author.colour)
                    embed.set_image(url=teams[team]["kits"][kit])
                    embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command()
    async def fixtures(self, ctx, week: Optional[int] = None):
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
            if week == 0:
                return await ctx.send("Try starting with week 1.")
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
        if await self.config.guild(ctx.guild).cupmode():
            return await ctx.send(
                "This simulation league is in cup mode, contact the maintainer of the league for the current standings."
            )
        standings = await self.config.guild(ctx.guild).standings()
        if standings is None:
            return await ctx.send("The table is empty.")
        if not verbose:
            t = []  # PrettyTable(["Team", "W", "L", "D", "PL", "PO"])
            for x in sorted(
                standings,
                key=lambda x: (standings[x]["points"], standings[x]["gd"], standings[x]["gf"]),
                reverse=True,
            ):
                t.append(
                    [
                        x,
                        standings[x]["wins"],
                        standings[x]["losses"],
                        standings[x]["draws"],
                        standings[x]["played"],
                        standings[x]["points"],
                    ]
                )
            tab = tabulate(t, headers=["Team", "Wins", "Losses", "Draws", "Played", "Points"])
            await ctx.send(box(tab))
        else:
            t = []
            for x in sorted(
                standings,
                key=lambda x: (standings[x]["points"], standings[x]["gd"], standings[x]["gf"]),
                reverse=True,
            ):
                t.append(
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
            tab = tabulate(
                t,
                headers=["Team", "Wins", "Losses", "Draws", "Played", "Points", "GD", "GF", "GA"],
            )
            await ctx.send(box(tab))

    @checks.admin_or_permissions(manage_guild=True)
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.guild)
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @commands.command(aliases=["playsim", "simulate"])
    async def sim(self, ctx, team1: str, team2: str):
        """Simulate a game between two teams."""
        teams = await self.config.guild(ctx.guild).teams()
        if team1 not in teams or team2 not in teams:
            return await ctx.send("One of those teams do not exist.")
        if team1 == team2:
            return await ctx.send("You can't sim two of the same teams silly.")
        msg = await ctx.send("Updating cached levels...")
        await self.updatecachegame(ctx.guild, team1, team2)
        await msg.delete()
        await asyncio.sleep(2)
        teams = await self.config.guild(ctx.guild).teams()
        lvl1 = teams[team1]["cachedlevel"]
        lvl2 = teams[team2]["cachedlevel"]
        bonuslvl1 = teams[team1]["bonus"]
        bonuslvl2 = teams[team2]["bonus"]
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
        stadium = teams[team1]["stadium"] if teams[team1]["stadium"] is not None else None

        weather = random.choice(WEATHER)
        im = await self.matchinfo(ctx, [team1, team2], weather, stadium, homewin, awaywin, draw)
        await ctx.send(file=im)

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
        redcardmodifier = await self.config.guild(ctx.guild).redcardmodifier()
        team1players = list(teams[team1]["members"].keys())
        team2players = list(teams[team2]["members"].keys())
        logos = ["sky", "bt", "bein", "bbc"]
        yellowcards = []
        logo = random.choice(logos)
        motm = {}
        events = False

        # Team 1 stuff
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

        # Team 2 stuff
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

        async def TeamWeightChance(
            ctx, t1totalxp, t2totalxp, reds1: int, reds2: int, team1bonus: int, team2bonus: int
        ):
            if t1totalxp < 2:
                t1totalxp = 1
            if t2totalxp < 2:
                t2totalxp = 1
            team1bonus = team1bonus * 15
            team2bonus = team2bonus * 15
            t1totalxp = t1totalxp * float(f"1.{team1bonus}")
            t2totalxp = t2totalxp * float(f"1.{team2bonus}")
            self.log.debug(f"Team 1: {t1totalxp} - Team 2: {t2totalxp}")
            redst1 = float(f"0.{reds1 * redcardmodifier}")
            redst2 = float(f"0.{reds2 * redcardmodifier}")
            total = ["A"] * int(((1 - redst1) * 100) * t1totalxp) + ["B"] * int(
                ((1 - redst2) * 100) * t2totalxp
            )
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
                if len(rosterUpdate) == 1:
                    return None
                player = random.choice(rosterUpdate)
                if player in yc or player in yellowcards:
                    output = [team, player, 2]
                    return output
                else:
                    output = [team, player]
                    return output
            elif event == 2 or event == 3:
                rosterUpdate = [i for i in fs_players if i not in rc]
                if len(rosterUpdate) == 1 and event == 2:
                    return None
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
                    teamStats = await TeamWeightChance(
                        ctx, lvl1, lvl2, reds[team1], reds[team2], bonuslvl1, bonuslvl2
                    )
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
                    if len(playerGoal) == 3:
                        user2 = self.bot.get_user(int(playerGoal[2]))
                        if user2 is None:
                            user2 = await self.bot.fetch_user(int(playerGoal[2]))
                        if user2 not in motm:
                            motm[user2] = 1
                        else:
                            motm[user2] += 1
                        if user2.id not in assists:
                            assists[user2.id] = 1
                        else:
                            assists[user2.id] += 1
                    user = self.bot.get_user(int(playerGoal[1]))
                    if user is None:
                        user = await self.bot.fetch_user(int(playerGoal[1]))
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
                    teamStats = await TeamWeightChance(
                        ctx, lvl1, lvl2, reds[team1], reds[team2], bonuslvl1, bonuslvl2
                    )
                    playerPenalty = await PlayerGenerator(
                        3, teamStats[0], teamStats[1], teamStats[2]
                    )
                    user = self.bot.get_user(int(playerPenalty[1]))
                    if user is None:
                        user = await self.bot.fetch_user(int(playerPenalty[1]))
                    image = await self.penaltyimg(ctx, str(playerPenalty[0]), str(min), user)
                    await ctx.send(file=image)
                    pB = await self.penaltyBlock(ctx.guild, probability)
                    if pB is True:
                        events = True
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerPenalty[1] not in stats["penalties"]:
                                stats["penalties"][playerPenalty[1]] = {"scored": 0, "missed": 1}
                            else:
                                stats["penalties"][playerPenalty[1]]["missed"] += 1
                        user = self.bot.get_user(int(playerPenalty[1]))
                        if user is None:
                            user = await self.bot.fetch_user(int(playerPenalty[1]))
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
                        user = self.bot.get_user(int(playerPenalty[1]))
                        if user is None:
                            user = await self.bot.fetch_user(int(playerPenalty[1]))
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
                    if playerYellow is not None:
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
                            user = self.bot.get_user(int(playerYellow[1]))
                            if user is None:
                                user = await self.bot.fetch_user(int(playerYellow[1]))
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
                                    len(teams[str(str(playerYellow[0]))]["members"])
                                    - (int(teamStats[7]))
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
                            user = self.bot.get_user(int(playerYellow[1]))
                            if user is None:
                                user = await self.bot.fetch_user(int(playerYellow[1]))
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
                    if playerRed is not None:
                        teamStats[7] += 1
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerRed[1] not in stats["reds"]:
                                stats["reds"][playerRed[1]] = 1
                            else:
                                stats["reds"][playerRed[1]] += 1
                        reds[str(playerRed[0])] += 1
                        teamStats[2].append(playerRed[1])
                        events = True
                        user = self.bot.get_user(int(playerRed[1]))
                        if user is None:
                            user = await self.bot.fetch_user(int(playerRed[1]))
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
                            str(
                                len(teams[str(str(playerRed[0]))]["members"]) - (int(teamStats[7]))
                            ),
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
                            ctx, lvl1, lvl2, reds[team1], reds[team2], bonuslvl1, bonuslvl2
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
                            user2 = self.bot.get_user(int(playerGoal[2]))
                            if user2 is None:
                                user2 = await self.bot.fetch_user(int(playerGoal[2]))
                            if user2 not in motm:
                                motm[user2] = 1
                            else:
                                motm[user2] += 1
                            if user2.id not in assists:
                                assists[user2.id] = 1
                            else:
                                assists[user2.id] += 1
                        events = True
                        user = self.bot.get_user(int(playerGoal[1]))
                        if user is None:
                            user = await self.bot.fetch_user(int(playerGoal[1]))
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
                            ctx, lvl1, lvl2, reds[team1], reds[team2], bonuslvl1, bonuslvl2
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
                            user2 = self.bot.get_user(int(playerGoal[2]))
                            if user2 is None:
                                user2 = await self.bot.fetch_user(int(playerGoal[2]))
                            if user2 not in motm:
                                motm[user2] = 1
                            else:
                                motm[user2] += 1
                            if user2.id not in assists:
                                assists[user2.id] = 1
                            else:
                                assists[user2.id] += 1
                        events = True
                        user = self.bot.get_user(int(playerGoal[1]))
                        if user is None:
                            user = await self.bot.fetch_user(int(playerGoal[1]))
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
                await self.cleansheets(ctx, team1, team2, team1Stats[8], team2Stats[8])
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
        if ctx.guild.id in self.bets:
            self.bets[ctx.guild.id] = {}
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
                    self.bot.get_user(motmwinner.id), (75 * motmgoals) + (30 * motmassists)
                )
            except AttributeError:
                pass
            im = await self.motmpic(
                ctx,
                motmwinner,
                team1 if str(motmwinner.id) in teams[team1]["members"].keys() else team2,
                motmgoals,
                motmassists,
            )
            async with self.config.guild(ctx.guild).stats() as stats:
                if str(motmwinner.id) not in stats["motm"]:
                    stats["motm"][str(motmwinner.id)] = 1
                else:
                    stats["motm"][str(motmwinner.id)] += 1
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
        if ctx.guild.id not in self.bets:
            self.bets[ctx.guild.id] = {}
        elif ctx.author.id in self.bets[ctx.guild.id]:
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
            self.bets[ctx.guild.id][ctx.author] = {"Bets": [(team, bet)]}
            currency = await bank.get_currency_name(ctx.guild)
            await bank.withdraw_credits(ctx.author, bet)
            await ctx.send(f"{ctx.author.mention} placed a {bet} {currency} bet on {str(team)}.")

    async def payout(self, guild, winner, odds):
        if winner is None:
            return None
        bet_winners = []
        if guild.id not in self.bets:
            return None
        for better in self.bets[guild.id]:
            for team, bet in self.bets[guild.id][better]["Bets"]:
                if team == winner:
                    bet_winners.append(f"{better.mention} - Winnings: {int(bet + (bet * odds))}")
                    await bank.deposit_credits(better, int(bet + (bet * odds)))
        return "\n".join(bet_winners) if bet_winners else None

    async def cleansheets(self, ctx, team1, team2, team1score, team2score):
        if team1score == 0 and team2score > 0:
            async with self.config.guild(ctx.guild).stats() as stats:
                if team2 in stats["cleansheets"]:
                    stats["cleansheets"][team2] += 1
                else:
                    stats["cleansheets"][team2] = 1
        elif team2score == 0 and team1score > 0:
            async with self.config.guild(ctx.guild).stats() as stats:
                if team2 in stats["cleansheets"]:
                    stats["cleansheets"][team1] += 1
                else:
                    stats["cleansheets"][team1] = 1
