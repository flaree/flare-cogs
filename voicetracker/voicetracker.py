import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from math import ceil

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_timedelta, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

log = logging.getLogger("red.flare.voicetracker")


class VoiceTracker(commands.Cog):

    __version__ = "0.0.2"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nCog Author: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.tracking = {}
        self.config = Config.get_conf(self, identifier=95932766180343808)
        default_guild = {"voice_channels": {}, "enabled": False, "tracking": []}
        default_member = {"enabled": False}
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.config_guild_cache = {}
        self.config_member_cache = {}
        self.update_cache_dict = defaultdict(dict)
        self.bg_loop_task = asyncio.create_task(self.init())

    async def init(self):
        await self.bot.wait_until_ready()
        await self.update_cache()
        while True:
            try:
                await self.save_config()
                await asyncio.sleep(60)
            except Exception as exc:
                log.error("Exception in bg_loop: ", exc_info=exc)
                self.bg_loop_task.cancel()

    def cog_unload(self):
        asyncio.create_task(self.save_config())
        self.bg_loop_task.cancel()

    async def update_cache(self):
        self.config_guild_cache = await self.config.all_guilds()
        self.config_member_cache = await self.config.all_members()

    async def save_config(self):
        for server, data in self.update_cache_dict.items():
            async with self.config.guild_from_id(server).voice_channels() as voice_channels:
                for channel in data:
                    if channel not in voice_channels:
                        voice_channels[channel] = data[channel]
                    else:
                        for user, time in data[channel].items():
                            if user in voice_channels[channel]:
                                voice_channels[channel][user] += time
                            else:
                                voice_channels[channel] = {user: time}
                        self.update_cache_dict[server][channel] = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        channel = after.channel or before.channel
        if (
            self.config_guild_cache.get(member.guild.id, {}).get("enabled", False) is False
            or channel.id
            not in self.config_guild_cache.get(member.guild.id, {}).get("tracking", [])
        ) and (
            self.config_member_cache.get(member.guild.id, {})
            .get(member.id, {})
            .get("enabled", False)
            is False
        ):
            return
        if before.channel is None and after.channel is not None:
            self.tracking[member.id] = {
                "channel": after.channel.id,
                "time": datetime.now(tz=timezone.utc),
            }
        elif before.channel is not None and after.channel is None:
            if member.id in self.tracking:
                time = datetime.now(tz=timezone.utc) - self.tracking[member.id]["time"]
                seconds = time.total_seconds()
                if (
                    self.update_cache_dict[member.guild.id]
                    .get(before.channel.id, {})
                    .get(member.id)
                    is None
                ):
                    self.update_cache_dict[member.guild.id] = {
                        before.channel.id: {member.id: seconds}
                    }
                else:
                    self.update_cache_dict[member.guild.id][before.channel.id][
                        member.id
                    ] += seconds
                del self.tracking[member.id]
        elif before.channel is not None:
            if member.id in self.tracking:
                time = datetime.now(tz=timezone.utc) - self.tracking[member.id]["time"]
                seconds = time.total_seconds()
                if (
                    self.update_cache_dict[member.guild.id]
                    .get(before.channel.id, {})
                    .get(member.id)
                    is None
                ):
                    self.update_cache_dict[member.guild.id] = {
                        before.channel.id: {member.id: seconds}
                    }
                else:
                    self.update_cache_dict[member.guild.id][before.channel.id][
                        member.id
                    ] += seconds
                del self.tracking[member.id]
            self.tracking[member.id] = {
                "channel": after.channel.id,
                "time": datetime.now(tz=timezone.utc),
            }

    @commands.group(aliases=["vc"])
    @commands.guild_only()
    async def voicetracker(self, ctx):
        """Voice Tracker"""

    @voicetracker.command(name="toggle")
    async def vc_toggle(self, ctx):
        """Enable/Disable Voice Tracker"""
        value = not await self.config.member(ctx.author).enabled()
        if value:
            await ctx.send("You have enabled your voice tracker.")
            await self.config.member(ctx.author).enabled.set(True)
        else:
            await ctx.send("You have disabled your voice tracker.")
            await self.config.member(ctx.author).enabled.set(False)
        await self.update_cache()

    @commands.group()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def vcset(self, ctx):
        """Voice Tracker Settings"""

    @vcset.command(name="toggle")
    async def vcset_toggle(self, ctx):
        """Enable/Disable Server Voice Tracker"""
        value = not await self.config.guild(ctx.guild).enabled()
        if value:
            await ctx.send("You have enabled your voice tracker for this server.")
            await self.config.guild(ctx.guild).enabled.set(True)
        else:
            await ctx.send("You have disabled the voice tracker for this server.")
            await self.config.guild(ctx.guild).enabled.set(False)
        await self.update_cache()

    @vcset.command(name="track", aliases=["add"])
    async def vcset_track(self, ctx, *, channel: discord.VoiceChannel):
        """Add a voice channel to track"""
        async with self.config.guild(ctx.guild).tracking() as voice_channels:
            if channel.id in voice_channels:
                await ctx.send(f"Removed {channel.mention} from tracking stats.")
                voice_channels.remove(channel.id)
            else:
                await ctx.send(f"Added {channel.mention} to tracking stats.")
                voice_channels.append(channel.id)
        await self.update_cache()

    @voicetracker.command(name="stats")
    async def vc_stats(self, ctx, user: discord.Member = None):
        """Voice Tracker Stats"""
        user = user or ctx.author
        await self.save_config()
        data = await self.config.guild(ctx.guild).voice_channels()

        msg = ""
        userid = str(user.id)
        for channel in data:
            if userid in data[channel]:
                channel_obj = ctx.guild.get_channel(int(channel))
                msg += f"{channel_obj.mention if channel_obj else 'Deleted Channel'} - {humanize_timedelta(seconds=ceil(data[channel][userid]))}\n"
        if msg == "":
            msg = f"No data found. Ensure you've toggled tracking on via `{ctx.prefix}vc toggle`."
        lst = list(pagify(msg, delims=["\n"]))
        embeds = []
        for i, page in enumerate(lst):
            embed = discord.Embed(
                title=f"Voice Tracker Stats for {user.display_name}",
                description=page,
                colour=user.colour,
            )
            embed.set_footer(text=f"Page {i+1}/{len(lst)}")
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
