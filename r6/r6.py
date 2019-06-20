import discord
import aiohttp
import asyncio
from redbot.core import commands, checks, Config
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import datetime
from .stats import Stats


class R6(commands.Cog):
    """Rainbow6 Related Commands"""

    __version__ = "1.3.2"

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        default_member = {"picture": False}
        self.config.register_member(**default_member)
        self.bot = bot
        self.stats = Stats(bot)
        self.platforms = ["psn", "xbl", "uplay"]
        self.regions = {"na": "ncsa", "eu": "emea", "asia": "apac"}
        self.foreignops = {"jager": "jäger", "nokk": "nøkk", "capitao": "capitão"}

    @commands.group(autohelp=True)
    async def r6(self, ctx):
        """R6 Commands - Valid consoles are psn, xbl and uplay."""
        pass

    @r6.command()
    async def profile(self, ctx, profile, platform="uplay"):
        """General R6 Stats."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.profile(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.profilecreate(data)
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.color, title="R6 Profile for {}".format(profile)
                )
                embed.set_thumbnail(url=data["avatar_url_256"])
                embed.add_field(name="Level:", value=data["progression"]["level"])
                embed.add_field(
                    name="Timeplayed:",
                    value=str(
                        datetime.timedelta(seconds=int(data["stats"]["general"]["playtime"]))
                    ),
                )
                embed.add_field(name="Total Wins:", value=data["stats"]["general"]["wins"])
                embed.add_field(name="Total Losses:", value=data["stats"]["general"]["losses"])
                embed.add_field(name="Draws:", value=data["stats"]["general"]["draws"])
                embed.add_field(
                    name="Lootbox %:", value=data["progression"]["lootbox_probability"]
                )
                embed.add_field(name="Kills:", value=data["stats"]["general"]["kills"])
                embed.add_field(name="Deaths:", value=data["stats"]["general"]["deaths"])
                embed.add_field(name="KDR:", value=data["stats"]["general"]["kd"])
                try:
                    wlr = (
                        round(
                            data["stats"]["general"]["wins"]
                            / data["stats"]["general"]["games_played"],
                            2,
                        )
                        * 100
                    )
                except ZeroDivisionError:
                    wlr = 0
                embed.add_field(name="Total W/LR %:", value=wlr)
                try:
                    rwlr = (
                        round(
                            data["stats"]["queue"]["ranked"]["wins"]
                            / data["stats"]["queue"]["ranked"]["games_played"],
                            2,
                        )
                        * 100
                    )
                except ZeroDivisionError:
                    rwlr = 0
                embed.add_field(name="Total Ranked W/LR:", value=rwlr)
                await ctx.send(embed=embed)

    @r6.command()
    async def casual(self, ctx, profile, platform="uplay"):
        """Casual R6 Stats."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.profile(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.casualstatscreate(data)
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.colour, title="R6 Casual Statistics for {}".format(profile)
                )
                embed.set_thumbnail(url=data["avatar_url_256"])
                embed.add_field(name="Level:", value=data["progression"]["level"])
                embed.add_field(
                    name="Timeplayed:",
                    value=str(
                        datetime.timedelta(
                            seconds=int(data["stats"]["queue"]["casual"]["playtime"])
                        )
                    ),
                )
                embed.add_field(name="Total Wins:", value=data["stats"]["queue"]["casual"]["wins"])
                embed.add_field(
                    name="Total Losses:", value=data["stats"]["queue"]["casual"]["losses"]
                )
                embed.add_field(name="Draws:", value=data["stats"]["queue"]["casual"]["draws"])
                embed.add_field(
                    name="Total Games Played:",
                    value=data["stats"]["queue"]["casual"]["games_played"],
                )
                embed.add_field(name="Kills:", value=data["stats"]["queue"]["casual"]["kills"])
                embed.add_field(name="Deaths:", value=data["stats"]["queue"]["casual"]["deaths"])
                embed.add_field(name="KDR:", value=data["stats"]["queue"]["casual"]["kd"])
                try:
                    wlr = (
                        round(
                            data["stats"]["queue"]["casual"]["wins"]
                            / data["stats"]["queue"]["casual"]["games_played"],
                            2,
                        )
                        * 100
                    )
                except ZeroDivisionError:
                    wlr = 0
                embed.add_field(name="Total W/LR %:", value=wlr)
                await ctx.send(embed=embed)

    @r6.command()
    async def ranked(self, ctx, profile, platform="uplay"):
        """Ranked R6 Stats."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.profile(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.casualstatscreate(data)
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.colour, title="R6 Casual Statistics for {}".format(profile)
                )
                embed.set_thumbnail(url=data["avatar_url_256"])
                embed.add_field(name="Level:", value=data["progression"]["level"])
                embed.add_field(
                    name="Timeplayed:",
                    value=str(
                        datetime.timedelta(
                            seconds=int(data["stats"]["queue"]["ranked"]["playtime"])
                        )
                    ),
                )
                embed.add_field(name="Total Wins:", value=data["stats"]["queue"]["ranked"]["wins"])
                embed.add_field(
                    name="Total Losses:", value=data["stats"]["queue"]["ranked"]["losses"]
                )
                embed.add_field(name="Draws:", value=data["stats"]["queue"]["ranked"]["draws"])
                embed.add_field(
                    name="Total Games Played:",
                    value=data["stats"]["queue"]["ranked"]["games_played"],
                )
                embed.add_field(name="Kills:", value=data["stats"]["queue"]["ranked"]["kills"])
                embed.add_field(name="Deaths:", value=data["stats"]["queue"]["ranked"]["deaths"])
                embed.add_field(name="KDR:", value=data["stats"]["queue"]["ranked"]["kd"])
                try:
                    wlr = (
                        round(
                            data["stats"]["queue"]["ranked"]["wins"]
                            / data["stats"]["queue"]["ranked"]["games_played"],
                            2,
                        )
                        * 100
                    )
                except ZeroDivisionError:
                    wlr = 0
                embed.add_field(name="Total W/LR %:", value=wlr)
                await ctx.send(embed=embed)

    @r6.command()
    async def operator(self, ctx, profile, operator: str, platform="uplay"):
        """R6 Operator Stats."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if operator in self.foreignops:
            operator = self.foreignops[operator]
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.operators(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        ops = []
        for operators in data:
            ops.append(operators["name"].lower())
        if operator.lower() not in ops:
            return await ctx.send(
                "No statistics found for the current operator or the operator is invalid."
            )
        ind = ops.index(operator)
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.operatorstatscreate(data[ind], profile)
                await ctx.send(file=image)
            else:
                data = data[ind]
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} Statistics for {}".format(operator.title(), profile),
                )
                embed.set_thumbnail(url=data["badge_image"])
                embed.add_field(name="Kills:", value=data["kills"])
                embed.add_field(name="Deaths:", value=data["deaths"])
                embed.add_field(name="Wins:", value=data["wins"])
                embed.add_field(name="Losses:", value=data["losses"])
                embed.add_field(name="KDR:", value=data["kd"])
                embed.add_field(
                    name="Playtime:", value=str(datetime.timedelta(seconds=int(data["playtime"])))
                )
                embed.add_field(name="Headshots:", value=data["headshots"])
                embed.add_field(
                    name="W/LR %:", value=round(data["wins"] / (data["wins"] + data["losses"]), 2)
                )
                try:
                    for ability in data["abilities"]:
                        embed.add_field(name=ability["ability"], value=ability["value"])
                except KeyError:
                    pass
                await ctx.send(embed=embed)

    @r6.command()
    async def season(self, ctx, profile, platform, region, season: int):
        """R6 Seasonal Stats."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        if region not in self.regions:
            return await ctx.send("Not a valid region.")
        region = self.regions[region]
        data = await self.stats.ranked(profile, platform, region, season, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        if data == "Season not found":
            return await ctx.send("The season you provided was not found.")
        if season > len(data[0]) or season < 7:
            return await ctx.send("Invalid season.")
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.seasoncreate(data, season, profile)
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} Statistics for {}".format(
                        data[0][season].title().replace("_", " "), profile
                    ),
                )
                embed.set_thumbnail(
                    url=self.stats.rank[list(self.stats.rank)[data[1]["max_rank"]]]
                )
                embed.add_field(name="Wins:", value=data[1]["wins"])
                embed.add_field(name="Losses:", value=data[1]["losses"])
                embed.add_field(name="Abandons:", value=data[1]["abandons"])
                embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")
                embed.add_field(name="Max MMR:", value=data[1]["max_mmr"])
                embed.add_field(name="End MMR:", value=data[1]["mmr"])
                embed.add_field(name="Max Rank:", value=list(self.stats.rank)[data[1]["max_rank"]])
                embed.add_field(name="End Rank:", value=data[1]["rank_text"])
                await ctx.send(embed=embed)

    @r6.command()
    async def operators(self, ctx, profile, platform, statistic):
        """Statistics for all operators.
        If you do not have any stats for an operator then it is ommited.
        Different stats include kills, deaths, kd, wins, losses, headshots, dbnos, meele_kills and playtime"""
        stats = [
            "kills",
            "deaths",
            "kd",
            "wins",
            "losses",
            "wl",
            "headshots",
            "dbnos",
            "meele_kills",
            "playtime",
        ]
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if statistic.lower() not in stats:
            return await ctx.send("Not a valid statistic.")
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.operators(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        ops = []
        for operators in data:
            ops.append(operators["name"].lower())
        if not ops:
            return await ctx.send("No operator statistics found.")
        if len(ops) > 26:
            opsone = ops[:26]
            opstwo = ops[26:]
            async with ctx.typing():
                em1 = discord.Embed(
                    title=f"{statistic.title()} statistics for {profile} - Page 1/2",
                    colour=ctx.authour.colour,
                )
                em2 = discord.Embed(
                    title=f"{statistic.title()} statistics for {profile} - Page 2/2",
                    colour=ctx.author.colour,
                )
                for i in range(len(opsone)):
                    if statistic.lower() != "playtime":
                        em1.add_field(name=data[i]["name"], value=data[i][statistic])
                    else:
                        em1.add_field(
                            name=data[i]["name"],
                            value=str(datetime.timedelta(seconds=int(data[i][statistic]))),
                        )
                for i in range(len(opstwo)):
                    i += 25
                    if statistic.lower() != "playtime":
                        em2.add_field(name=data[i]["name"], value=data[i][statistic])
                    else:
                        em2.add_field(
                            name=data[i]["name"],
                            value=str(datetime.timedelta(seconds=int(data[i][statistic]))),
                        )
            embeds = []
            embeds.append(em1)
            embeds.append(em2)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            async with ctx.typing():
                em1 = discord.Embed(
                    title=f"{statistic.title()} statistics for {profile}", colour=ctx.author.colour
                )
                for i in range(len(ops)):
                    if statistic.lower() != "playtime":
                        em1.add_field(name=data[i]["name"], value=data[i][statistic])
                    else:
                        em1.add_field(
                            name=data[i]["name"],
                            value=str(datetime.timedelta(seconds=int(data[i][statistic]))),
                        )
            await ctx.send(embed=em1)

    @r6.command()
    async def general(self, ctx, profile, platform="uplay"):
        """General R6S Stats."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.profile(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        async with ctx.typing():
            embed = discord.Embed(
                title="General R6S Stats for {}".format(profile), color=ctx.author.colour
            )
            for stat in data["stats"]["general"]:
                if stat != "playtime":
                    embed.add_field(
                        name=stat.replace("_", " ").title(), value=data["stats"]["general"][stat]
                    )
                else:
                    embed.add_field(
                        name=stat.replace("_", " ").title(),
                        value=str(datetime.timedelta(seconds=int(data["stats"]["general"][stat]))),
                    )
        await ctx.send(embed=embed)

    @r6.command()
    async def weapontype(self, ctx, profile, platform="uplay"):
        """R6 Weapon type statistics."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.weapontypes(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        embed = discord.Embed(
            color=ctx.author.colour, title="Weapon Statistics for {}".format(profile)
        )
        weps = data["categories"]
        for wep in weps:
            embed.add_field(
                name=wep["category"],
                value="**Kills**: {}\n**Deaths**: {}\n**KD**: {}\n**Headshots**: {}\n**HS%**: {}\n**Times Chosen**: {}\n**Bullets Fired**: {}\n**Bullets Hit**: {}".format(
                    wep["kills"],
                    wep["deaths"],
                    wep["kd"],
                    wep["headshots"],
                    wep["headshot_percentage"],
                    wep["times_chosen"],
                    wep["bullets_fired"],
                    wep["bullets_hit"],
                ),
            )
        embed.add_field(name="\N{ZERO WIDTH SPACE}", value="\N{ZERO WIDTH SPACE}")
        await ctx.send(embed=embed)

    @r6.command()
    async def weapon(self, ctx, profile, weapon: str, platform="uplay"):
        """R6 Weapon Statistics.
        If the weapon name has a space, please surround it with quotes."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.weapons(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        weapons = []
        for wep in data["weapons"]:
            weapons.append(wep["weapon"].lower())
        if weapon.lower() not in weapons:
            return await ctx.send("Invalid weapon or no statistics available.")
        ind = weapons.index(weapon.lower())
        embed = discord.Embed(
            colour=ctx.author.colour,
            title="{} information for {}".format(weapon.upper(), profile),
            description="**Category**: {}\n**Kills**: {}\n**Deaths**: {}\n**KD**: {}\n**Headshots**: {}\n**HS %**: {}\n**Times Chosen**: {}\n**Bullets Fired**: {}\n**Bullets Hit**: {}".format(
                data["weapons"][ind]["category"],
                data["weapons"][ind]["kills"],
                data["weapons"][ind]["deaths"],
                data["weapons"][ind]["kd"],
                data["weapons"][ind]["headshots"],
                data["weapons"][ind]["headshot_percentage"],
                data["weapons"][ind]["times_chosen"],
                data["weapons"][ind]["bullets_fired"],
                data["weapons"][ind]["bullets_hit"],
            ),
        )
        await ctx.send(embed=embed)

    @r6.command()
    async def leaderboard(self, ctx, platform, region: str = "all", page: int = 1):
        """R6 Leaderboard Statistics.
        Regions: all, eu, na, asia"""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        if region != "all" and region not in self.regions:
            return await ctx.send("Not a valid region.")
        if page < 1 or page > 50:
            return await ctx.send("Invalid page number, must be between 1 and 50.")
        if region == "all":
            pass
        else:
            region = self.regions[region]
        data = await self.stats.leaderboard(platform, region, page, api["authorization"])
        if data is None:
            return await ctx.send("Invalid request, no statistics found.")
        embeds = []
        for i in range(0, 100, 25):
            embed = discord.Embed(
                colour=ctx.author.colour,
                title=f"R6 Leaderboard Statistics for {platform.upper()} - Region: {region.upper()}",
            )
            for player in data[i : i + 25]:
                embed.add_field(
                    name=f"{player['position']}. {player['username']}",
                    value=f"**Level**: {player['stats']['level']}\n**KD**: {player['stats']['kd']}\n**WL/R**: {player['stats']['wl']}\n**Score**: {round(player['score'], 2)}",
                )
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @r6.command()
    async def gamemodes(self, ctx, profile: str, platform: str = "uplay"):
        """R6 Gamemode Statistics."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.profile(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        embeds = []
        async with ctx.typing():
            for gm in data["stats"]["gamemode"]:
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} statistics for {}".format(gm.replace("_", " ").title(), profile),
                )
                for stat in data["stats"]["gamemode"][gm]:
                    if stat == "playtime":
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=datetime.timedelta(seconds=data["stats"]["gamemode"][gm][stat]),
                        )
                    else:
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=data["stats"]["gamemode"][gm][stat],
                        )
                embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @r6.command()
    async def queue(self, ctx, profile: str, platform: str = "uplay"):
        """R6 stats from casual, ranked & other together."""
        api = await self.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
        if api["authorization"] is None:
            return await ctx.send(
                "Your R6Stats API key has not been set. Check out {}r6set for more informtion.".format(
                    ctx.prefix
                )
            )
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.profile(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        embeds = []
        async with ctx.typing():
            for gm in data["stats"]["queue"]:
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} statistics for {}".format(gm.replace("_", " ").title(), profile),
                )
                for stat in data["stats"]["queue"][gm]:
                    if stat == "playtime":
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=datetime.timedelta(seconds=data["stats"]["queue"][gm][stat]),
                        )
                    else:
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=data["stats"]["queue"][gm][stat],
                        )
                embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @r6.command()
    async def setpicture(self, ctx, toggle: bool = True):
        """Set wheter to recieve an embed or a picture.
        Toggle must be a valid bool."""
        await self.config.member(ctx.author).picture.set(toggle)
        if toggle:
            await ctx.send("Your stat messages will now be sent as a picture.")
        else:
            await ctx.send("Your stat messages will now be sent as an embed.")

    @checks.is_owner()
    @commands.command()
    async def r6set(self, ctx):
        """Instructions on how to set the api key."""
        message = "1. You must retrieve an API key from the R6Stats website.\n2. Copy your api key into `{}set api r6stats authorization,your_r6stats_apikey`".format(
            ctx.prefix
        )
        await ctx.maybe_send_embed(message)
