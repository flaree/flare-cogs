import asyncio
from io import BytesIO

import aiohttp
import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class Livescores(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.len = {}
        self.api = "http://livescore-api.com/api-client/"

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def get(self, url):
        async with self.session.get(url) as response:
            return await response.json()

    @checks.admin()
    @commands.command()
    async def matchpost(self, ctx, matchid: int):
        """Live Match Posting"""
        api = await self.bot.db.api_tokens.get_raw(
            "livescore", default={"key": None, "secret": None}
        )
        if api["key"] is None or api["secret"] is None:
            return await ctx.send("Invalid API Key.")
        matches = await self.get(
            self.api + "scores/live.json?key={}&secret={}".format(api["key"], api["secret"])
        )
        if matches["success"] is False:
            return await ctx.send("Failed.")
        home = None
        away = None
        time = None
        for match in matches["data"]["match"]:
            if match["id"] == matchid:
                home = match["home_name"]
                away = match["away_name"]
                time = match["time"]
                if time == "HT":
                    time = 45
                if time == "FT":
                    return
                timeleft = (135 - int(time)) * 2
        if home is None:
            home = "Team Unavailable"
        if away is None:
            away = "Team Unavailable"
        if time is None:
            timeleft = 240
        counter = 0
        self.len[matchid] = 0
        while True:
            data = await self.get(
                self.api
                + "scores/events.json?key={}&secret={}&id={}".format(
                    api["key"], api["secret"], matchid
                )
            )
            if data["success"] is False:
                return await ctx.send("Failed to find match.")
            if data["data"]["event"]:
                if self.len[matchid] == 0:
                    self.len[matchid] = len(data["data"]["event"])
                try:
                    if player != "":
                        player = " ".join(data["data"]["event"][-1]["player"].split()[-1::-1])
                    else:
                        player = "Unavailable"
                except:
                    player = "Unavailable"
                if len(data["data"]["event"]) > self.len[matchid]:
                    if data["data"]["event"][-1]["event"] == "GOAL":
                        await ctx.send(
                            data["data"]["event"][-1]["event"]
                            + ": {}\nScored by ".format(
                                home if data["data"]["event"][-1]["home_away"] == "h" else away
                            )
                            + player
                            + ", "
                            + data["data"]["event"][-1]["time"]
                        )
                        self.len[matchid] = len(data["data"]["event"])
            await asyncio.sleep(30)
            counter += 1
            print(timeleft - counter, "requests left for this match.")
            if counter > timeleft:
                return

    @checks.admin()
    @commands.command()
    async def ongoing(self, ctx, compid=None):
        """List ongoing matches - optional competition/league id to shorten results."""
        api = await self.bot.db.api_tokens.get_raw(
            "livescore", default={"key": None, "secret": None}
        )
        if api["key"] is None or api["secret"] is None:
            return await ctx.send("Invalid API Key.")
        data = await self.get(
            self.api
            + "scores/live.json?key={}&secret={}{}".format(
                api["key"],
                api["secret"],
                "&competition_id={}".format(compid) if compid is not None else "",
            )
        )
        if data["success"] is False:
            return await ctx.send("Failed.")
        embeds = []
        if not data["data"]["match"]:
            return await ctx.send("No matches available.")
        for match in data["data"]["match"]:
            embed = discord.Embed(
                colour=ctx.author.color, title=f"{match['home_name']} vs {match['away_name']}"
            )
            for key in match:
                if key != "events":
                    embed.add_field(
                        name=key.replace("_", " ").title(),
                        value=match[key] if match[key] else "None",
                    )
            embeds.append(embed)
        if embeds:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send("No matches available.")

    @checks.admin()
    @commands.command()
    async def leagueid(self, ctx, *, name: str):
        """Find out the league ID to shorten results for ongoing matches"""
        api = await self.bot.db.api_tokens.get_raw(
            "livescore", default={"key": None, "secret": None}
        )
        if api["key"] is None or api["secret"] is None:
            return await ctx.send("Invalid API Key.")
        data = await self.get(
            self.api + "competitions/list.json?key={}&secret={}".format(api["key"], api["secret"])
        )
        if data["success"] is False:
            return await ctx.send("Failed.")
        embeds = []
        if data["data"]["competition"]:
            for match in data["data"]["competition"]:
                if name.lower() in match["name"].lower():
                    embed = discord.Embed(
                        colour=ctx.author.color, title="Matches for {}".format(name.title())
                    )
                    embed.add_field(name="League Name", value=match["name"])
                    embed.add_field(name="League ID", value=match["id"])
                    try:
                        embed.add_field(name="Country", value=match["countries"][0]["name"])
                        embed.add_field(name="Country ID", value=match["countries"][0]["id"])
                    except:
                        embed.add_field(name="Country", value=match["federations"][0]["name"])
                        embed.add_field(name="Country ID", value=match["federations"][0]["id"])
                    embeds.append(embed)
            if embeds:
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                await ctx.send("No leagues available.")

    @checks.admin()
    @commands.command()
    async def matchinfo(self, ctx, matchid: int):
        """Match information."""
        api = await self.bot.db.api_tokens.get_raw(
            "livescore", default={"key": None, "secret": None}
        )
        if api["key"] is None or api["secret"] is None:
            return await ctx.send("Invalid API Key.")
        data = await self.get(
            self.api + "scores/live.json?key={}&secret={}".format(api["key"], api["secret"])
        )
        if data["success"] is False:
            return await ctx.send("Failed.")
        embeds = []
        for match in data["data"]["match"]:
            if match["id"] == matchid:
                embed = discord.Embed(
                    colour=ctx.author.color, title=f"{match['home_name']} vs {match['away_name']}"
                )
                for key in match:
                    if key != "events":
                        embed.add_field(
                            name=key.replace("_", " ").title(),
                            value=match[key] if match[key] else "None",
                        )
                embeds.append(embed)
        if embeds:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send("No match available.")
