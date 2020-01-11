import typing

import discord
import r6statsapi
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify, humanize_timedelta
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .stats import Stats


async def tokencheck(ctx):
    try:
        token = await ctx.bot.db.api_tokens.get_raw("r6stats", default={"authorization": None})
    except AttributeError:
        token = await ctx.bot.get_shared_api_tokens("r6stats")
    if token.get("authorization") is not None:
        return True
    else:
        return False


class R6(commands.Cog):
    """Rainbow6 Related Commands"""

    __version__ = "1.5.2"

    def __init__(self, bot):
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        default_member = {"picture": False}
        self.config.register_member(**default_member)
        self.bot = bot
        self.stats = Stats(bot)
        self.platforms = {
            "psn": r6statsapi.Platform.psn,
            "ps4": r6statsapi.Platform.psn,
            "ps": r6statsapi.Platform.psn,
            "xbl": r6statsapi.Platform.xbox,
            "xbox": r6statsapi.Platform.xbox,
            "uplay": r6statsapi.Platform.uplay,
            "pc": r6statsapi.Platform.uplay,
        }
        self.regions = {
            "na": "ncsa",
            "eu": "emea",
            "asia": "apac",
            "us": "ncsa",
            "as": "apac",
            "europe": "emea",
        }
        self.foreignops = {"jager": "jäger", "nokk": "nøkk", "capitao": "capitão"}
        self.client = None

    async def initalize(self):
        try:
            token = await self.bot.db.api_tokens.get_raw(
                "r6stats", default={"authorization": None}
            )
        except AttributeError:
            token = await self.bot.get_shared_api_tokens("r6stats")
        self.client = r6statsapi.Client(token.get("authorization", None))

    def cog_unload(self):
        self.client.destroy()

    async def request_data(self, ctx, type, **kwargs):
        types = {
            "generic": self.client.get_generic_stats,
            "seasonal": self.client.get_seasonal_stats,
            "operator": self.client.get_operators_stats,
            "weapon": self.client.get_weapon_stats,
            "weaponcategories": self.client.get_weaponcategory_stats,
            "queue": self.client.get_queue_stats,
            "gamemodes": self.client.get_gamemode_stats,
            "leaderboard": self.client.get_leaderboard,
        }
        request = types[type]
        exceptionstatus = False
        try:
            data = await request(**kwargs)
        except r6statsapi.errors.Unauthorized:
            await ctx.send(
                f"The current token is invalid. Please set a new one with help from the {ctx.prefix}r6set command and reload the cog."
            )
            exceptionstatus = True
        except r6statsapi.errors.HTTPException as e:
            await ctx.send(f"There was an error during the request.\nError Message: {' '.join(e.message.strip('_'))}")
            exceptionstatus = True
        except r6statsapi.errors.InternalError:
            await ctx.send(
                "There was an internal error processing your request, please try again later."
            )
            exceptionstatus = True
        except r6statsapi.errors.PlayerNotFound:
            await ctx.send(
                "The player provided was not found, please check your spelling and platform and try again."
            )
            exceptionstatus = True
        if exceptionstatus:
            return None
        return data

    @commands.check(tokencheck)
    @commands.group(autohelp=True)
    async def r6(self, ctx):
        """Rainbow 6 Siege Statistics
        
        Valid consoles are psn, xbox and pc.
        Valid regions are NA, EU and Asia"""
        pass

    @r6.command()
    async def profile(self, ctx, profile, platform="uplay"):
        """General R6 Stats.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "generic", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.profilecreate(data)
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.color, title="R6 Profile for {}".format(profile)
                )
                try:
                    wlr = (
                        round(data.general_stats["wins"] / data.general_stats["games_played"], 2)
                        * 100
                    )
                except ZeroDivisionError:
                    wlr = 0
                embed.set_thumbnail(url=data.avatar_url_256)
                accstats = f'**Level**: {data.level}\n**Playtime**: {humanize_timedelta(seconds=int(data.general_stats["playtime"]))}\n**Lootbox %**: {data.lootbox_probability}%'
                stats = f'**Wins**: {data.general_stats["wins"]}\n**Losses**: {data.general_stats["losses"]}\n**Draws**: {data.general_stats["draws"]}\n**W/L Ratio**: {wlr}%'
                killstats = f'**Kills**: {data.general_stats["kills"]}\n**Deaths**: {data.general_stats["deaths"]}\n**KDR**: {data.general_stats["kd"]}'
                embed.add_field(name="Account Stats", value=accstats, inline=False)
                embed.add_field(name="Match Stats", value=stats, inline=True)
                embed.add_field(name="Kill Stats", value=killstats, inline=True)
                await ctx.send(embed=embed)

    @r6.command()
    async def casual(self, ctx, profile, platform="uplay"):
        """Casual R6 Stats.
        
        Valid platforms are psn, xbl and uplay."""

        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "generic", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.casualstatscreate(data)
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.colour, title="R6 Casual Statistics for {}".format(profile)
                )
                embed.set_thumbnail(url=data.avatar_url_256)
                try:
                    wlr = (
                        round(
                            data.queue_stats["casual"]["wins"]
                            / data.queue_stats["casual"]["games_played"],
                            2,
                        )
                        * 100
                    )
                except ZeroDivisionError:
                    wlr = 0
                accstats = f'**Level**: {data.level}\n**Playtime**: {humanize_timedelta(seconds=int(data.queue_stats["casual"]["playtime"]))}'
                stats = f'**Games Playes**: {data.queue_stats["casual"]["games_played"]}\n**Wins**: {data.queue_stats["casual"]["wins"]}\n**Losses**: {data.queue_stats["casual"]["losses"]}\n**Draws**: {data.queue_stats["casual"]["draws"]}\n**W/L Ratio**: {wlr}%'
                killstats = f'**Kills**: {data.queue_stats["casual"]["kills"]}\n**Deaths**: {data.queue_stats["casual"]["deaths"]}\n**KDR**: {data.queue_stats["casual"]["kd"]}'
                embed.add_field(name="Account Stats", value=accstats, inline=False)
                embed.add_field(name="Match Stats", value=stats, inline=True)
                embed.add_field(name="Kill Stats", value=killstats, inline=True)
                await ctx.send(embed=embed)

    @r6.command()
    async def ranked(self, ctx, profile, platform="uplay"):
        """Ranked R6 Stats.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "generic", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.rankedstatscreate(data)
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.colour, title="R6 Ranked Statistics for {}".format(profile)
                )
                embed.set_thumbnail(url=data.avatar_url_256)
                try:
                    wlr = (
                        round(
                            data.queue_stats["ranked"]["wins"]
                            / data.queue_stats["ranked"]["games_played"],
                            2,
                        )
                        * 100
                    )
                except ZeroDivisionError:
                    wlr = 0
                accstats = f'**Level**: {data.level}\n**Playtime**: {humanize_timedelta(seconds=int(data.queue_stats["ranked"]["playtime"]))}'
                stats = f'**Games Playes**: {data.queue_stats["ranked"]["games_played"]}\n**Wins**: {data.queue_stats["ranked"]["wins"]}\n**Losses**: {data.queue_stats["ranked"]["losses"]}\n**Draws**: {data.queue_stats["casual"]["draws"]}\n**W/L Ratio**: {wlr}%'
                killstats = f'**Kills**: {data.queue_stats["ranked"]["kills"]}\n**Deaths**: {data.queue_stats["ranked"]["deaths"]}\n**KDR**: {data.queue_stats["ranked"]["kd"]}'
                embed.add_field(name="Account Stats", value=accstats, inline=False)
                embed.add_field(name="Match Stats", value=stats, inline=True)
                embed.add_field(name="Kill Stats", value=killstats, inline=True)
                await ctx.send(embed=embed)

    @r6.command()
    async def operator(self, ctx, profile, operator: str, platform="uplay"):
        """R6 Operator Stats.
        
        Valid platforms are psn, xbl and uplay."""
        if operator in self.foreignops:
            operator = self.foreignops[operator]
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "operator", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        ops = []
        for operators in data.operators:
            ops.append(operators["name"].lower())
        if operator.lower() not in ops:
            return await ctx.send(
                "No statistics found for the current operator or the operator is invalid."
            )
        ind = ops.index(operator)
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.operatorstatscreate(data, ind, profile)
                await ctx.send(file=image)
            else:
                data = data.operators[ind]
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} Statistics for {}".format(operator.title(), profile),
                )
                embed.set_thumbnail(url=data["badge_image"])
                wlr = round(data["wins"] / (data["wins"] + data["losses"]), 2)
                accstats = f'**Operator**: {operator.title()}\n**Playtime**: {humanize_timedelta(seconds=int(data["playtime"]))}'
                stats = f'**Wins**: {data["wins"]}\n**Losses**: {data["losses"]}\n**W/L Ratio**: {wlr}%'
                killstats = f'**Kills**: {data["kills"]}\n**Deaths**: {data["deaths"]}\n**KDR**: {data["kd"]}\n**Headshots**: {data["headshots"]}'
                embed.add_field(name="Operator Info", value=accstats, inline=False)
                embed.add_field(name="Match Stats", value=stats, inline=True)
                embed.add_field(name="Kill Stats", value=killstats, inline=True)
                try:
                    msg = ""
                    for ability in data["abilities"]:
                        msg += f'**{ability["ability"]}**: {ability["value"]}'
                    embed.add_field(name="Operator Stats", value=msg)
                except KeyError:
                    pass
                await ctx.send(embed=embed)

    async def seasonalstats(self, ctx, profile, platform):
        data = await self.request_data(ctx, "seasonal", player=profile, platform=platform)
        if data is None:
            return None
        seasons = list(data.seasons.keys())
        seasons += [None] * 6
        seasons.reverse()
        return (seasons, data.seasons, data)

    @r6.command()
    async def season(self, ctx, profile, platform, region, season: typing.Optional[int]):
        """R6 Seasonal Stats.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        if region not in self.regions:
            return await ctx.send("Not a valid region.")
        region = self.regions[region]
        data = await self.seasonalstats(ctx, profile, platform)
        if data is None:
            return
        if not season:
            season = len(data[0]) - 1
        if season > len(data[0]) - 1 or season < 6:
            return await ctx.send("Invalid season.")
        seasondata = data[1][data[0][season]]["regions"][region][0]
        if season >= 14:
            ranks = self.stats.ranksember
        else:
            ranks = self.stats.ranks
        async with ctx.typing():
            picture = await self.config.member(ctx.author).picture()
            if picture:
                image = await self.stats.seasoncreate(
                    data[2], seasondata, season, profile, data[1][data[0][season]]["name"]
                )
                await ctx.send(file=image)
            else:
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} Statistics for {}".format(
                        data[0][season].title().replace("_", " "), profile
                    ),
                )
                embed.set_thumbnail(url=self.stats.rankurl + ranks[seasondata["rank_text"]])

                accstats = f'**Rank**: {seasondata["rank_text"]}\n**MMR**: {seasondata["mmr"]}\n**Max Rank**: {list(ranks)[seasondata["max_rank"]]}\n**Max MMR**: {seasondata["max_mmr"]}'
                if seasondata["rank_text"] == "Champions":
                    accstats += (
                        f'\n**Champions Position**: #{str(seasondata["champions_rank_position"])}'
                    )
                try:
                    wlr = (
                        round(
                            seasondata["wins"]
                            / (seasondata["wins"] + seasondata["losses"] + seasondata["abandons"]),
                            2,
                        )
                        * 100
                    )
                except ZeroDivisionError:
                    wlr = 0
                stats = f'**Wins**: {seasondata["wins"]}\n**Losses**: {seasondata["losses"]}\n**Abandons**: {seasondata["abandons"]}\n**W/L Ratio**: {wlr}%'
                try:
                    kd = round(seasondata["kills"] / seasondata["deaths"], 2)
                except ZeroDivisionError:
                    kd = 0
                except TypeError:
                    kd = "Error calculating KDR"
                killstats = f'**Kills**: {seasondata["kills"]}\n**Deaths**: {seasondata["deaths"]}\n**KDR**: {kd}'
                embed.add_field(name="Season Stats", value=accstats, inline=False)
                embed.add_field(name="Match Stats", value=stats, inline=True)
                embed.add_field(name="Kill Stats", value=killstats, inline=True)
                await ctx.send(embed=embed)

    @r6.command()
    async def operators(self, ctx, profile, platform, statistic):
        """Statistics for all operators.

        If you do not have any stats for an operator then it is ommited.
        Different stats include kills, deaths, kd, wins, losses, headshots, dbnos, meele_kills and playtime
        
        Valid platforms are psn, xbl and uplay."""
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
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        if statistic not in stats:
            return await ctx.send(
                "Invalid Statistic. Please use one of the following:\n```{}```".format(
                    ", ".join(stats)
                )
            )
        data = await self.request_data(
            ctx, "operator", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        ops = []
        for operators in data.operators:
            ops.append(operators["name"].lower())
        if not ops:
            return await ctx.send("No operator statistics found.")
        if len(ops) > 26:
            opsone = ops[:26]
            opstwo = ops[26:]
            async with ctx.typing():
                em1 = discord.Embed(
                    title=f"{statistic.title()} statistics for {profile} - Page 1/2",
                    colour=ctx.author.colour,
                )
                em2 = discord.Embed(
                    title=f"{statistic.title()} statistics for {profile} - Page 2/2",
                    colour=ctx.author.colour,
                )
                for i in range(len(opsone)):
                    if statistic.lower() != "playtime":
                        em1.add_field(
                            name=data.operators[i]["name"], value=data.operators[i][statistic]
                        )
                    else:
                        em1.add_field(
                            name=data.operators[i]["name"],
                            value=str(
                                humanize_timedelta(seconds=int(data.operators[i][statistic]))
                            ),
                        )
                for i in range(len(opstwo)):
                    i += 25
                    if statistic.lower() != "playtime":
                        em2.add_field(
                            name=data.operators[i]["name"], value=data.operators[i][statistic]
                        )
                    else:
                        em2.add_field(
                            name=data.operators[i]["name"],
                            value=str(
                                humanize_timedelta(seconds=int(data.operators[i][statistic]))
                            ),
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
                        em1.add_field(
                            name=data.operators[i]["name"], value=data.operators[i][statistic]
                        )
                    else:
                        em1.add_field(
                            name=data.operators[i]["name"],
                            value=str(
                                humanize_timedelta(seconds=int(data.operators[i][statistic]))
                            ),
                        )
            await ctx.send(embed=em1)

    @r6.command()
    async def general(self, ctx, profile, platform="uplay"):
        """General R6 Stats.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "generic", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        async with ctx.typing():
            embed = discord.Embed(
                title="General R6S Stats for {}".format(profile), color=ctx.author.colour
            )
            for stat in data.general_stats:
                if stat != "playtime":
                    embed.add_field(
                        name=stat.replace("_", " ").title(), value=data.general_stats[stat]
                    )
                else:
                    embed.add_field(
                        name=stat.replace("_", " ").title(),
                        value=str(humanize_timedelta(seconds=int(data.general_stats[stat]))),
                    )
        await ctx.send(embed=embed)

    @r6.command(aliases=["weapontypes"])
    async def weaponcategories(self, ctx, profile, platform="uplay"):
        """R6 Weapon type statistics.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "weaponcategories", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        embed = discord.Embed(
            color=ctx.author.colour, title="Weapon Statistics for {}".format(profile)
        )
        weps = data.weapon_categories
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

        If the weapon name has a space, please surround it with quotes.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "weapon", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        weapons = []
        for wep in data.weapons:
            weapons.append(wep["weapon"].lower())
        if weapon.lower() not in weapons:
            return await ctx.send("Invalid weapon or no statistics available.")
        ind = weapons.index(weapon.lower())
        embed = discord.Embed(
            colour=ctx.author.colour,
            title="{} information for {}".format(weapon.upper(), profile),
            description="**Category**: {}\n**Kills**: {}\n**Deaths**: {}\n**KD**: {}\n**Headshots**: {}\n**HS %**: {}\n**Times Chosen**: {}\n**Bullets Fired**: {}\n**Bullets Hit**: {}".format(
                data.weapons[ind]["category"],
                data.weapons[ind]["kills"],
                data.weapons[ind]["deaths"],
                data.weapons[ind]["kd"],
                data.weapons[ind]["headshots"],
                data.weapons[ind]["headshot_percentage"],
                data.weapons[ind]["times_chosen"],
                data.weapons[ind]["bullets_fired"],
                data.weapons[ind]["bullets_hit"],
            ),
        )
        await ctx.send(embed=embed)

    @r6.command()
    async def leaderboard(self, ctx, platform, region: str = "all", page: int = 1):
        """R6 Leaderboard Statistics.

        Regions: all, eu, na, asia
        
        Valid platforms are psn, xbl and uplay."""
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
        data = await self.request_data(
            ctx, "leaderboard", platform=self.platforms[platform], region=region, page=page
        )
        if data is None:
            return
        embeds = []
        for i in range(0, 100, 25):
            embed = discord.Embed(
                colour=ctx.author.colour,
                title=f"R6 Leaderboard Statistics for {platform.upper()} - Region: {region.upper()}",
            )
            for player in data.leaderboard[i : i + 25]:
                embed.add_field(
                    name=f"{player['position']}. {player['username']}",
                    value=f"**Level**: {player['stats']['level']}\n**KD**: {player['stats']['kd']}\n**WL/R**: {player['stats']['wl']}\n**Score**: {round(player['score'], 2)}",
                )
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @r6.command()
    async def gamemodes(self, ctx, profile: str, platform: str = "uplay"):
        """R6 Gamemode Statistics.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "gamemodes", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        embeds = []
        async with ctx.typing():
            for gm in data.gamemode_stats:
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} statistics for {}".format(gm.replace("_", " ").title(), profile),
                )
                for stat in data.gamemode_stats[gm]:
                    if stat == "playtime":
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=humanize_timedelta(seconds=data.gamemode_stats[gm][stat]),
                        )
                    else:
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=data.gamemode_stats[gm][stat],
                        )
                embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @r6.command()
    async def queue(self, ctx, profile: str, platform: str = "uplay"):
        """R6 stats from casual, ranked & other together.
        
        Valid platforms are psn, xbl and uplay."""
        if platform not in self.platforms:
            return await ctx.send("Not a valid platform.")
        data = await self.request_data(
            ctx, "queue", player=profile, platform=self.platforms[platform]
        )
        if data is None:
            return
        if data.queue_stats is None:
            return await ctx.send("User not found.")
        embeds = []
        async with ctx.typing():
            for gm in data.queue_stats:
                embed = discord.Embed(
                    colour=ctx.author.colour,
                    title="{} statistics for {}".format(gm.replace("_", " ").title(), profile),
                )
                for stat in data.queue_stats[gm]:
                    if stat == "playtime":
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=humanize_timedelta(seconds=data.queue_stats[gm][stat]),
                        )
                    else:
                        embed.add_field(
                            name=f"{stat.replace('_', ' ').title()}",
                            value=data.queue_stats[gm][stat],
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
