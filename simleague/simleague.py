from redbot.core import commands, Config, checks
import discord
import aiohttp
import asyncio
import random
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from tabulate import tabulate
from prettytable import PrettyTable
# THANKS TO https://code.sololearn.com/ci42wd5h0UQX/#py FOR THE SIMULATION

class SimLeague(commands.Cog):

    __version__ = "0.2.0"

    def __init__(self, bot):
        defaults = {
            "levels": {},
            "teams": {},
            "fixtures": [],
            "standings": {},
            "week": 0,
            "stats": {"goals": {}, "yellows": {}, "reds": {}},
        }
        self.config = Config.get_conf(self, identifier=4268355870, force_registration=True)
        self.config.register_global(**defaults)
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.week = 0

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def get(self, url):
        async with self.session.get(url) as response:
            resp = await response.json(content_type=None)
            return resp

    async def update(self):
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
        a = {}
        for player in data["players"]:
            a[player["username"]] = str(player["level"])
        for player in data1["players"]:
            a[player["username"]] = str(player["level"])
        for player in data2["players"]:
            a[player["username"]] = str(player["level"])
        for player in data3["players"]:
            a[player["username"]] = str(player["level"])
        await self.config.levels.set(a)

    @checks.mod()
    @commands.command()
    async def register(self, ctx, teamname: str, members: commands.Greedy[discord.Member]):
        """Register a team"""
        if len(members) > 5:
            return await ctx.send("You have provided to many members.")
        if len(members) < 3:
            return await ctx.send("You must provide atleast 3 members.")
        await self.update()
        names = [x.name for x in members]
        ids = [x.id for x in members]
        async with self.config.teams() as teams:
            a = []
            for team in teams:
                for member in names:
                    if member in teams[team]["members"]:
                        a.append(member)
            if a:
                return await ctx.send(a)
            teams[teamname] = {"members": names, "ids": ids}
        async with self.config.standings() as standings:
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
        await ctx.tick()

    @commands.command(name="teams", aliases=["list"])
    async def _list(self, ctx):
        """List current teams"""
        teams = await self.config.teams()
        embed = discord.Embed()
        for i, team in enumerate(teams):
            embed.add_field(
                name=f"Team {i}",
                value=f"Team: {team}\nMembers: {', '.join(teams[team]['members'])}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @checks.mod()
    @commands.command()
    async def createfixtures(self, ctx):
        """Create the fixtures for the current teams."""
        teams = await self.config.teams()
        teams = list(teams.keys())
        if len(teams) % 2:
            teams.append("Day off")
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
        await self.config.fixtures.set(fixtures)
        await ctx.tick()

    @commands.command()
    async def fixture(self, ctx, week: int):
        """Show fixtures for a game week."""
        fixtures = await self.config.fixtures()
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
        fixtures = await self.config.fixtures()
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
        """Current sim standings"""
        standings = await self.config.standings()
        if not verbose:
            t = PrettyTable(["Team", "Wins", "Losses", "Played", "Points"])
            for x in sorted(standings, key=lambda x: standings[x]["points"], reverse=True), 1:
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
            for x in sorted(standings, key=lambda x: standings[x]["points"], reverse=True), 1:
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

    @checks.mod()
    @commands.command()
    async def clear(self, ctx):
        """Clear the current table/teams"""
        await self.config.clear()
        await self.config.week.set(0)
        await ctx.tick()

    @commands.command()
    async def week(self, ctx):
        """Return the current gameweek"""
        week = await self.config.week()
        await ctx.send(f"We are currently on week {week + 1}. Check the fixtures using .fixtures")

    @checks.mod()
    @commands.command()
    async def reset(self, ctx):
        """Reset the gameweek to 0"""
        await self.config.week.set(0)
        await ctx.tick()

    @commands.command()
    async def topscorer(self, ctx):
        """Top scorers."""
        stats = await self.config.stats()
        stats = stats["goals"]
        if stats:
            a = []
            for k in sorted(stats, key=lambda x: stats[x], reverse=True):
                a.append(f"{k} - {stats[k]}")
            await ctx.send("\n".join(a[:10]))
        else:
            await ctx.send("No stats available.")

    @commands.command()
    async def yellowcards(self, ctx):
        """Players with the most yellow cards."""
        stats = await self.config.stats()
        stats = stats["yellows"]
        if stats:
            a = []
            for k in sorted(stats, key=lambda x: stats[x], reverse=True):
                a.append(f"{k} - {stats[k]}")
            await ctx.send("\n".join(a[:10]))
        else:
            await ctx.send("No stats available.")

    @commands.command()
    async def redcards(self, ctx):
        """Players with the most red cards."""
        stats = await self.config.stats()
        stats = stats["reds"]
        if stats:
            a = []
            for k in sorted(stats, key=lambda x: stats[x], reverse=True):
                a.append(f"{k} - {stats[k]}")
            await ctx.send("\n".join(a[:10]))
        else:
            await ctx.send("No stats available.")

    @checks.mod()
    @commands.command()
    async def simall(self, ctx):
        """Play the current weeks simulated games."""
        msg = await ctx.send("Updating levels. Please wait...")
        await self.update()
        await msg.delete()
        goals = {}
        yellows = {}
        reds = {}
        fixtures = await self.config.fixtures()
        if not fixtures:
            return await ctx.send("Please use .createfixtures to generate the fixtures.")
        week = await self.config.week()
        if week > len(fixtures) - 1:
            return await ctx.send(
                "You have finished the league, to continue please call a mod to reset the table"
            )
        fixture = fixtures[week]
        await ctx.send("Week {} Games:".format(week + 1))
        for fixt in fixture:
            b = []
            teams = await self.config.teams()
            team1 = fixt[0]
            team2 = fixt[1]
            if team1 == "Day off" or team2 == "Day off":
                continue
            team1players = teams[team1]["members"]
            team2players = teams[team2]["members"]
            events = False
            Event = [
                "Goal!",
                "Yellow Card,",
                "Red Card!",
                "Penalty!",
                "Injury!",
                "Score:",
                "Substitution",
            ]

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

            # If you want to increase the odds of a particular event happening, simply change the number after the greater than sign in the following functions below. Increasing the number will decrease the odds of an event occuring and vice versa.

            async def TeamChance():
                xp = await self.config.levels()
                team1pl = teams[team1]["ids"]
                team2pl = teams[team2]["ids"]
                t1totalxp = 0
                t2totalxp = 0
                for memberid in team1pl:
                    member = self.bot.get_user(memberid)
                    try:
                        t1totalxp += int(xp[member.name])
                    except KeyError:
                        t1totalxp += 1
                for memberid in team2pl:
                    member = self.bot.get_user(memberid)
                    try:
                        t2totalxp += int(xp[member.name])
                    except KeyError:
                        t2totalxp += 1
                total = ["A"] * (t1totalxp) + ["B"] * (t2totalxp)
                rdmint = random.choice(total)
                if rdmint == "A":
                    return team1Stats
                else:
                    return team2Stats

            def yCardChance():
                rdmint = random.randint(0, 100)
                if rdmint > 98:
                    return True

            def rCardChance():
                rdmint = random.randint(0, 300)
                if rdmint > 299:
                    return True

            def goalChance():
                rdmint = random.randint(0, 100)
                if rdmint > 96:
                    return True

            def penaltyChance():
                rdmint = random.randint(0, 250)
                if rdmint > 249:
                    return True

            def penaltyBlock():
                rdmint = random.randint(0, 1)
                if rdmint > 0.6:
                    return True

            # Add your own player roster by replacing the names in the lists below:

            def PlayerGenerator(event, team, yc, rc, injury, sub_in, sub_out):
                random.shuffle(team1players)
                random.shuffle(team2players)
                arsenalFirstsquad = team1players
                chelseaFirstsquad = team2players
                output = []
                if team == team1:
                    fs_players = arsenalFirstsquad
                    yc = yC_team1
                    rc = rC_team1
                    injury = injury_team1
                    sub_in = sub_in_team1
                    sub_out = sub_out_team1
                elif team == team2:
                    fs_players = chelseaFirstsquad
                    yc = yC_team2
                    rc = rC_team2
                    injury = injury_team2
                    sub_in = sub_in_team2
                    sub_out = sub_out_team2
                if event == 0:
                    rosterUpdate = [i for i in fs_players if i not in rc]
                    for i in sub_in:
                        rosterUpdate.append(i)
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
            b.append(team1 + " vs " + team2)
            b.append(team1 + ": " + ", ".join(team1players))
            b.append(team2 + ": " + ", ".join(team2players))
            b.append("\n**Match Start**!\n")
            await ctx.send("```" + "\n".join(b) + "```")
            b = []
            await asyncio.sleep(2)
            for min in range(1, 91):
                if events == False:
                    gC = goalChance()
                    if gC == True:
                        b = []
                        teamStats = await TeamChance()
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
                        b.append(
                            ""
                            + Event[5]
                            + " "
                            + team1.upper()
                            + " "
                            + str(team1Stats[8])
                            + " : "
                            + str(team2Stats[8])
                            + " "
                            + team2.upper()
                        )
                        b.append(
                            "\N{STOPWATCH} "
                            + str(min)
                            + " min: "
                            + "\N{SOCCER BALL} GOAALLL! ("
                            + str(playerGoal[0])
                            + " "
                            + str(Event[0])
                            + ") \n\N{HEAVY EXCLAMATION MARK SYMBOL} "
                            + str(playerGoal[1]).upper()
                            + " HAS SCORED!"
                        )
                        if playerGoal[1] not in goals:
                            goals[playerGoal[1]] = 1
                        else:
                            goals[playerGoal[1]] += 1
                        events = True
                        await ctx.send("```\n" + "\n".join(b) + "```")
                        await asyncio.sleep(2)
                if events == False:
                    pC = penaltyChance()
                    if pC == True:
                        teamStats = await TeamChance()
                        playerPenalty = PlayerGenerator(
                            3,
                            teamStats[0],
                            teamStats[1],
                            teamStats[2],
                            teamStats[3],
                            teamStats[4],
                            teamStats[5],
                        )
                        b = []
                        b.append(
                            "\N{STOPWATCH} "
                            + str(min)
                            + " IN: \n"
                            + str(playerPenalty[0])
                            + " "
                            + str(Event[3])
                        )
                        b.append("" + str(playerPenalty[1]) + " steps up to shoot...")
                        pB = penaltyBlock()
                        if pB == True:
                            b.append("SHOT BLOCKED!!")
                            events = True
                        else:
                            teamStats[8] += 1
                            b.append(
                                "\u200b\N{SOCCER BALL} GOAALLL!\n\N{HEAVY EXCLAMATION MARK SYMBOL}"
                                + str(playerPenalty[0]).upper()
                                + " HAS SCORED!"
                            )
                            b.append(
                                ""
                                + Event[5]
                                + " "
                                + team1.upper()
                                + " "
                                + str(team1Stats[8])
                                + " : "
                                + str(team2Stats[8])
                                + " "
                                + team2.upper()
                            )
                            if playerPenalty[0] not in goals:
                                goals[playerPenalty[0]] = 1
                            else:
                                goals[playerPenalty[0]] += 1
                            events = True
                        await ctx.send("```\n" + "\n".join(b) + "```")
                        await asyncio.sleep(2)
                if events == False:
                    yC = yCardChance()
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
                        b = []
                        if len(playerYellow) == 3:
                            teamStats[7] += 1
                            b.append(
                                "\N{STOPWATCH} "
                                + str(min)
                                + " min: "
                                + str(playerYellow[0])
                                + " "
                                + str(Event[1])
                                + " "
                                + str(playerYellow[1])
                                + "\n"
                                + str(playerYellow[1])
                                + "'s Second Yellow! Red Card!"
                                + "\n         "
                                + str(playerYellow[0])
                                + " are down to "
                                + str(5 - (int(teamStats[7])))
                                + " men!"
                            )
                            if playerYellow[1] not in reds:
                                reds[playerYellow[1]] = 1
                                yellows[playerYellow[1]] += 1
                            else:
                                yellows[playerYellow[1]] += 1
                                reds[playerYellow[1]] += 1
                            teamStats[2].append(playerYellow[1])
                            events = True
                        else:
                            b.append(
                                "\N{STOPWATCH} "
                                + str(min)
                                + " min: "
                                + str(playerYellow[0])
                                + " "
                                + str(Event[1])
                                + " "
                                + str(playerYellow[1])
                            )
                            if playerYellow[1] not in yellows:
                                yellows[playerYellow[1]] = 1
                            else:
                                yellows[playerYellow[1]] += 1
                            teamStats[1].append(playerYellow[1])
                            events = True
                        await ctx.send("```\n" + "\n".join(b) + "```")
                        await asyncio.sleep(2)
                if events == False:
                    rC = rCardChance()
                    if rC == True:
                        b = []
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
                        b.append(
                            "\N{STOPWATCH} "
                            + str(min)
                            + " min: "
                            + str(playerRed[0])
                            + " "
                            + str(Event[2])
                            + " "
                            + str(playerRed[1])
                            + "\n"
                            + str(playerRed[0])
                            + " are down to "
                            + str(5 - (int(teamStats[7])))
                            + " men!"
                        )
                        if playerRed[1] not in reds:
                            reds[playerRed[1]] = 1
                        else:
                            reds[playerRed[1]] += 1
                        teamStats[2].append(playerRed[1])
                        events = True
                        await ctx.send("```\n" + "\n".join(b) + "```")
                        await asyncio.sleep(2)
                if events == False:
                    pass
                events = False
                if min == 45:
                    b = []
                    added = random.randint(1, 5)
                    b.append(str(added) + " Minute(s) of Stoppage Time")
                    s = 45
                    for i in range(added):
                        s += 1
                        gC = goalChance()
                        if gC == True:
                            teamStats = await TeamChance()
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
                            b.append(
                                "\N{STOPWATCH} "
                                + str(s)
                                + " min in stoppage time: \N{SOCCER BALL} GOAALLL! ("
                                + str(playerGoal[0])
                                + " "
                                + str(Event[0])
                                + ")\n\N{HEAVY EXCLAMATION MARK SYMBOL} "
                                + str(playerGoal[1]).upper()
                                + " HAS SCORED!"
                            )
                            b.append(
                                "        "
                                + Event[5]
                                + " "
                                + team1.upper()
                                + " "
                                + str(team1Stats[8])
                                + " : "
                                + str(team2Stats[8])
                                + " "
                                + team2.upper()
                            )
                            if playerGoal[1] not in goals:
                                goals[playerGoal[1]] = 1
                            else:
                                goals[playerGoal[1]] += 1
                            events = True
                        events = False
                    await ctx.send("```\n" + "\n".join(b) + "```")
                    await asyncio.sleep(2)
                    await ctx.send("```css\n[HALF TIME]\n```")
                    await asyncio.sleep(2)

                if min == 90:
                    b = []
                    added = random.randint(1, 5)
                    b.append(str(added) + " Minute(s) of Stoppage Time")
                    s = 90
                    for i in range(added):
                        s += 1
                        gC = goalChance()
                        if gC == True:
                            teamStats = await TeamChance()
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
                            b.append(
                                "\N{STOPWATCH} "
                                + str(s)
                                + " min in stoppage time: \N{SOCCER BALL} GOAALLL! ("
                                + str(playerGoal[0])
                                + " "
                                + str(Event[0])
                                + ")\n\N{HEAVY EXCLAMATION MARK SYMBOL} "
                                + str(playerGoal[1]).upper()
                                + " HAS SCORED!"
                            )
                            b.append(
                                ""
                                + Event[5]
                                + " "
                                + team1.upper()
                                + " "
                                + str(team1Stats[8])
                                + " : "
                                + str(team2Stats[8])
                                + " "
                                + team2.upper()
                            )
                            if playerGoal[1] not in goals:
                                goals[playerGoal[1]] = 1
                            else:
                                goals[playerGoal[1]] += 1
                            events = True
                        events = False
                    await ctx.send("```\n" + "\n".join(b) + "```")
                    b = []
                    b.append("\n[FULL TIME]\n")
                    await ctx.send("```css\n" + "\n".join(b) + "```")
                    await asyncio.sleep(5)
                    await ctx.send(
                        "Final Score: "
                        + team1.upper()
                        + " "
                        + str(team1Stats[8])
                        + " : "
                        + str(team2Stats[8])
                        + " "
                        + team2.upper()
                    )
                    if team1Stats[8] > team2Stats[8]:
                        async with self.config.standings() as standings:
                            standings[team1]["wins"] += 1
                            standings[team1]["points"] += 3
                            standings[team1]["played"] += 1
                            standings[team2]["losses"] += 1
                            standings[team2]["played"] += 1
                    if team1Stats[8] < team2Stats[8]:
                        async with self.config.standings() as standings:
                            standings[team2]["points"] += 3
                            standings[team2]["wins"] += 1
                            standings[team2]["played"] += 1
                            standings[team1]["losses"] += 1
                            standings[team1]["played"] += 1
                    if team1Stats[8] == team2Stats[8]:
                        async with self.config.standings() as standings:
                            standings[team1]["played"] += 1
                            standings[team2]["played"] += 1
                            standings[team1]["points"] += 1
                            standings[team2]["points"] += 1
                            standings[team2]["draws"] += 1
                            standings[team1]["draws"] += 1
                    team1gd = team1Stats[8] - team2Stats[8]
                    team2gd = team2Stats[8] - team1Stats[8]
                    async with self.config.standings() as standings:
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
                    if len(fixtures) > 1:
                        await asyncio.sleep(10)

        async with self.config.stats() as stats:
            for goal in goals:
                stats["goals"][goal] = goals[goal]
            for red in reds:
                stats["reds"][red] = reds[red]
            for yellowc in yellows:
                stats["yellows"][yellowc] = yellows[yellowc]
        week += 1
        await self.config.week.set(week)

    @checks.mod()
    @commands.command()
    async def playsim(self, ctx, team1: str, team2: str):
        """Manually sim a game."""
        b = []
        teams = await self.config.teams()
        goals = {}
        yellows = {}
        reds = {}
        team1players = teams[team1]["members"]
        team2players = teams[team2]["members"]
        events = False
        Event = [
            "Goal!",
            "Yellow Card,",
            "Red Card!",
            "Penalty!",
            "Injury!",
            "Score:",
            "Substitution",
        ]

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

        # If you want to increase the odds of a particular event happening, simply change the number after the greater than sign in the following functions below. Increasing the number will decrease the odds of an event occuring and vice versa.

        async def TeamChance():
            xp = await self.config.levels()
            team1pl = teams[team1]["ids"]
            team2pl = teams[team2]["ids"]
            t1totalxp = 0
            t2totalxp = 0
            for memberid in team1pl:
                member = self.bot.get_user(memberid)
                try:
                    t1totalxp += int(xp[member.name])
                except KeyError:
                    t1totalxp += 1
            for memberid in team2pl:
                member = self.bot.get_user(memberid)
                try:
                    t2totalxp += int(xp[member.name])
                except KeyError:
                    t2totalxp += 1
            total = ["A"] * (t1totalxp) + ["B"] * (t2totalxp)
            rdmint = random.choice(total)
            if rdmint == "A":
                return team1Stats
            else:
                return team2Stats

        def yCardChance():
            rdmint = random.randint(0, 100)
            if rdmint > 98:
                return True

        def rCardChance():
            rdmint = random.randint(0, 300)
            if rdmint > 299:
                return True

        def goalChance():
            rdmint = random.randint(0, 100)
            if rdmint > 96:
                return True

        def penaltyChance():
            rdmint = random.randint(0, 250)
            if rdmint > 249:
                return True

        def penaltyBlock():
            rdmint = random.randint(0, 1)
            if rdmint > 0.6:
                return True

        # Add your own player roster by replacing the names in the lists below:

        def PlayerGenerator(event, team, yc, rc, injury, sub_in, sub_out):
            random.shuffle(team1players)
            random.shuffle(team2players)
            arsenalFirstsquad = team1players
            chelseaFirstsquad = team2players
            output = []
            if team == team1:
                fs_players = arsenalFirstsquad
                yc = yC_team1
                rc = rC_team1
                injury = injury_team1
                sub_in = sub_in_team1
                sub_out = sub_out_team1
            elif team == team2:
                fs_players = chelseaFirstsquad
                yc = yC_team2
                rc = rC_team2
                injury = injury_team2
                sub_in = sub_in_team2
                sub_out = sub_out_team2
            if event == 0:
                rosterUpdate = [i for i in fs_players if i not in rc]
                for i in sub_in:
                    rosterUpdate.append(i)
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
        b.append(team1 + " vs " + team2)
        b.append(team1 + ": " + ", ".join(team1players))
        b.append(team2 + ": " + ", ".join(team2players))
        b.append("\n**Match Start**!\n")
        await ctx.send("```" + "\n".join(b) + "```")
        b = []
        await asyncio.sleep(2)
        for min in range(1, 91):
            if events == False:
                gC = goalChance()
                if gC == True:
                    b = []
                    teamStats = await TeamChance()
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
                    b.append(
                        ""
                        + Event[5]
                        + " "
                        + team1.upper()
                        + " "
                        + str(team1Stats[8])
                        + " : "
                        + str(team2Stats[8])
                        + " "
                        + team2.upper()
                    )
                    b.append(
                        "\N{STOPWATCH} "
                        + str(min)
                        + " min: "
                        + "\N{SOCCER BALL} GOAALLL! ("
                        + str(playerGoal[0])
                        + " "
                        + str(Event[0])
                        + ") \n\N{HEAVY EXCLAMATION MARK SYMBOL} "
                        + str(playerGoal[1]).upper()
                        + " HAS SCORED!"
                    )
                    if playerGoal[1] not in goals:
                        goals[playerGoal[1]] = 1
                    else:
                        goals[playerGoal[1]] += 1
                    events = True
                    await ctx.send("```\n" + "\n".join(b) + "```")
                    await asyncio.sleep(2)
            if events == False:
                pC = penaltyChance()
                if pC == True:
                    teamStats = await TeamChance()
                    playerPenalty = PlayerGenerator(
                        3,
                        teamStats[0],
                        teamStats[1],
                        teamStats[2],
                        teamStats[3],
                        teamStats[4],
                        teamStats[5],
                    )
                    b = []
                    b.append(
                        "\N{STOPWATCH} "
                        + str(min)
                        + " IN: \n"
                        + str(playerPenalty[0])
                        + " "
                        + str(Event[3])
                    )
                    b.append("" + str(playerPenalty[1]) + " steps up to shoot...")
                    pB = penaltyBlock()
                    if pB == True:
                        b.append("SHOT BLOCKED!!")
                        events = True
                    else:
                        teamStats[8] += 1
                        b.append(
                            "\u200b\N{SOCCER BALL} GOAALLL!\n\N{HEAVY EXCLAMATION MARK SYMBOL}"
                            + str(playerPenalty[0]).upper()
                            + " HAS SCORED!"
                        )
                        b.append(
                            ""
                            + Event[5]
                            + " "
                            + team1.upper()
                            + " "
                            + str(team1Stats[8])
                            + " : "
                            + str(team2Stats[8])
                            + " "
                            + team2.upper()
                        )
                        if playerPenalty[0] not in goals:
                            goals[playerPenalty[0]] = 1
                        else:
                            goals[playerPenalty[0]] += 1
                        events = True
                    await ctx.send("```\n" + "\n".join(b) + "```")
                    await asyncio.sleep(2)
            if events == False:
                yC = yCardChance()
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
                    b = []
                    if len(playerYellow) == 3:
                        teamStats[7] += 1
                        b.append(
                            "\N{STOPWATCH} "
                            + str(min)
                            + " min: "
                            + str(playerYellow[0])
                            + " "
                            + str(Event[1])
                            + " "
                            + str(playerYellow[1])
                            + "\n"
                            + str(playerYellow[1])
                            + "'s Second Yellow! Red Card!"
                            + "\n         "
                            + str(playerYellow[0])
                            + " are down to "
                            + str(5 - (int(teamStats[7])))
                            + " men!"
                        )
                        if playerYellow[1] not in reds:
                            reds[playerYellow[1]] = 1
                            yellows[playerYellow[1]] += 1
                        else:
                            yellows[playerYellow[1]] += 1
                            reds[playerYellow[1]] += 1
                        teamStats[2].append(playerYellow[1])
                        events = True
                    else:
                        b.append(
                            "\N{STOPWATCH} "
                            + str(min)
                            + " min: "
                            + str(playerYellow[0])
                            + " "
                            + str(Event[1])
                            + " "
                            + str(playerYellow[1])
                        )
                        if playerYellow[1] not in yellows:
                            yellows[playerYellow[1]] = 1
                        else:
                            yellows[playerYellow[1]] += 1
                        teamStats[1].append(playerYellow[1])
                        events = True
                    await ctx.send("```\n" + "\n".join(b) + "```")
                    await asyncio.sleep(2)
            if events == False:
                rC = rCardChance()
                if rC == True:
                    b = []
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
                    b.append(
                        "\N{STOPWATCH} "
                        + str(min)
                        + " min: "
                        + str(playerRed[0])
                        + " "
                        + str(Event[2])
                        + " "
                        + str(playerRed[1])
                        + "\n"
                        + str(playerRed[0])
                        + " are down to "
                        + str(5 - (int(teamStats[7])))
                        + " men!"
                    )
                    if playerRed[1] not in reds:
                        reds[playerRed[1]] = 1
                    else:
                        reds[playerRed[1]] += 1
                    teamStats[2].append(playerRed[1])
                    events = True
                    await ctx.send("```\n" + "\n".join(b) + "```")
                    await asyncio.sleep(2)
            if events == False:
                pass
            events = False
            if min == 45:
                b = []
                added = random.randint(1, 5)
                b.append(str(added) + " Minute(s) of Stoppage Time")
                s = 45
                for i in range(added):
                    s += 1
                    gC = goalChance()
                    if gC == True:
                        teamStats = await TeamChance()
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
                        b.append(
                            "\N{STOPWATCH} "
                            + str(s)
                            + " min in stoppage time: \N{SOCCER BALL} GOAALLL! ("
                            + str(playerGoal[0])
                            + " "
                            + str(Event[0])
                            + ")\n\N{HEAVY EXCLAMATION MARK SYMBOL} "
                            + str(playerGoal[1]).upper()
                            + " HAS SCORED!"
                        )
                        b.append(
                            "        "
                            + Event[5]
                            + " "
                            + team1.upper()
                            + " "
                            + str(team1Stats[8])
                            + " : "
                            + str(team2Stats[8])
                            + " "
                            + team2.upper()
                        )
                        if playerGoal[1] not in goals:
                            goals[playerGoal[1]] = 1
                        else:
                            goals[playerGoal[1]] += 1
                        events = True
                    events = False
                await ctx.send("```\n" + "\n".join(b) + "```")
                await asyncio.sleep(2)
                await ctx.send("```css\n[HALF TIME]\n```")
                await asyncio.sleep(2)

            if min == 90:
                b = []
                added = random.randint(1, 5)
                b.append(str(added) + " Minute(s) of Stoppage Time")
                s = 90
                for i in range(added):
                    s += 1
                    gC = goalChance()
                    if gC == True:
                        teamStats = await TeamChance()
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
                        b.append(
                            "\N{STOPWATCH} "
                            + str(s)
                            + " min in stoppage time: \N{SOCCER BALL} GOAALLL! ("
                            + str(playerGoal[0])
                            + " "
                            + str(Event[0])
                            + ")\n\N{HEAVY EXCLAMATION MARK SYMBOL} "
                            + str(playerGoal[1]).upper()
                            + " HAS SCORED!"
                        )
                        b.append(
                            ""
                            + Event[5]
                            + " "
                            + team1.upper()
                            + " "
                            + str(team1Stats[8])
                            + " : "
                            + str(team2Stats[8])
                            + " "
                            + team2.upper()
                        )
                        if playerGoal[1] not in goals:
                            goals[playerGoal[1]] = 1
                        else:
                            goals[playerGoal[1]] += 1
                        events = True
                    events = False
                await ctx.send("```\n" + "\n".join(b) + "```")
                b = []
                b.append("\n[FULL TIME]\n")
                await ctx.send("```css\n" + "\n".join(b) + "```")
                await asyncio.sleep(5)
                await ctx.send(
                    "Final Score: "
                    + team1.upper()
                    + " "
                    + str(team1Stats[8])
                    + " : "
                    + str(team2Stats[8])
                    + " "
                    + team2.upper()
                )
                if team1Stats[8] > team2Stats[8]:
                    async with self.config.standings() as standings:
                        standings[team1]["wins"] += 1
                        standings[team1]["points"] += 3
                        standings[team1]["played"] += 1
                        standings[team2]["losses"] += 1
                        standings[team2]["played"] += 1
                if team1Stats[8] < team2Stats[8]:
                    async with self.config.standings() as standings:
                        standings[team2]["points"] += 3
                        standings[team2]["wins"] += 1
                        standings[team2]["played"] += 1
                        standings[team1]["losses"] += 1
                        standings[team1]["played"] += 1
                if team1Stats[8] == team2Stats[8]:
                    async with self.config.standings() as standings:
                        standings[team1]["played"] += 1
                        standings[team2]["played"] += 1
                        standings[team1]["points"] += 1
                        standings[team2]["points"] += 1
                        standings[team2]["draws"] += 1
                        standings[team1]["draws"] += 1
                team1gd = team1Stats[8] - team2Stats[8]
                team2gd = team2Stats[8] - team1Stats[8]
                async with self.config.standings() as standings:
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

        async with self.config.stats() as stats:
            for goal in goals:
                stats["goals"][goal] = goals[goal]
            for red in reds:
                stats["reds"][red] = reds[red]
            for yellowc in yellows:
                stats["yellows"][yellowc] = yellows[yellowc]
