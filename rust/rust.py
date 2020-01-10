import typing
from functools import partial

import aiohttp
import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from valve.steam.api import interface

from .steam import SteamUser


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


BASE_URL = "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?appid=252490&key={steamkey}&steamid={steamid}"


async def tokencheck(ctx):
    try:
        token = await ctx.bot.db.api_tokens.get_raw("steam", default={"web": None})
    except AttributeError:
        token = await ctx.bot.get_shared_api_tokens("steam")
    if token.get("web") is not None:
        return True
    else:
        await ctx.send("Your steam API key has not been set.")
        return False


class Rust(commands.Cog):
    """Rust Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        defaults = {"id": None}
        self.config.register_user(**defaults)

    def cog_unload(self):
        self.session.detach()

    async def initalize(self):
        try:
            self.apikeys = await self.bot.db.api_tokens.get_raw("steam", default={"web": None})
        except AttributeError:
            self.apikeys = await self.bot.get_shared_api_tokens("steam")
        self.steam = await self.bot.loop.run_in_executor(
            None, partial(interface.API, key=self.apikeys["web"])
        )

    async def get_stats(self, id):
        async with self.session.get(
            BASE_URL.format(steamkey=self.apikeys.get("web"), steamid=id)
        ) as request:
            try:
                return await request.json()
            except:
                return None

    @commands.command()
    async def rustset(self, ctx, name: str):
        """Set your rust steam acc"""
        await self.config.user(ctx.author).id.set(name)
        await ctx.tick()

    @commands.check(tokencheck)
    @commands.command()
    async def rust(self, ctx, *, profile: typing.Union[discord.Member, str] = None):
        if profile is None:
            profile = ctx.author
        if isinstance(profile, discord.Member):
            profile = await self.config.user(profile).id()
            if profile is None:
                return await ctx.send("User hasn't set a profile yet.")
        try:
            profile = await SteamUser.convert(ctx, profile)
        except:
            return await ctx.send(
                "Error converting your name to a SteamID. Use your SteamIDs to be more precise.\n<https://steamid.io/lookup/>"
            )
        data = await self.get_stats(profile.steamid64)
        if data is None:
            return await ctx.send(
                "No stats available, profile may be private. If not, use your steam64ID. \n<https://steamid.io/lookup/>"
            )
        embed = discord.Embed(
            color=discord.Color.red(), title="Rust Stats for {}".format(profile.personaname)
        )
        embed.set_thumbnail(url=profile.avatar184)
        playerstats = data.get("playerstats")
        if playerstats is None:
            return await ctx.send("No stats returned, ensure you specified the right account.")
        stats = {}
        for stat in playerstats["stats"]:
            stats[stat["name"]] = stat["value"]
        killstats = "**Player Kills**: {}\n**Deaths**: {}\n**Suicides**: {}\n**Headshots**: {}".format(
            stats.get("kill_player", 0),
            stats.get("deaths", 0),
            stats.get("death_suicide", 0),
            stats.get("headshot", 0),
        )
        killstatsnpc = "**Bear Kills**: {}\n**Boar Kills**: {}\n**Chicken Kills**: {}\n**Horse Kills**: {}".format(
            stats.get("kill_bear", 0),
            stats.get("kill_boar", 0),
            stats.get("kill_chicken",),
            stats.get("kill_horse", 0),
        )
        harveststats = "**Wood Harvested**: {}\n**Cloth Harvested**: {}\n**Stone Harvested**: {}\n**Leather Harvested**: {}\n**Scrap Harvested**: {}\n**Metal Ore Aquired**: {}\n**LGF Aquired**: {}".format(
            stats.get("harvested_wood", 0),
            stats.get("harvested_cloth", 0),
            stats.get("harvested_stones", 0),
            stats.get("harvested_leather", 0),
            stats.get("acquired_scrap", 0),
            stats.get("acquired_metal.ore", 0),
            stats.get("acquired_lowgradefuel", 0),
        )
        deathstats = f"**Deaths**: {stats.get('deaths', 0)}\n**Suicides**: {stats.get('death_suicide', 0)}\n**Death by Fall**: {stats.get('death_fall', 0)}\n**Death by Entity**: {stats.get('death_entity', 0)}\n**Death by Bear**: {stats.get('death_bear', 0)}"
        bulletstats = f"**Bullets Fired**: {stats.get('bullet_fired', 0)}\n**Bullets Hit (Player)**: {stats.get('bullet_hit_player', 0)}\n**Bullets Hit (Entity)**: {stats.get('bullet_hit_entity', 0)}\n**Bullets Hit (Building)**: {stats.get('bullet_hit_building', 0)}"
        arrowstats = f"**Arrows Shot**: {stats.get('arrow_fired', 0)}\n**Arrows Hit (Player)**: {stats.get('arrow_hit_player', 0)}\n**Arrows Hit (Entity)**: {stats.get('arrow_hit_entity', 0)}\n**Arrows Hit (Building)**: {stats.get('arrow_hit_building', 0)}"
        shotgunstats = f"**Shotgun Shots**: {stats.get('shotgun_fired', 0)}\n**Shotgun Hits (Player)**: {stats.get('shotgun_hit_player', 0)}\n**Shotgun Hits (Entity)**: {stats.get('shotgun_hit_entity', 0)}\n**Shotguns Hits (Building)**: {stats.get('shotgun_hit_entity', 0)}"
        miscstats = f"**Items Dropped**: {stats.get('item_drop', 0)}\n**Wounded**: {stats.get('wounded', 0)}\n**Wounded Assisted**: {stats.get('wounded_assisted', 0)}\n**Wounded Healed**: {stats.get('wounded_healed', 0)}\n**Inventory Opened**: {stats.get('INVENTORY_OPENED', 0)}\n**Crafting Opened**: {stats.get('CRAFTING_OPENED', 0)}\n**Map Opened**: {stats.get('MAP_OPENED', 0)}"
        embed.add_field(name="General Statistics", value=killstats)
        embed.add_field(name="Kill Statistics NPC", value=killstatsnpc)
        embed.add_field(name="Death Statistics", value=deathstats)
        embed.add_field(name="Bullet Statistics", value=bulletstats)
        embed.add_field(name="Arrow Statistics", value=arrowstats)
        embed.add_field(name="Shotgun Statistics", value=shotgunstats)
        embed.add_field(name="Harvest Statistics", value=harveststats)
        embed.add_field(name="Misc Statistics", value=miscstats)

        await ctx.send(embed=embed)

    @commands.check(tokencheck)
    @commands.command()
    async def rustachievements(
        self, ctx, *, profile: typing.Union[discord.Member, SteamUser] = None
    ):
        if profile is None:
            profile = ctx.author
        if isinstance(profile, discord.Member):
            profile = await self.config.user(profile).id()
            if profile is None:
                return await ctx.send("User hasn't set a profile yet.")
        try:
            profile = await SteamUser.convert(ctx, profile)
        except:
            return await ctx.send("Error converting.")
        data = await self.get_stats(profile.steamid64)
        if data is None:
            return await ctx.send(
                "No stats available, profile may be private. If not, use your steam64ID."
            )
        embeds = []
        chunk = chunks(data["playerstats"]["achievements"], 15)
        for achivements in chunk:
            msg = ""
            for achivement in achivements:
                msg += "**{}** - Achieved\n".format(achivement["name"].replace("_", " ").title())
            embed = discord.Embed(
                color=discord.Color.red(),
                title="Rust Achievements for {}".format(profile.personaname),
                description=msg,
            )
            embed.set_thumbnail(url=profile.avatar184)
            embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
