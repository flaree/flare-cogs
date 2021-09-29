import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Literal, Optional

import discord
from redbot.core import Config, commands
from redbot.core.commands.converter import TimedeltaConverter

log = logging.getLogger("red.flare.snipe")

CacheType = Literal["edit", "delete"]


class Snipe(commands.Cog):
    """Snipe the last message from a server."""

    __version__ = "0.2.1"

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
        self.delete_cache = defaultdict(dict)
        self.edit_cache = defaultdict(dict)
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

    def clear_cache(self, cache_type: CacheType):
        cache = getattr(self, f"{cache_type}_cache")
        to_delete = []
        for guild_id, channels in cache.items():
            for channel_id, cached_message in channels.items():
                if datetime.utcnow() - cached_message["timestamp"] > timedelta(
                    seconds=self.config_cache[guild_id]["timeout"]
                ):
                    to_delete.append([guild_id, channel_id])
        for guild_id, channel_id in to_delete:
            del cache[guild_id][channel_id]

    async def snipe_loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                self.clear_cache("delete")
                self.clear_cache("edit")
                await asyncio.sleep(await self.config.timer())
            except Exception as exc:
                log.error("Exception occured in snipe loop: ", exc_info=exc)
                break

    async def generate_cache(self):
        self.config_cache = await self.config.all_guilds()

    def add_delete_cache_entry(self, message: discord.Message):
        self.delete_cache[message.guild.id][message.channel.id] = {
            "content": message.content,
            "author": message.author.id,
            "timestamp": message.created_at,
        }

    def add_edit_cache_entry(self, before: discord.Message, after: discord.Message):
        self.edit_cache[after.guild.id][after.channel.id] = {
            "old_content": before.content,
            "new_content": after.content,
            "author": after.author.id,
            "timestamp": after.created_at,
        }

    def _listener_should_return(self, message: discord.Message) -> bool:
        guild = message.guild
        if not guild or message.author.bot:
            return True
        config = self.config_cache.get(guild.id)
        if not config:
            return True
        return not config["toggle"]

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if self._listener_should_return(message):
            return
        self.add_delete_cache_entry(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content:
            return
        if self._listener_should_return(after):
            return
        self.add_edit_cache_entry(before, after)

    @staticmethod
    async def reply(ctx: commands.Context, content: str = None, **kwargs) -> discord.Message:
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        kwargs["reference"] = ref
        return await ctx.send(content, **kwargs)

    async def get_snipe(
        self, snipe_type: CacheType, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        cache = getattr(self, f"{snipe_type}_cache")
        channel = channel or ctx.channel
        author_perms = channel.permissions_for(ctx.author)
        if not (author_perms.read_messages and author_perms.read_message_history):
            await self.reply(ctx, f"You don't have permission to read messages in {channel}.")
            return False

        guild: discord.Guild = ctx.guild
        if not await self.config.guild(guild).toggle():
            await self.reply(
                ctx,
                f"Sniping is not allowed in this server! An admin may turn it on by typing `{ctx.clean_prefix}snipeset enable true`.",
            )
            return False

        try:
            channelsnipe = cache[guild.id][channel.id]
        except KeyError:
            return
        if datetime.utcnow() - channelsnipe["timestamp"] > timedelta(
            seconds=await self.config.guild(guild).timeout()
        ):
            try:
                del cache[guild.id][channel.id]
            except KeyError:
                pass
            return
        try:
            del cache[guild.id][channel.id]
        except KeyError:
            pass
        return channelsnipe

    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def snipe(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Shows the last deleted message from a specified channel."""
        channelsnipe = await self.get_snipe("delete", ctx)
        if not channelsnipe:
            if channelsnipe is False:
                return
            await self.reply(ctx, "There's nothing to snipe!")
            return

        if not ctx.guild.chunked:
            await ctx.guild.chunk()
        author = ctx.guild.get_member(channelsnipe["author"])
        content = channelsnipe["content"]
        if content == "":
            description = (
                "No message content.\nThe deleted message may have been an image or an embed."
            )
        else:
            description = content

        embed = discord.Embed(
            description=description,
            timestamp=channelsnipe["timestamp"],
            color=ctx.author.color,
        )
        embed.set_footer(text=f"Sniped by: {ctx.author}")
        if author:
            embed.set_author(name=f"{author} ({author.id})", icon_url=author.avatar_url)
        else:
            embed.set_author(name="Removed Member")
        await self.reply(ctx, embed=embed)

    @staticmethod
    def get_content(content: str, limit: int = 1024):
        return content if len(content) <= limit else f"{content[:limit - 3]}..."

    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["esnipe"])
    async def editsnipe(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """Shows the last deleted message from a specified channel."""
        channelsnipe = await self.get_snipe("edit", ctx)
        if not channelsnipe:
            if channelsnipe is False:
                return
            await self.reply(ctx, "There's nothing to snipe!")
            return

        if not ctx.guild.chunked:
            await ctx.guild.chunk()
        author = ctx.guild.get_member(channelsnipe["author"])

        embed = discord.Embed(
            timestamp=channelsnipe["timestamp"],
            color=ctx.author.color,
        )
        old_content = self.get_content(channelsnipe["old_content"])
        new_content = self.get_content(channelsnipe["new_content"])
        embed.add_field(name="Old Content:", value=old_content)
        embed.add_field(name="New Content:", value=new_content)
        embed.set_footer(text=f"Sniped by: {str(ctx.author)}")
        if author is None:
            embed.set_author(name="Removed Member")
        else:
            embed.set_author(name=f"{author} ({author.id})", icon_url=author.avatar_url)
        await self.reply(ctx, embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def snipeset(self, ctx):
        """Group Command for Snipe Settings."""

    @snipeset.command()
    async def enable(self, ctx, state: bool):
        """Enable or disable sniping.

        State must be a bool or one of the following: True/False, On/Off, Y/N"""
        if state:
            await self.config.guild(ctx.guild).toggle.set(True)
            await self.reply(ctx, f"Sniping has been enabled in {ctx.guild}.")
        else:
            await self.config.guild(ctx.guild).toggle.set(False)
            await self.reply(ctx, f"Sniping has been disabled in {ctx.guild}.")
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
