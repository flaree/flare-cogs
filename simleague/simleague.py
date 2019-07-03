import asyncio
import random
import string
from io import BytesIO
from typing import Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps
from prettytable import PrettyTable
from pymongo import MongoClient
from redbot.core import Config, bank, checks, commands
from redbot.core.data_manager import bundled_data_path, cog_data_path
from redbot.core.utils.chat_formatting import box

client = MongoClient()
db = client["leveler"]

# THANKS TO https://code.sololearn.com/ci42wd5h0UQX/#py FOR THE SIMULATION AND FIXATOR/AIKATERNA/STEVY FOR THE PILLOW HELP/LEVELER


class SimLeague(commands.Cog):

    __version__ = "2.1.2"

    def __init__(self, bot):
        defaults = {
            "levels": {},
            "teams": {},
            "fixtures": [],
            "standings": {},
            "stats": {"goals": {}, "yellows": {}, "reds": {}, "penalties": {}, "assists": {}},
            "users": [],
            "resultchannel": [],
            "gametime": 1,
            "bettime": 90,
            "htbreak": 5,
            "bettoggle": True,
            "betmax": 10000,
            "betmin": 10,
        }
        defaults_user = {"notify": True}
        self.config = Config.get_conf(self, identifier=4268355870, force_registration=True)
        self.config.register_guild(**defaults)
        self.config.register_user(**defaults_user)
        self.bot = bot
        self.active = False
        self.started = False
        self.teams = []
        self.bets = {}
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

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
            msg = ""
            msg += "Game Time: 1m for every {}s.\n".format(gametime)
            msg += "HT Break: {}s.\n".format(htbreak)
            msg += "Posting Results: {}.\n".format("Yes" if results else "No")
            msg += "Accepting Bets: {}.\n".format("Yes" if bettoggle else "No")
            if bettoggle:
                bettime = await self.config.guild(guild).bettime()
                betmax = await self.config.guild(guild).betmax()
                betmin = await self.config.guild(guild).betmin()
                msg += "Bet Time: {}s.\n".format(bettime)
                msg += "Max Bet: {}.\n".format(betmax)
                msg += "Min Bedt: {}.\n".format(betmin)
            await ctx.send(box(msg))

    @checks.admin()
    @simset.group(autohelp=True)
    async def bet(self, ctx):
        """Simulation Betting Settings."""
        pass

    @checks.admin()
    @commands.group(autohelp=True)
    async def stats(self, ctx):
        """Sim League Statistics."""
        pass

    @checks.admin()
    @bet.command()
    async def bettime(self, ctx, time: int = 90):
        """Set the time allowed for betting - 120 seconds is the max."""
        if time < 0 or time > 120:
            time = 90
        await self.config.guild(ctx.guild).bettime.set(time)
        await ctx.tick()

    @checks.admin()
    @bet.command()
    async def betmax(self, ctx, amount: int):
        """Set the max amount for betting."""
        if amount > 0:
            return await ctx.send("Amount must be greater than 0.")
        await self.config.guild(ctx.guild).betmax.set(amount)
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
    async def halftimetime(self, ctx, time: int = 1):
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
        """Register a team."""
        if len(members) != 4:
            return await ctx.send("You must provide 4 members.")
        # await self.update()
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
    async def _list(self, ctx):
        """List current teams."""
        teams = await self.config.guild(ctx.guild).teams()
        if not teams:
            return await ctx.send("No teams have been registered.")
        embed = discord.Embed(colour=ctx.author.colour)
        for team in teams:
            mems = [x for x in teams[team]["members"].keys()]
            lvl = await self.teamlevel(ctx, team)
            embed.add_field(
                name=f"Team {team}",
                value=f"Members: {', '.join(mems)}\nCaptain: {list(teams[team]['captain'].keys())[0]}\nTeam Level: {lvl}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command()
    async def team(self, ctx, *, team: str):
        """List a team."""
        teams = await self.config.guild(ctx.guild).teams()
        if not teams:
            return await ctx.send("No teams have been registered.")
        if team not in teams:
            return await ctx.send("Team does not exist, ensure that it is correctly capitilized.")
        im = await self.walkout(ctx, team)
        await ctx.send(file=im)

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
    async def fixture(self, ctx, week: int):
        """Show fixtures for a game week."""
        fixtures = await self.config.guild(ctx.guild).fixtures()
        if not fixtures:
            return await ctx.send("No fixtures have been made.")
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
    async def fixtures(self, ctx):
        """Show all fixtures."""
        fixtures = await self.config.guild(ctx.guild).fixtures()
        if not fixtures:
            return await ctx.send("No fixtures have been made.")
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

    @checks.admin()
    @simset.command()
    async def clear(self, ctx):
        """Clear the current table/teams."""
        await self.config.guild(ctx.guild).clear()
        await self.config.guild(ctx.guild).standings.set({})
        await ctx.tick()

    @stats.command(alies=["topscorer", "topscorers"])
    async def goals(self, ctx):
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

    @stats.command()
    async def penalties(self, ctx):
        """Penalties scored and missed statistics."""
        stats = await self.config.guild(ctx.guild).stats()
        stats = stats["penalties"]
        if stats:
            a = []
            b = []
            for k in sorted(stats, key=lambda x: stats[x]["scored"], reverse=True):
                a.append(f"{k} - {stats[k]}")
            for k in sorted(stats, key=lambda x: stats[x]["missed"], reverse=True):
                b.append(f"{k} - {stats[k]}")
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

    # @checks.mod()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.guild)
    @commands.command(aliases=["sim"])
    async def playsim(self, ctx, team1: str, team2: str):
        """Manually sim a game."""
        uff = False
        if ctx.guild.id == 410031796105773057:
            uff = True

        teams = await self.config.guild(ctx.guild).teams()
        if team1 not in teams or team2 not in teams:
            return await ctx.send("One of those teams do not exist.")
        if uff:
            msg = await ctx.send("Updating levels. Please wait...")
            await self.update(ctx.guild)
            await msg.delete()
        self.active = True
        self.teams = [team1, team2]
        bettime = await self.config.guild(ctx.guild).bettime()
        bet = await ctx.send(
            "Betting is now open, game will commence in {} seconds.\nUsage: {}bet <amount> <team>".format(
                bettime, ctx.prefix
            )
        )
        await asyncio.sleep(bettime)
        await bet.delete()
        self.started = True
        team1players = list(teams[team1]["members"].keys())
        team2players = list(teams[team2]["members"].keys())
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

        async def TeamWeightChance(ctx):
            xp = await self.config.guild(ctx.guild).levels()
            team1pl = teams[team1]["ids"]
            team2pl = teams[team2]["ids"]
            t1totalxp = 0
            t2totalxp = 0
            if ctx.guild.id == 410031796105773057:
                for memberid in team1pl:
                    member = self.bot.get_user(memberid)
                    if member is None:
                        member = await self.bot.fetch_user(memberid)
                    try:
                        t1totalxp += int(xp[member.name])
                    except KeyError:
                        t1totalxp += 1
                for memberid in team2pl:
                    member = self.bot.get_user(memberid)
                    if member is None:
                        member = await self.bot.fetch_user(memberid)
                    try:
                        t2totalxp += int(xp[member.name])
                    except KeyError:
                        t2totalxp += 1

            else:
                for memberid in team1pl:
                    user = self.bot.get_user(memberid)
                    if user is None:
                        user = await self.bot.fetch_user(memberid)
                    try:
                        userinfo = db.users.find_one({"user_id": str(user.id)})
                        level = userinfo["servers"][str(ctx.guild.id)]["level"]
                        t1totalxp += int(level)
                    except (KeyError, TypeError):
                        t1totalxp += 1
                for memberid in team2pl:
                    user = self.bot.get_user(memberid)
                    if user is None:
                        user = await self.bot.fetch_user(memberid)
                    try:
                        userinfo = db.users.find_one({"user_id": str(user.id)})
                        level = userinfo["servers"][str(ctx.guild.id)]["level"]
                        t2totalxp += int(level)
                    except (KeyError, TypeError):
                        t2totalxp += 1
            total = ["A"] * (t1totalxp) + ["B"] * (t2totalxp)
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

        def PlayerGenerator(event, team, yc, rc, injury, sub_in, sub_out):
            random.shuffle(team1players)
            random.shuffle(team2players)
            output = []
            if team == team1:
                fs_players = team1players
                yc = yC_team1
                rc = rC_team1
                injury = injury_team1
                sub_in = sub_in_team1
                sub_out = sub_out_team1
            elif team == team2:
                fs_players = team2players
                yc = yC_team2
                rc = rC_team2
                injury = injury_team2
                sub_in = sub_in_team2
                sub_out = sub_out_team2
            if event == 0:
                rosterUpdate = [i for i in fs_players if i not in rc]
                for i in sub_in:
                    rosterUpdate.append(i)
                isassist = False
                assist = random.randint(0, 100)
                playernum = random.randint(0, len(rosterUpdate) - 1)
                if assist > 20:
                    isassist = True
                    assisternum = random.randint(0, len(rosterUpdate) - 2)
                if isassist:
                    player = rosterUpdate[playernum]
                    rosterUpdate.pop(playernum)
                    assister = rosterUpdate[assisternum]
                    output = [team, player, assister]
                else:
                    player = rosterUpdate[random.randint(0, len(rosterUpdate) - 1)]
                    output = [team, player]
                return output
            elif event == 1:
                rosterUpdate = [i for i in fs_players if i not in rc]
                for i in sub_in:
                    rosterUpdate.append(i)
                player = rosterUpdate[random.randint(0, len(rosterUpdate) - 1)]
                if player[:] in yc:
                    output = [team, player, 2]
                    return output
                else:
                    player = rosterUpdate[random.randint(0, len(rosterUpdate) - 1)]
                    output = [team, player]
                    return output
            elif event == 2 or event == 3:
                rosterUpdate = [i for i in fs_players if i not in rc]
                for i in sub_in:
                    rosterUpdate.append(i)
                player_out = rosterUpdate[random.randint(0, len(rosterUpdate) - 1)]
                output = [team, player_out]
                return output

        # Start of Simulation!
        await self.matchnotif(ctx, team1, team2)
        im = await self.walkout(ctx, team1)
        im2 = await self.walkout(ctx, team2)
        await ctx.send("Teams:", file=im)
        await ctx.send(file=im2)
        await asyncio.sleep(10)
        timemsg = await ctx.send("Kickoff!")
        gametime = await self.config.guild(ctx.guild).gametime()
        for min in range(1, 91):
            await asyncio.sleep(gametime)
            if min % 5 == 0:
                await timemsg.edit(content="Minute: {}".format(min))
            if events == False:
                gC = self.goalChance()
                if gC == True:
                    teamStats = await TeamWeightChance(ctx)
                    playerGoal = PlayerGenerator(
                        0,
                        teamStats[0],
                        teamStats[1],
                        teamStats[2],
                        teamStats[3],
                        teamStats[4],
                        teamStats[5],
                    )
                    teamStats[8] += 1
                    async with self.config.guild(ctx.guild).stats() as stats:
                        if playerGoal[1] not in stats["goals"]:
                            stats["goals"][playerGoal[1]] = 1
                        else:
                            stats["goals"][playerGoal[1]] += 1
                        if len(playerGoal) == 3:
                            if playerGoal[1] not in stats["assists"]:
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
                    user = self.bot.get_user(uid)
                    if user is None:
                        user = await self.bot.fetch_user(uid)
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
            if events == False:
                pC = self.penaltyChance()
                if pC == True:
                    teamStats = await TeamWeightChance(ctx)
                    playerPenalty = PlayerGenerator(
                        3,
                        teamStats[0],
                        teamStats[1],
                        teamStats[2],
                        teamStats[3],
                        teamStats[4],
                        teamStats[5],
                    )
                    image = await self.penaltyimg(
                        ctx, str(playerPenalty[0]), str(min), playerPenalty[1]
                    )
                    await ctx.send(file=image)
                    pB = self.penaltyBlock()
                    if pB == True:
                        events = True
                        uid = teams[str(playerPenalty[0])]["members"][playerPenalty[1]]
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerPenalty[0] not in stats["penalties"]:
                                stats["penalties"][playerPenalty[0]]["missed"] = 1
                            else:
                                stats["penalties"][playerPenalty[0]]["missed"] += 1
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
                            if playerPenalty[0] not in stats["goals"]:
                                stats["goals"][playerPenalty[0]] = 1
                            else:
                                stats["goals"][playerPenalty[0]] += 1
                            if playerPenalty[0] not in stats["penalties"]:
                                stats["penalties"][playerPenalty[0]]["scored"] = 1
                            else:
                                stats["penalties"][playerPenalty[0]]["scored"] += 1
                        events = True
                        uid = teams[str(playerPenalty[0])]["members"][playerPenalty[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
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
            if events == False:
                yC = self.yCardChance()
                if yC == True:
                    teamStats = await TeamChance()
                    playerYellow = PlayerGenerator(
                        1,
                        teamStats[0],
                        teamStats[1],
                        teamStats[2],
                        teamStats[3],
                        teamStats[4],
                        teamStats[5],
                    )
                    if len(playerYellow) == 3:
                        teamStats[7] += 1
                        teamStats[2].append(playerYellow[1])
                        async with self.config.guild(ctx.guild).stats() as stats:
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
                            str(4 - (int(teamStats[7]))),
                        )
                        await ctx.send(file=image)
                    else:

                        teamStats[1].append(playerYellow[1])
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
            if events == False:
                rC = self.rCardChance()
                if rC == True:
                    teamStats = await TeamChance()
                    playerRed = PlayerGenerator(
                        2,
                        teamStats[0],
                        teamStats[1],
                        teamStats[2],
                        teamStats[3],
                        teamStats[4],
                        teamStats[5],
                    )
                    teamStats[7] += 1
                    async with self.config.guild(ctx.guild).stats() as stats:
                        if playerRed[1] not in stats["reds"]:
                            stats["reds"][playerRed[1]] = 1
                        else:
                            stats["reds"][playerRed[1]] += 1
                    teamStats[2].append(playerRed[1])
                    events = True
                    uid = teams[str(playerRed[0])]["members"][playerRed[1]]
                    user = self.bot.get_user(uid)
                    if user is None:
                        user = await self.bot.fetch_user(uid)
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
                        str(4 - (int(teamStats[7]))),
                    )
                    await ctx.send(file=image)
            if events == False:
                pass
            events = False
            if min == 45:
                added = random.randint(1, 5)
                im = await self.extratime(ctx, added)
                await ctx.send(file=im)
                s = 45
                for i in range(added):
                    s += 1
                    gC = self.goalChance()
                    if gC == True:
                        teamStats = await TeamWeightChance(ctx)
                        playerGoal = PlayerGenerator(
                            0,
                            teamStats[0],
                            teamStats[1],
                            teamStats[2],
                            teamStats[3],
                            teamStats[4],
                            teamStats[5],
                        )
                        teamStats[8] += 1
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerGoal[1] not in stats["goals"]:
                                stats["goals"][playerGoal[1]] = 1
                            else:
                                stats["goals"][playerGoal[1]] += 1
                            if len(playerGoal) == 3:
                                if playerGoal[1] not in stats["assists"]:
                                    stats["assists"][playerGoal[2]] = 1
                                else:
                                    stats["assists"][playerGoal[2]] += 1
                        if len(playerGoal) == 3:
                            assister = teams[str(playerGoal[0])]["members"][playerGoal[2]]
                            user2 = self.bot.get_user(assister)
                            if user2 is None:
                                user2 = await self.bot.fetch_user(uid)
                        events = True
                        uid = teams[str(playerGoal[0])]["members"][playerGoal[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
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

                    events = False
                    ht = await self.config.guild(ctx.guild).htbreak()
                im = await self.timepic(
                    ctx, team1, team2, str(team1Stats[8]), str(team2Stats[8]), "HT"
                )
                await ctx.send(file=im)
                await asyncio.sleep(ht)

            if min == 90:
                added = random.randint(1, 5)
                im = await self.extratime(ctx, added)
                await ctx.send(file=im)
                s = 90
                for i in range(added):
                    s += 1
                    gC = self.goalChance()
                    if gC == True:
                        teamStats = await TeamWeightChance(ctx)
                        playerGoal = PlayerGenerator(
                            0,
                            teamStats[0],
                            teamStats[1],
                            teamStats[2],
                            teamStats[3],
                            teamStats[4],
                            teamStats[5],
                        )
                        teamStats[8] += 1
                        async with self.config.guild(ctx.guild).stats() as stats:
                            if playerGoal[1] not in stats["goals"]:
                                stats["goals"][playerGoal[1]] = 1
                            else:
                                stats["goals"][playerGoal[1]] += 1
                            if len(playerGoal) == 3:
                                if playerGoal[1] not in stats["assists"]:
                                    stats["assists"][playerGoal[2]] = 1
                                else:
                                    stats["assists"][playerGoal[2]] += 1
                        if len(playerGoal) == 3:
                            assister = teams[str(playerGoal[0])]["members"][playerGoal[2]]
                            user2 = self.bot.get_user(assister)
                            if user2 is None:
                                user2 = await self.bot.fetch_user(uid)
                        events = True
                        uid = teams[str(playerGoal[0])]["members"][playerGoal[1]]
                        user = self.bot.get_user(uid)
                        if user is None:
                            user = await self.bot.fetch_user(uid)
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
                    await asyncio.sleep(2)
                    events = False
                im = await self.timepic(
                    ctx, team1, team2, str(team1Stats[8]), str(team2Stats[8]), "FT"
                )
                await timemsg.edit(content="Match Concluded")
                await ctx.send(file=im)
                if team1Stats[8] > team2Stats[8]:
                    async with self.config.guild(ctx.guild).standings() as standings:
                        standings[team1]["wins"] += 1
                        standings[team1]["points"] += 3
                        standings[team1]["played"] += 1
                        standings[team2]["losses"] += 1
                        standings[team2]["played"] += 1
                        t = await self.payout(ctx.guild, team1)
                if team1Stats[8] < team2Stats[8]:
                    async with self.config.guild(ctx.guild).standings() as standings:
                        standings[team2]["points"] += 3
                        standings[team2]["wins"] += 1
                        standings[team2]["played"] += 1
                        standings[team1]["losses"] += 1
                        standings[team1]["played"] += 1
                        t = await self.payout(ctx.guild, team2)
                if team1Stats[8] == team2Stats[8]:
                    async with self.config.guild(ctx.guild).standings() as standings:
                        standings[team1]["played"] += 1
                        standings[team2]["played"] += 1
                        standings[team1]["points"] += 1
                        standings[team2]["points"] += 1
                        standings[team2]["draws"] += 1
                        standings[team1]["draws"] += 1
                        t = await self.payout(ctx.guild, None)
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
        self.active = False
        self.started = False
        self.bets = {}
        if t is not None:
            await ctx.send("Bet Winners:\n" + t)

    async def bet_conditions(self, ctx, bet, team):
        bettoggle = await self.config.guild(ctx.guild).bettoggle()
        if not bettoggle:
            return await ctx.send("Betting is currently disabled.")
        if not self.active:
            await ctx.send("There isn't a game onright now.")
            return False
        elif self.started:
            await ctx.author.send("You can't place a bet after the game has started.")
            return False
        elif ctx.author in self.bets:
            await ctx.send("You have already entered a bet for the game.")
            return False

        minbet = await self.config.guild(ctx.guild).betmin()
        if bet < minbet:
            await ctx.send("The minimum bet is {}".format(minbet))
            return False
        maxbet = await self.config.guild(ctx.guild).betmax()
        if bet > maxbet:
            await ctx.send("The maximum bet is {}".format(minbet))
            return False

        if not await bank.can_spend(ctx.author, bet):
            await ctx.send("You do not have enough money to cover the bet.")
            return False
        else:
            return True

    @commands.command(name="bet")
    async def _bet(self, ctx, bet: int, team: str):
        """Bet on a team."""
        if await self.bet_conditions(ctx, bet, team):
            self.bets[ctx.author] = {"Bets": [(team, bet)]}
            currency = await bank.get_currency_name(ctx.guild)
            await bank.withdraw_credits(ctx.author, bet)
            await ctx.send(f"{ctx.author.mention} placed a {bet} {currency} bet on {str(team)}.")

    async def payout(self, guild, winner):
        if winner is None:
            return None
        bet_winners = []
        for better in self.bets:
            for team, bet in self.bets[better]["Bets"]:
                if team == winner:
                    bet_winners.append(f"{better.mention} - Winnings: {bet * 2}")
                    await bank.deposit_credits(better, bet * 2)
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
                "{} {} : {} {}".format(team1.upper(), score1, score2, team2.upper()),
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
                "{} {} : {} {}".format(team1.upper(), score1, score2, team2.upper()),
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

    async def timepic(self, ctx, team1, team2, score1, score2, time):
        font_bold_file = f"{bundled_data_path(self)}/LeagueSpartan-Bold.otf"
        name_fnt = ImageFont.truetype(font_bold_file, 20)
        # set canvas
        width = 360
        height = 100
        bg_color = (255, 255, 255, 0)
        scorebg = Image.open(await self.getimg("https://i.imgur.com/eCPpheL.png"))
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

    async def walkout(self, ctx, team1):

        font_bold_file = f"{bundled_data_path(self)}/font_bold.ttf"
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        font_unicode_file = f"{bundled_data_path(self)}/unicode.ttf"
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        general_info_fnt = ImageFont.truetype(font_bold_file, 15, encoding="utf-8")
        teams = await self.config.guild(ctx.guild).teams()

        # set canvas
        width = 420
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
            draw.text((x, 160), player.name, font=general_info_fnt, fill=(255, 255, 255, 255))
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
        level = await self.teamlevel(ctx, team1)
        if ctx.guild.id == 410031796105773057:
            _write_unicode(
                "Team: {} | Captain: {} | Total Level: {} ".format(
                    team1, list(teams[team1]["captain"].keys())[0], level
                ),
                10,
                vert_pos + 3,
                name_fnt,
                header_u_fnt,
                grey_color,
            )
        else:
            _write_unicode(
                "Team: {} | Captain: {} | Total Level: {} ".format(
                    team1, list(teams[team1]["captain"].keys())[0], level
                ),
                10,
                vert_pos + 3,
                name_fnt,
                header_u_fnt,
                grey_color,
            )
        result = Image.alpha_composite(result, process)
        file = BytesIO()
        result.save(file, "PNG", quality=100)
        file.seek(0)
        image = discord.File(file, filename="pikaleague.png")
        return image

    async def teamlevel(self, ctx, team):
        t1totalxp = 0
        teams = await self.config.guild(ctx.guild).teams()
        team1pl = teams[team]["ids"]
        if ctx.guild.id == 410031796105773057:
            xp = await self.config.guild(ctx.guild).levels()
            for memberid in team1pl:
                member = await self.bot.fetch_user(memberid)
                try:
                    t1totalxp += int(xp[member.name])
                except KeyError:
                    t1totalxp += 1
            return t1totalxp
        else:
            for memberid in team1pl:
                user = await self.bot.fetch_user(memberid)
                try:
                    userinfo = db.users.find_one({"user_id": str(user.id)})
                    level = userinfo["servers"][str(ctx.guild.id)]["level"]
                    t1totalxp += int(level)
                except (KeyError, TypeError):
                    t1totalxp += 1
            return t1totalxp

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

    def yCardChance(self):
        rdmint = random.randint(0, 100)
        if rdmint > 98:
            return True

    def rCardChance(self):
        rdmint = random.randint(0, 300)
        if rdmint > 299:
            return True

    def goalChance(self):
        rdmint = random.randint(0, 100)
        if rdmint > 96:
            return True

    def penaltyChance(self):
        rdmint = random.randint(0, 250)
        if rdmint > 249:
            return True

    def penaltyBlock(self):
        rdmint = random.randint(0, 1)
        if rdmint > 0.6:
            return True

    async def update(self, guild):
        data = await self.get(
            "https://mee6.xyz/api/plugins/levels/leaderboard/410031796105773057??page=0&?limit=999"
        )
        data1 = await self.get(
            "https://mee6.xyz/api/plugins/levels/leaderboard/410031796105773057?page=1&?limit=999"
        )
        data2 = await self.get(
            "https://mee6.xyz/api/plugins/levels/leaderboard/410031796105773057?page=2&?limit=999"
        )
        data3 = await self.get(
            "https://mee6.xyz/api/plugins/levels/leaderboard/410031796105773057?page=3&?limit=999"
        )
        data4 = await self.get(
            "https://mee6.xyz/api/plugins/levels/leaderboard/410031796105773057?page=4&?limit=999"
        )
        a = {}
        for player in data["players"]:
            a[player["username"]] = str(player["level"])
        for player in data1["players"]:
            a[player["username"]] = str(player["level"])
        for player in data2["players"]:
            a[player["username"]] = str(player["level"])
        for player in data3["players"]:
            a[player["username"]] = str(player["level"])
        for player in data4["players"]:
            a[player["username"]] = str(player["level"])
        await self.config.guild(guild).levels.set(a)
