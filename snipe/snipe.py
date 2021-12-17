import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import discord
from redbot.core import Config, commands
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.menus import DEFAULT_CONTROLS

from .menus import menu

log = logging.getLogger("red.flare.snipe")

CacheType = Literal["edit", "delete"]


class Snipe(commands.Cog):
    """Snipe the last message from a server."""

    __version__ = "0.3.0"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        defaults_guild = {"toggle": False, "timeout": 30, "max": 1}
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
        for guild_id, channels in cache.items():
            for _, queue in channels.items():
                i = sum(
                    (
                        datetime.now(tz=timezone.utc) - message["timestamp"]
                    ).total_seconds()
                    > self.config_cache[guild_id]["timeout"]
                    for message in queue
                )

                if i > 0:
                    for _ in range(i):
                        try:
                            queue.popleft()
                        except IndexError:
                            pass

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
        if self.delete_cache[message.guild.id].get(message.channel.id) is None:
            self.delete_cache[message.guild.id][message.channel.id] = deque(
                maxlen=self.config_cache[message.guild.id].get("max", 1)
            )
        self.delete_cache[message.guild.id][message.channel.id].append(
            {
                "content": message.content,
                "author": message.author.id,
                "timestamp": datetime.now(tz=timezone.utc),
            }
        )

    def add_edit_cache_entry(self, before: discord.Message, after: discord.Message):
        if self.edit_cache[after.guild.id].get(after.channel.id) is None:
            self.edit_cache[after.guild.id][after.channel.id] = deque(
                maxlen=self.config_cache[after.guild.id].get("max", 1)
            )
        self.edit_cache[after.guild.id][after.channel.id].append(
            {
                "old_content": before.content,
                "new_content": after.content,
                "author": after.author.id,
                "timestamp": datetime.now(tz=timezone.utc),
            }
        )

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
    async def reply(
        ctx: commands.Context, content: str = None, embeds: list = None, **kwargs
    ) -> discord.Message:
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        kwargs["reference"] = ref
        if content is not None:
            return await ctx.send(content, **kwargs)
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0], **kwargs)
        return await menu(ctx, embeds, DEFAULT_CONTROLS, **kwargs)

    async def get_snipe(
        self,
        snipe_type: CacheType,
        ctx: commands.Context,
        channel: discord.TextChannel = None,
        amount: int = 1,
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
        snipes = []
        for _ in range(amount):
            try:
                snipe = cache[guild.id][channel.id].pop()
                if datetime.now(tz=timezone.utc) - snipe["timestamp"] > timedelta(
                    seconds=await self.config.guild(guild).timeout()
                ):
                    continue
                snipes.append(snipe)
            except (IndexError, KeyError):
                return snipes
        if not snipes:
            return
        return snipes

    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def snipe(
        self,
        ctx: commands.Context,
        amount: Optional[int] = 1,
        channel: Optional[discord.TextChannel] = None,
    ):
        """Shows the last deleted message from a specified channel."""
        channelsnipes = await self.get_snipe("delete", ctx, channel=channel, amount=amount)
        if not channelsnipes:
            if channelsnipes is False:
                return
            await self.reply(ctx, "There's nothing to snipe!")
            return

        if not ctx.guild.chunked:
            await ctx.guild.chunk()
        embeds = []
        for snipe in channelsnipes:
            author = ctx.guild.get_member(snipe["author"])
            content = snipe["content"]
            if content == "":
                description = (
                    "No message content.\nThe deleted message may have been an image or an embed."
                )
            else:
                description = content

            embed = discord.Embed(
                description=description,
                timestamp=snipe["timestamp"],
                color=ctx.author.color,
            )
            embed.set_footer(text=f"Sniped by: {ctx.author}")
            if author:
                embed.set_author(name=f"{author} ({author.id})", icon_url=author.avatar_url)
            else:
                embed.set_author(name="Removed Member")
            embeds.append(embed)
        await self.reply(ctx, embeds=embeds)

    @staticmethod
    def get_content(content: str, limit: int = 1024):
        return content if len(content) <= limit else f"{content[:limit - 3]}..."

    @commands.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.channel)
    @commands.bot_has_permissions(embed_links=True)
    @commands.command(aliases=["esnipe"])
    async def editsnipe(
        self,
        ctx: commands.Context,
        amount: Optional[int] = 1,
        channel: Optional[discord.TextChannel] = None,
    ):
        """Shows the last deleted message from a specified channel."""
        channelsnipes = await self.get_snipe("edit", ctx, channel=channel, amount=amount)
        if not channelsnipes:
            if channelsnipes is False:
                return
            await self.reply(ctx, "There's nothing to snipe!")
            return

        if not ctx.guild.chunked:
            await ctx.guild.chunk()
        embeds = []
        for snipe in channelsnipes:
            author = ctx.guild.get_member(snipe["author"])

            embed = discord.Embed(
                timestamp=snipe["timestamp"],
                color=ctx.author.color,
            )
            old_content = self.get_content(snipe["old_content"])
            new_content = self.get_content(snipe["new_content"])
            embed.add_field(name="Old Content:", value=old_content)
            embed.add_field(name="New Content:", value=new_content)
            embed.set_footer(text=f'Sniped by: {ctx.author}')
            if author is None:
                embed.set_author(name="Removed Member")
            else:
                embed.set_author(name=f"{author} ({author.id})", icon_url=author.avatar_url)
            embeds.append(embed)
        await self.reply(ctx, embeds=embeds)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def snipeset(self, ctx: commands.Context):
        """Group Command for Snipe Settings."""

    @snipeset.command()
    async def enable(self, ctx: commands.Context, state: bool):
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
        ctx: commands.Context,
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

    @snipeset.command(name="max")
    async def _max(self, ctx: commands.Context, amount: int):
        """Set the max amount of snipes to store per channel."""
        if amount < 1 or amount > 10:
            await self.reply(ctx, "The max amount must be between 1 and 10.")
            return
        await self.config.guild(ctx.guild).max.set(amount)
        self.edit_cache[ctx.guild.id][ctx.channel.id] = deque(maxlen=amount)
        self.delete_cache[ctx.guild.id][ctx.channel.id] = deque(maxlen=amount)
        await ctx.tick()

    @snipeset.command()
    @commands.is_owner()
    async def deletetime(
        self,
        ctx: commands.Context,
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
