from datetime import datetime
from io import BytesIO
from typing import Literal

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_timedelta
from redbot.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu, next_page, prev_page

from .converters import StrUser
from .funcs import account_matches, account_ongoing, account_stats, match_info


async def tokencheck(ctx):
    token = await ctx.bot.get_shared_api_tokens("faceit")
    return bool(token.get("authorization"))


controls = {
    "⬅": prev_page,
    "❌": close_menu,
    "➡": next_page,
    "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}": match_info,
}

profile_controls = {
    "\N{SPORTS MEDAL}": account_stats,
    "\N{CROSSED SWORDS}\N{VARIATION SELECTOR-16}": account_matches,
    "❌": close_menu,
}

profile_controls_ongoing = {
    "\N{SPORTS MEDAL}": account_stats,
    "\N{CROSSED SWORDS}\N{VARIATION SELECTOR-16}": account_matches,
    "\N{VIDEO GAME}": account_ongoing,
    "❌": close_menu,
}


class Faceit(commands.Cog):
    """CS:GO Faceit Statistics."""

    __version__ = "0.0.10"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.api = "https://open.faceit.com/data/v4"
        self._session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, 95932766180343808, force_registration=True)
        self.config.register_user(name=None)
        self.token = None

    async def red_get_data_for_user(self, *, user_id: int):
        name = await self.config.user_from_id(user_id).name()
        if name is None:
            return {}
        contents = f"Faceit Account for Discord user with ID {user_id}:\n- Name: {name}\n"
        return {"user_data.txt": BytesIO(contents.encode())}

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):

        await self.config.user_from_id(user_id).clear()

    def cog_unload(self):
        self.bot.loop.create_task(self._session.close())

    async def initalize(self):
        token = await self.bot.get_shared_api_tokens("faceit")
        self.token = token.get("authorization")

    async def get(self, url):
        async with self._session.get(
            self.api + url, headers={"authorization": "bearer {}".format(self.token)}
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status == 401:
                return {"error": "Authorization Failed - API Key may be invalid."}
            return await resp.json()

    async def get_ongoing(self, _id):
        async with self._session.get(
            "https://api.faceit.com/match/v1/matches/groupByState?userId=" + _id
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status == 401:
                return {"error": "Authorization Failed - API Key may be invalid."}
            return await resp.json()

    async def get_userid(self, username) -> str:
        userid = await self.get("/players?nickname={}".format(username))
        if userid.get("error"):
            return {"failed": userid.get("error")}
        if userid.get("errors"):
            return {"failed": userid.get("errors")[0]["message"]}
        else:
            return userid["player_id"]

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "faceit":
            self.token = api_tokens.get("authorization")

    async def get_user(self, ctx, user):
        if user is None:
            name = await self.config.user(ctx.author).name()
            if name is None:
                await ctx.send(
                    "You don't have a valid account linked, check {}faceit set.".format(ctx.prefix)
                )
                return False
        elif isinstance(user, discord.User):
            name = await self.config.user(user).name()
            if name is None:
                name = await self.get_userid(user.name)
                if isinstance(name, dict):
                    await ctx.send(name["failed"])
                    return False
        else:
            name = await self.get_userid(user)
            if isinstance(name, dict):
                await ctx.send(name["failed"])
                return False
        return name

    @commands.is_owner()
    @commands.command()
    async def faceitset(self, ctx):
        """Help on setting up faceit cog."""
        msg = (
            "How to setup the faceit cog.\n"
            "**1** - Visit https://developers.faceit.com and login or create a faceit account.\n"
            "**2** - Create an application at https://developers.faceit.com/apps\n"
            "**3** - Head over to the app you just created and click on the 'API KEYS' tab. Under this, click create then create a **SERVER SIDE** key.\n"
            "**4** - Use the following command with your key.\n{}set api faceit authorization <API_KEY_HERE>".format(
                ctx.prefix
            )
        )
        await ctx.maybe_send_embed(msg)

    @commands.group()
    @commands.check(tokencheck)
    async def faceit(self, ctx):
        """Faceit Commands."""

    @faceit.command(name="set")
    async def _set(self, ctx, *, name: str = None):
        """Set your faceit username."""
        if name is None:
            await self.config.user(ctx.author).name.set(name)
            await ctx.send("Your account link has been reset.")
            return
        uname = await self.get_userid(name)
        if isinstance(uname, dict):
            await ctx.send(uname["failed"])
            return
        await ctx.send(
            "Your account {} has been linked to the Faceit ID `{}`.".format(name, uname)
        )
        await self.config.user(ctx.author).name.set(uname)

    @faceit.command()
    async def profile(self, ctx, *, user: StrUser = None):
        """Faceit Profile Stats."""
        name = await self.get_user(ctx, user)
        if name is False:
            return
        profilestats = await self.get("/players/{}".format(name))
        if profilestats.get("error"):
            return await ctx.send(profilestats.get("error"))
        if profilestats.get("errors"):
            return await ctx.send(profilestats.get("errors")[0]["message"])
        ongoing = await self.is_ongoing(ctx, name, False)
        msg = "\nPress the \N{SPORTS MEDAL} button for the first game statistics.\nPress the \N{CROSSED SWORDS}\N{VARIATION SELECTOR-16} button for the most recent matches."
        if ongoing:
            msg += "\nPress the \N{VIDEO GAME}\N{VARIATION SELECTOR-16} button for information about the current ongoing match"
        embed = discord.Embed(
            color=ctx.author.color,
            title="Faceit Profile for {}".format(profilestats["nickname"]),
            description=msg,
            url=profilestats["faceit_url"].format(lang=profilestats["settings"]["language"]),
        )
        embed.set_thumbnail(url=profilestats["avatar"])
        accinfo = f"**Nickname**: {profilestats['nickname']}\n**Membership**: {profilestats['membership_type'].title()}"
        embed.add_field(name="Account Information", value=accinfo)
        steaminfo = f"**Steam Nickname**: {profilestats['steam_nickname']}\n**Steam ID 64**: {profilestats['steam_id_64']}\n**New Steam ID**: {profilestats['new_steam_id']}"
        embed.add_field(name="Steam Information", value=steaminfo)
        infractioninfo = f"**AFK(s)**: {profilestats['infractions']['afk']}\n**Leaves**: {profilestats['infractions']['leaver']}\n**Not Checked In**: {profilestats['infractions']['qm_not_checkedin']}\n**Not Voted**: {profilestats['infractions']['qm_not_voted']}"
        if profilestats["infractions"]["last_infraction_date"] != "":
            infractioninfo += f"\n**Last Infraction Date**: {profilestats['infractions']['last_infraction_date']}"
        embed.add_field(name="Infraction Information", value=infractioninfo)
        for game in profilestats["games"]:
            embed.add_field(
                name=game.title(),
                value=f"**Region**: {profilestats['games'][game]['region']}\n**Skill Level**: {profilestats['games'][game]['skill_level']}\n**ELO**: {profilestats['games'][game]['faceit_elo']}",
            )
        embed.set_author(name=profilestats["nickname"], icon_url=profilestats["avatar"])
        await menu(
            ctx, [embed], profile_controls if not ongoing else profile_controls_ongoing, timeout=30
        )

    @faceit.command()
    async def matches(self, ctx, *, user: StrUser = None):
        """Faceit Match Stats."""
        name = await self.get_user(ctx, user)
        if name is False:
            return
        profilestats = await self.get("/players/{}/history".format(name))
        if profilestats.get("error"):
            return await ctx.send(profilestats.get("error"))
        if profilestats.get("errors"):
            return await ctx.send(profilestats.get("errors")[0]["message"])
        embeds = []
        for i, game in enumerate(profilestats["items"], 1):
            teams = {
                "faction1": game["teams"]["faction1"]["nickname"],
                "faction2": game["teams"]["faction2"]["nickname"],
            }
            embed = discord.Embed(
                title=f"{game['competition_name']} - {teams['faction1']} vs {teams['faction2']}",
                description=f"Winner: **{teams[game['results']['winner']]}**\n[Match Room - Click Here]({game['faceit_url']})\n\nClick on the \N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} button below for more detailed statistics.",
                timestamp=datetime.fromtimestamp(game["started_at"]),
            )
            embed.add_field(name="Match ID", value=game["match_id"], inline=False)
            embed.set_footer(
                text=f"Game {i}/20 - Duration: {humanize_timedelta(seconds=game['finished_at'] - game['started_at'])}"
            )
            for team in teams:
                players = []
                for player in game["teams"][team]["players"]:
                    players.append(
                        f"[{player['nickname']}]({player['faceit_url'].format(lang='en')})"
                    )
                embed.add_field(name=f"{teams[team]} Players", value="\n".join(players))

            embeds.append(embed)
        if embeds:
            await menu(ctx, embeds, controls, timeout=30)
        else:
            await ctx.send("No information for previous matches found.")

    @faceit.command()
    async def match(self, ctx, match_id):
        """In-depth stats for a match."""
        match = await self.get("/matches/{}/stats".format(match_id))
        if match.get("error"):
            return await ctx.send(match.get("error"))
        if match.get("errors"):
            return await ctx.send(match.get("errors")[0]["message"])
        match = match["rounds"]
        embeds = []
        teams = {
            match[0]["teams"][0]["team_id"]: match[0]["teams"][0]["team_stats"]["Team"],
            match[0]["teams"][1]["team_id"]: match[0]["teams"][1]["team_stats"]["Team"],
        }
        embed = discord.Embed(
            title=" vs ".join(teams.values()) + " Statistics",
            description=f"**Winner**: {teams[match[0]['round_stats']['Winner']]}\n**Map**: {match[0]['round_stats']['Map']}\n**Score**: {match[0]['round_stats']['Score']}",
        )
        team1, team2 = [team for team in teams.values()]
        team1stats = sorted(match[0]["teams"][0]["team_stats"].items())
        team2stats = sorted(match[0]["teams"][1]["team_stats"].items())
        embed.add_field(
            name=f"{team1} Team Stats",
            value="\n".join([f"**{item[0]}**: {item[1]}" for item in team1stats]),
        )
        embed.add_field(
            name=f"{team2} Team Stats",
            value="\n".join([f"**{item[0]}**: {item[1]}" for item in team2stats]),
        )
        embed.set_footer(text="Page 1/3")
        embeds.append(embed)

        for i, team in enumerate(match[0]["teams"], 2):
            embed = discord.Embed(title=team["team_stats"]["Team"] + " Player Statistics")
            for player in team["players"]:
                playerstats = sorted(player["player_stats"].items())
                embed.add_field(
                    name=player["nickname"],
                    value="\n".join([f"**{item[0]}**: {item[1]}" for item in playerstats]),
                )
            embed.add_field(name="\u200b", value="\u200b")
            embed.set_footer(text=f"Page {i}/3")
            embeds.append(embed)
        if embeds:
            await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=60)
        else:
            await ctx.send("No information for match found.")

    @faceit.command()
    async def stats(self, ctx, game, *, user: StrUser = None):
        """In-depth stats for any faceit supported game."""
        name = await self.get_user(ctx, user)
        if name is False:
            return
        stats = await self.get("/players/{}/stats/{}".format(name, game))
        if stats.get("error"):
            return await ctx.send(stats.get("error"))
        if stats.get("errors"):
            return await ctx.send(stats.get("errors")[0]["message"])
        embeds = []
        if stats["lifetime"]["Recent Results"] is not None:
            recent_results = [
                ("W" if bool(int(game)) else "L")
                for game in stats["lifetime"]["Recent Results"]
                if game is not None
            ]
            msg = "**Recent Results**: " + " ".join(recent_results) + "\n"
        else:
            msg = "**Recent Results**: N/A"
        msg += "\n".join(
            [
                f"**{item[0]}**: {item[1]}"
                for item in sorted(stats["lifetime"].items())
                if item[0] != "Recent Results"
            ]
        )
        embed = discord.Embed(title=f"{game.title()} stats for {name}", description=msg)
        embed.set_footer(text=f"Page 1/{len(stats['segments']) + 1}")
        embeds.append(embed)
        for i, segment in enumerate(stats["segments"], 2):
            embed = discord.Embed(
                title=f"{segment['label']} statistics",
                description="\n".join(
                    [f"**{item[0]}**: {item[1]}" for item in sorted(segment["stats"].items())]
                ),
            )
            embed.set_thumbnail(url=segment["img_regular"])
            embed.set_footer(text=f"Page {i}/{len(stats['segments']) + 1}")
            embeds.append(embed)
        if embeds:
            await menu(ctx, embeds, DEFAULT_CONTROLS, timeout=30)
        else:
            await ctx.send("No information found.")

    @faceit.command()
    async def ongoing(self, ctx, *, user: StrUser = None):
        """Check if a user has an ongoing game."""
        name = await self.get_user(ctx, user)
        if name is False:
            return
        ongoing = await self.is_ongoing(ctx, name)
        if ongoing is False:
            return
        ongoing = ongoing[0]
        team1, team2 = ongoing["teams"]["faction1"], ongoing["teams"]["faction2"]
        embed = discord.Embed(
            title=f"{team1['name']} vs {team2['name']}",
            timestamp=datetime.strptime(ongoing["createdAt"], "%Y-%m-%dT%H:%M:%S%z"),
        )
        embed.set_author(name=f"Ongoing {ongoing['entity']['name']}")
        embed.set_footer(text="Started:")
        embed.add_field(
            name=f"{team1['name']} Roster",
            value="\n".join([player["nickname"] for player in team1["roster"]]),
        )
        embed.add_field(
            name=f"{team2['name']} Roster",
            value="\n".join([player["nickname"] for player in team2["roster"]]),
        )
        await ctx.send(embed=embed)

    async def is_ongoing(self, ctx, name, messages=True):
        stats = await self.get_ongoing(name)
        if stats.get("error"):
            if messages:
                await ctx.send(stats.get("error"))
            return False
        if stats.get("errors"):
            if messages:
                await ctx.send(stats.get("errors")[0]["message"])
            return False
        ongoing = stats["payload"].get("ONGOING")
        if ongoing is None:
            if messages:
                await ctx.send("No ongoing game available.")
            return False
        return ongoing
