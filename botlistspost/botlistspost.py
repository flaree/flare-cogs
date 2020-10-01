import asyncio
import contextlib
import json
import logging
from typing import Dict

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

BOTBLOCK = "https://botblock.org/api"
BSDC = "https://api.server-discord.com/v2/bots/{BOTID}/stats"

log = logging.getLogger("red.flare.botlistpost")


class BotListsPost(commands.Cog):
    """Post data to bot lists. For DBL use Predas cog"""

    __version__ = "0.0.6"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(lists={}, version=1)
        self._session = aiohttp.ClientSession()
        self.bsdctoken = None
        self.post_stats_task = self.bot.loop.create_task(self.post_stats())

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    async def init(self):
        sd = await self.bot.get_shared_api_tokens("serverdiscord")
        self.bsdctoken = sd.get("authorization")
        if await self.config.version() < 2:
            await self.bot.send_to_owners(
                "Hi, the current cog has been redesigned to use bot block. If you dont wish to use this to manage more lists and save me time then feel free to uninstall. Current setup sites will no longer work (except server-discord) and will need to be readded."
            )
            await self.config.version.set(2)

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "serverdiscord":
            self.bsdctoken = {"Authorization": api_tokens.get("authorization")}

    def cog_unload(self):
        self.bot.loop.create_task(self._session.close())
        if self.post_stats_task:
            self.post_stats_task.cancel()

    async def post_stats(self):
        await self.bot.wait_until_ready()
        await self.init()
        botid = str(self.bot.user.id)
        while True:
            success = []
            failed = []
            serverc = len(self.bot.guilds)
            shardc = self.bot.shard_count
            conf = await self.config.lists()
            if conf:
                conf["server_count"] = serverc
                conf["shard_count"] = shardc
                conf["bot_id"] = botid

                async with self._session.post(
                    BOTBLOCK + "/count",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(conf),
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data.get("success"):
                            success = list(data["success"].keys())
                        if data.get("failure"):
                            for _list in data["failure"]:
                                failed.append(f"{_list} ({data['failure'][_list][0]})")
                    else:
                        print(await r.json())
                        failed.append(f"BotBlock ({r.status})")

            if self.bsdctoken is not None:
                async with self._session.post(
                    BSDC.format(BOTID=botid),
                    headers={"Authorization": f"SDC {self.bsdctoken}"},
                    data={"servers": serverc, "guilds": shardc},
                ) as resp:
                    resp = await resp.json()
                    if resp.get("status"):
                        success.append("Server-Discord bot list")
                    else:
                        failed.append(f"Server-Discord bot list ({resp.get('error')})")
            if failed:
                log.info(f"Unable to post data to {humanize_list(failed)}.")
            if success:
                log.info(f"Successfully posted servercount to {humanize_list(success)}.")
            await asyncio.sleep(1800)

    async def get_lists(self) -> Dict:
        async with self._session.get(BOTBLOCK + "/lists") as r:
            if r.status == 200:
                return await r.json()
            return {"error": r.status}

    @commands.is_owner()
    @commands.command()
    async def botlistpost(self, ctx):
        """Setup for botlistposting"""
        msg = (
            "This cog currently supports every bot list on [BotBlock](https://botblock.org) along with"
            " [Server-Discord](https://docs.server-discord.com/)."
            "To set this cog up for Server-Discord, please use the following command:\n"
            f"`{ctx.clean_prefix}set api serverdiscord authorization <SDC token>`\n"
            f"Otherwise, you need to type `{ctx.clean_prefix}botlist add <bot list> <token>`\n"
            f"You can find a list of allowed lists via `{ctx.clean_prefix}botlist list`"
        )
        await ctx.maybe_send_embed(msg)

    @commands.is_owner()
    @commands.group()
    async def botlist(self, ctx):
        """Bot list posting setup"""

    @botlist.command(name="list")
    async def _list(self, ctx):
        """Return all available botlists."""
        lists = await self.get_lists()
        if lists.get("error"):
            return await ctx.send(
                f"An error occured retrieving the lists. Error Code: {lists['error']}"
            )
        msg = ""
        for _list in lists:
            msg += f"[{_list}]({lists[_list]['url']})\n"
        embeds = []
        for page in pagify(msg, page_length=1024):
            embed = discord.Embed(
                title="Bot Lists", description=page, colour=await ctx.embed_colour()
            )
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @botlist.command(name="add")
    async def _add(self, ctx, site: str, *, token: str):
        """Add a botlist to post stats to."""
        with contextlib.suppress(discord.NotFound):
            await ctx.message.delete()
        lists = await self.get_lists()
        if lists.get("error"):
            return await ctx.send(
                f"An error occured retrieving the lists. Error Code: {lists['error']}"
            )
        if site not in lists:
            return await ctx.send(
                f"Your list doesn't appear to exist. Ensure its named after how it appears in `{ctx.cleanprefix}botlist list`"
            )
        async with self.config.lists() as config:
            if site in config:
                config[site] = token
                await ctx.send(f"{site} token has been updated.")
            else:
                config[site] = token
                await ctx.send(f"{site} has been added to the list.")

    @botlist.command(name="delete")
    async def _delete(self, ctx, site: str):
        """Remove a botlist from your setup lists.."""
        lists = await self.get_lists()
        if lists.get("error"):
            return await ctx.send(
                f"An error occured retrieving the lists. Error Code: {lists['error']}"
            )
        if site not in lists:
            return await ctx.send(
                f"Your list doesn't appear to exist. Ensure its named after how it appears in `{ctx.cleanprefix}botlist list`"
            )
        async with self.config.lists() as config:
            if site in config:
                del config[site]
                await ctx.send(f"{site} has been removed")
            else:
                await ctx.send(f"{site} doesnt exist in your setup bot lists.")

    @botlist.command()
    async def available(self, ctx):
        """List current setup botlists which are having stats posted to them."""
        conf = await self.config.lists()
        if not conf:
            return await ctx.send("You don't have any lists setup.")
        msg = ""
        for _list in conf:
            msg += f"{_list}\n"
        embeds = []
        for page in pagify(msg, page_length=1024):
            embed = discord.Embed(
                title="Bot Lists Setup", description=page, colour=await ctx.embed_colour()
            )
            embeds.append(embed)
        await menu(ctx, embeds, DEFAULT_CONTROLS)
