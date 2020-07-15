import asyncio
import json
import logging

import aiohttp
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list

DBLEL = "https://api.discordextremelist.xyz/v2/bot/{BOTID}/stats"
BFD = "https://botsfordiscord.com/api/bot/{BOTID}"

log = logging.getLogger(("red.flare.botlistpost"))


class BotListsPost(commands.Cog):
    """Post data to bot lists. For DBL use Predas cog"""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self._session = aiohttp.ClientSession(loop=self.bot.loop)
        self.dbleltoken = None
        self.bfdtoken = None
        self.post_stats_task = self.bot.loop.create_task(self.post_stats())

    async def init(self):
        bfd = await self.bot.get_shared_api_tokens("botsfordiscord")
        self.bfdtoken = bfd.get("authorization")
        dblel = await self.bot.get_shared_api_tokens("discordextremelist")
        self.dbleltoken = dblel.get("authorization")

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "botsfordiscord":
            self.bfdtoken = {"Authorization": api_tokens.get("authorization")}
        if service_name == "discordextremelist":
            self.dbleltoken = {"Authorization": api_tokens.get("authorization")}

    def cog_unload(self):
        self.bot.loop.create_task(self._session.close())
        if self.post_stats_task:
            self.post_stats_task.cancel()

    async def post_stats(self):
        await self.bot.wait_until_ready()
        await self.init()
        while True:
            success = []
            serverc = len(self.bot.guilds)
            if self.dbleltoken is not None:
                async with self._session.post(
                    DBLEL.format(BOTID=self.bot.user.id),
                    headers={"Authorization": self.dbleltoken, "Content-Type": "application/json"},
                    data=json.dumps({"guildCount": serverc, "shardCount": self.bot.shard_count}),
                ) as resp:
                    if resp.status == 200:
                        success.append("Discord Extreme List")

            if self.bfdtoken is not None:
                async with self._session.post(
                    BFD.format(BOTID=self.bot.user.id),
                    headers={"Authorization": self.bfdtoken, "Content-Type": "application/json"},
                    data=json.dumps({"server_count": serverc}),
                ) as resp:
                    if resp.status == 200:
                        success.append("Bots for Discord")
            if not success:
                log.info("Unable to post data to any botlist.")
            else:
                log.info(f"Successfully posted servercount to {humanize_list(success)}.")
            await asyncio.sleep(1800)

    @commands.command()
    async def botlistpost(self, ctx):
        """Setup for botlistposting"""
        msg = (
            "This cog currently supports Bots for Discord and Discord Extreme List.\n"
            "To set this cog up, please use the following commands:\n"
            "`{PREFIX}set api botsfordiscord authorization <botsfordiscord apikey>`\n`{PREFIX}set api discordextremelist authorization <discordextremelist apikey>`".format(
                PREFIX=ctx.clean_prefix
            )
        )
        await ctx.maybe_send_embed(msg)
