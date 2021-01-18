import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import discord
from redbot.core import Config, checks, commands
from redbot.core.commands.converter import TimedeltaConverter

log = logging.getLogger("red.flare.snipe")


class Snipe(commands.Cog):
    """Snipe the last message from a server."""

    __version__ = "0.1.0"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        defaults_guild = {"toggle": False, "timeout": 30}
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_guild(**defaults_guild)
        self.config.register_global(timer=60)
        self.bot = bot
        self.cache = {}
        self.snipe_loop_task: Optional[asyncio.Task] = None

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    async def init(self):
        self.snipe_loop_task = self.bot.loop.create_task(self.snipe_loop())
        await self.generate_cache()

    def cog_unload(self):
        if self.snipe_loop_task:
            self.snipe_loop_task.cancel()

    async def snipe_loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                to_delete = []
                for guild in self.cache:
                    for channel in self.cache[guild]:
                        if datetime.utcnow() - self.cache[guild][channel]["timestamp"] > timedelta(
                            seconds=self.config_cache[guild]["timeout"]
                        ):
                            to_delete.append([guild, channel])
                for entry in to_delete:
                    del self.cache[entry[0]][entry[1]]
                await asyncio.sleep(await self.config.timer())
            except Exception as exc:
                log.error("Exception occured in snipe loop: ", exc_info=exc)
                break

    async def generate_cache(self):
        self.config_cache = await self.config.all_guilds()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        guild_id = payload.guild_id
        if guild_id is None:
            return
        config = self.config_cache.get(guild_id)
        if not config:
            return
        if not config["toggle"]:
            return
        message = payload.cached_message
        if message is None:
            log.debug(
                f"Message {payload.message_id} not found in the cache, not adding to snipe cache. Guild ID: {guild_id} | Channel ID: {payload.channel_id}"
            )
            return
        if message.author.bot:
            return
        self.add_cache_entry(message, guild_id, payload.channel_id)

    def add_cache_entry(self, message, guild, channel):
        if guild not in self.cache:
            self.cache[guild] = {}
        self.cache[guild][channel] = {
            "content": message.content,
            "author": message.author.id,
            "timestamp": message.created_at,
        }

    @commands.cooldown(rate=1, per=5, type=commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def snipe(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Shows the last deleted message from a specified channel."""
        channel = channel or ctx.channel
        if not await self.config.guild(ctx.guild).toggle():
            await ctx.send(
                f"Sniping is not allowed in this server! An admin may turn it on by typing the `{ctx.clean_prefix}snipeset enable` command."
            )
            return
        guildcache = self.cache.get(ctx.guild.id, None)
        if guildcache is None:
            await ctx.send("There's nothing to snipe!")
            return
        channelsnipe = guildcache.get(channel.id, None)
        if channelsnipe is None:
            await ctx.send("There's nothing to snipe!")
            return
        if datetime.utcnow() - channelsnipe["timestamp"] > timedelta(
            seconds=await self.config.guild(ctx.guild).timeout()
        ):
            del self.cache[ctx.guild.id][channel.id]
            await ctx.send("There's nothing to snipe!")
            return
        del self.cache[ctx.guild.id][channel.id]
        author = ctx.guild.get_member(channelsnipe["author"])
        if not channelsnipe["content"]:
            embed = discord.Embed(
                description="No message content.\nThe deleted message may have been an image or an embed.",
                timestamp=channelsnipe["timestamp"],
                color=ctx.author.color,
            )
        else:
            embed = discord.Embed(
                description=channelsnipe["content"],
                timestamp=channelsnipe["timestamp"],
                color=ctx.author.color,
            )
        embed.set_footer(text=f"Sniped by: {str(ctx.author)}")
        if author is None:
            embed.set_author(name="Removed Member")
        else:
            embed.set_author(name=f"{author} ({author.id})", icon_url=author.avatar_url)
        await ctx.send(embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group()
    async def snipeset(self, ctx):
        """Group Command for Snipe Settings."""

    @snipeset.command()
    async def enable(self, ctx, state: bool):
        """Enable or disable sniping.

        State must be a bool or one of the following: True/False, On/Off, Y/N"""
        if state:
            await self.config.guild(ctx.guild).toggle.set(True)
            await ctx.send(f"Sniping has been enabled in {ctx.guild}.")
        else:
            await self.config.guild(ctx.guild).toggle.set(False)
            await ctx.send(f"Sniping has been disabled in {ctx.guild}.")
        await self.generate_cache()

    @snipeset.command()
    async def time(
        self,
        ctx,
        *,
        time: TimedeltaConverter(
            minimum=timedelta(),
            maximum=timedelta(minutes=60),
            default_unit="seconds",
            allowed_units=["seconds", "minutes"],
        ),
    ):
        """
        Set the time before snipes expire.

        Takes seconds or minutes, use the whole unit name with the amount.
        Defaults to seconds if no unit name used.
        """
        duration = time.total_seconds()
        await self.config.guild(ctx.guild).timeout.set(duration)
        await ctx.tick()
        await self.generate_cache()

    @snipeset.command()
    @commands.is_owner()
    async def deletetime(
        self,
        ctx,
        *,
        time: TimedeltaConverter(
            minimum=timedelta(),
            maximum=timedelta(minutes=60),
            default_unit="seconds",
            allowed_units=["seconds", "minutes"],
        ),
    ):
        """
        Set the time for snipes to be removed automatically.

        Takes seconds or minutes, use the whole unit name with the amount.
        Defaults to seconds if no unit name used.
        """
        duration = time.total_seconds()
        await self.config.timer.set(duration)
        await ctx.tick()
