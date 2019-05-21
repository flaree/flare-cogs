import random
import discord
import aiohttp
import asyncio
from redbot.core import commands, checks
from . import __path__
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
import datetime
import os
from .stats import Stats


class R6(commands.Cog):
    """Rainbow6 Related Commands"""

    __version__ = "0.3.1"

    def __init__(self, bot):
        self.bot = bot
        self.stats = Stats(bot)
        self.platforms = ["psn", "xbl", "uplay"]
        self.regions = {"na": "ncsa", "eu": "emea", "asia": "apac"}

    @commands.group(autohelp=True)
    async def r6(self, ctx):
        """R6 Commands"""
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
            image = await self.stats.profilecreate(data)
            await ctx.send(file=image)

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
            image = await self.stats.casualstatscreate(data)
            await ctx.send(file=image)

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
            image = await self.stats.rankedstatscreate(data)
            await ctx.send(file=image)

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
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.stats.operators(profile, platform, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        ops = []
        for operators in data:
            ops.append(operators["name"].lower())
        if operator not in ops:
            return await ctx.send("No statistics found for the current operator.")
        ind = ops.index(operator)
        async with ctx.typing():
            image = await self.stats.operatorstatscreate(data[ind], profile)
            await ctx.send(file=image)

    @r6.command()
    async def season(self, ctx, profile, platform, region, season: int = 12):
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
        if season > 12 or season < 7:
            return await ctx.send("Invalid season.")
        region = self.regions[region]
        data = await self.stats.ranked(profile, platform, region, season, api["authorization"])
        if data is None:
            return await ctx.send("User not found.")
        async with ctx.typing():
            image = await self.stats.seasoncreate(data, season, profile)
            await ctx.send(file=image)

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
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        if len(ops) > 26:
            opsone = ops[:26]
            opstwo = ops[26:]
            async with ctx.typing():
                em1 = discord.Embed(
                    title=f"{statistic.title()} statistics for {profile} - Page 1/2", colour=colour
                )
                em2 = discord.Embed(
                    title=f"{statistic.title()} statistics for {profile} - Page 2/2", colour=colour
                )
                for i, op in enumerate(opsone):
                    if statistic.lower() != "playtime":
                        em1.add_field(name=data[i]["name"], value=data[i][statistic])
                    else:
                        em1.add_field(
                            name=data[i]["name"],
                            value=str(datetime.timedelta(seconds=int(data[i][statistic]))),
                        )
                for i, op in enumerate(opstwo, 25):
                    print(i)
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
                    title=f"{statistic.title()} statistics for {profile}", colour=colour
                )
                for i, op in enumerate(opsone):
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
            embed = discord.Embed(title="General R6S Stats for {}".format(profile), color=0xFF0000)
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
        embed = discord.Embed(color=0xFF0000, title="Weapon Statistics for {}".format(profile))
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
        """R6S Weapon Statistics
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
            colour=0xFF0000,
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
        """R6 Leaderboard Statistics
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
        embed = discord.Embed(
            colour=0xFF0000,
            title=f"R6 Leaderboard Statistics for {platform.upper()} - Region: {region.upper()}",
        )
        embedone = discord.Embed(
            colour=0xFF0000,
            title=f"R6 Leaderboard Statistics for {platform.upper()} - Region: {region.upper()}",
        )
        embedtwo = discord.Embed(
            colour=0xFF0000,
            title=f"R6 Leaderboard Statistics for {platform.upper()} - Region: {region.upper()}",
        )
        embedthree = discord.Embed(
            colour=0xFF0000,
            title=f"R6 Leaderboard Statistics for {platform.upper()} - Region: {region.upper()}",
        )
        for player in data[:25]:
            embed.add_field(
                name=f"{player['position']}. {player['username']}",
                value=f"**Level**: {player['stats']['level']}\n**KD**: {player['stats']['kd']}\n**Score**: {round(player['score'], 2)}",
            )
        for player in data[25:50]:
            embedone.add_field(
                name=f"{player['position']}. {player['username']}",
                value=f"**Level**: {player['stats']['level']}\n**KD**: {player['stats']['kd']}\n**Score**: {round(player['score'], 2)}",
            )
        for player in data[50:75]:
            embedtwo.add_field(
                name=f"{player['position']}. {player['username']}",
                value=f"**Level**: {player['stats']['level']}\n**KD**: {player['stats']['kd']}\n**Score**: {round(player['score'], 2)}",
            )
        for player in data[75:]:
            embedthree.add_field(
                name=f"{player['position']}. {player['username']}",
                value=f"**Level**: {player['stats']['level']}\n**KD**: {player['stats']['kd']}\n**Score**: {round(player['score'], 2)}",
            )
        embeds.append(embed)
        embeds.append(embedone)
        embeds.append(embedtwo)
        embeds.append(embedthree)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @checks.is_owner()
    @commands.command()
    async def r6set(self, ctx):
        """Instructions on how to set the api key."""
        message = "1. You must retrieve an API key from the R6Stats website.\n2. Copy your api key into `{}set api r6stats authorization,your_r6stats_apikey`".format(
            ctx.prefix
        )
        await ctx.maybe_send_embed(message)
