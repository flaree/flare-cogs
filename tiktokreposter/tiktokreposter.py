import functools
import os
import re
import sys
from io import BytesIO
from logging import getLogger

import aiohttp
import discord
from redbot.core import Config, commands, data_manager
from yt_dlp import YoutubeDL

log = getLogger("red.flare.tiktokreposter")

if sys.version_info < (3, 9):
    import asyncio
    import contextvars
    from typing import Callable, TypeVar

    from typing_extensions import ParamSpec

    T = TypeVar("T")
    P = ParamSpec("P")

    # backport of 3.9's asyncio.to_thread
    async def to_thread(func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
        loop = asyncio.get_running_loop()
        ctx = contextvars.copy_context()
        func_call = functools.partial(ctx.run, func, *args, **kwargs)
        return await loop.run_in_executor(None, func_call)  # type: ignore

else:
    from asyncio import to_thread


class TikTokReposter(commands.Cog):
    """Repost TikTok videos to a channel."""

    __version__ = "0.0.3"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: .flare."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_guild(
            auto_repost=False, channels=[], interval=0, reply=True, delete=False, suppress=True
        )
        self.path = data_manager.cog_data_path(self)
        self.pattern = re.compile(
            r"^.*https:\/\/(?:m|www|vm)?\.?tiktok\.com\/((?:.*\b(?:(?:usr|v|embed|user|video)\/|\?shareId=|\&item_id=)(\d+))|\w+)"
        )
        self.cache = {}
        self.ytdl_opts = {
            "format": "best",
            "outtmpl": str(self.path / "%(id)s.%(ext)s"),
            "quiet": True,
            "default_search": "auto",
            "verbose": False,
            # turn off warnings
            "no_warnings": True,
        }
        self.ytdl = YoutubeDL(self.ytdl_opts)

    async def initialize(self):
        self.cache = await self.config.all_guilds()

    def extract_info_and_convert(self, url: str) -> "tuple[dict, BytesIO]":
        with self.ytdl as ytdl:
            info = ytdl.extract_info(url, download=True)
            if info is None:
                raise Exception("Failed to extract video info")
        video_id = info["id"]
        return info, self.convert_video(
            f"{self.path}/{video_id}.mp4", f"{self.path}/{video_id}_conv.mp4"
        )

    async def dl_tiktok(
        self, channel, url, *, message=None, reply=True, delete=False, suppress=True
    ):
        try:
            info, video = await to_thread(self.extract_info_and_convert, url)
        except Exception as e:
            log.error(f"Error downloading TikTok video: {e}")
            return
        video_id = info["id"]
        if message is None:
            await channel.send(
                file=discord.File(video, filename=video_id + ".mp4"),
                content=f'Video from <{url}>\n{info["title"]}',
            )
        else:
            if reply:
                if suppress:
                    if message.guild.me.guild_permissions.manage_messages:
                        await message.edit(suppress=True)
                await message.reply(
                    file=discord.File(video, filename=video_id + ".mp4"),
                    content=f'Video from <{url}>\n{info["title"]}',
                )
            elif delete:
                await message.delete()
                await channel.send(
                    file=discord.File(video, filename=video_id + ".mp4"),
                    content=f'Video from <{url}>\n{info["title"]}',
                )
        log.debug(f"Reposted TikTok video from {url}")

        # delete the video
        os.remove(f"{self.path}/{video_id}.mp4")
        os.remove(f"{self.path}/{video_id}_conv.mp4")

    def convert_video(self, video_path, conv_path):
        # convert the video to h264 codec
        os.system(
            f"ffmpeg -i {video_path} -c:v libx264 -c:a aac -strict experimental {conv_path} -hide_banner -loglevel error"
        )
        with open(conv_path, "rb") as f:
            video = BytesIO(f.read())
            video.seek(0)
        return video

    @commands.command()
    async def tiktok(self, ctx, url: str):
        """Download and repost a TikTok video."""
        async with ctx.typing():
            await self.dl_tiktok(ctx.channel, url)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not self.cache.get(message.guild.id, {}).get("auto_repost", False):
            return
        channels = self.cache.get(message.guild.id, {}).get("channels", [])
        if message.channel.id not in channels:
            return
        link = re.match(self.pattern, message.content)
        if link:
            log.debug(link)
            link = link.group(0)
            await self.dl_tiktok(
                message.channel,
                link,
                message=message,
                reply=self.cache.get(message.guild.id, {}).get("reply", True),
                delete=self.cache.get(message.guild.id, {}).get("delete", False),
                suppress=self.cache.get(message.guild.id, {}).get("suppress", True),
            )

    # setting commands

    @commands.group()
    async def tiktokset(self, ctx):
        """Settings for TikTokReposter."""

    @tiktokset.command()
    async def auto(self, ctx):
        """Toggle automatic reposting of TikTok links."""
        auto_repost = await self.config.guild(ctx.guild).auto_repost()
        await self.config.guild(ctx.guild).auto_repost.set(not auto_repost)
        await ctx.send(
            f"Automatic reposting of TikTok links is now {'enabled' if not auto_repost else 'disabled'}."
        )
        await self.initialize()

    @tiktokset.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Add or remove a channel to repost TikTok links."""
        channel = channel or ctx.channel
        channels = await self.config.guild(ctx.guild).channels()
        if channel.id in channels:
            channels.remove(channel.id)
            await ctx.send(
                f"{channel.mention} removed from the list of channels to repost TikTok links."
            )
        else:
            channels.append(channel.id)
            await ctx.send(
                f"{channel.mention} added to the list of channels to repost TikTok links."
            )
        await self.config.guild(ctx.guild).channels.set(channels)
        await self.initialize()

    @tiktokset.command()
    async def reply(self, ctx):
        """Toggle replying to TikTok links."""
        reply = await self.config.guild(ctx.guild).reply()
        await self.config.guild(ctx.guild).reply.set(not reply)
        delete = await self.config.guild(ctx.guild).delete()
        if delete:
            await ctx.send("Replying cannot be enabled while deleting messages is enabled.")
            return
        await ctx.send(
            f"Replying to TikTok links is now {'enabled' if not reply else 'disabled'}."
        )
        await self.initialize()

    @tiktokset.command()
    async def delete(self, ctx):
        """Toggle deleting messages with TikTok links."""
        delete = await self.config.guild(ctx.guild).delete()
        await self.config.guild(ctx.guild).delete.set(not delete)
        reply = await self.config.guild(ctx.guild).reply()
        if reply:
            await ctx.send("Deleting messages cannot be enabled while replying is enabled.")
            return
        await ctx.send(
            f"Deleting messages with TikTok links is now {'enabled' if not delete else 'disabled'}."
        )
        await self.initialize()

    @tiktokset.command()
    async def suppress(self, ctx):
        """Toggle suppressing the embed message."""
        suppress = await self.config.guild(ctx.guild).suppress()
        await self.config.guild(ctx.guild).suppress.set(not suppress)
        await ctx.send(
            f"Suppressing the message embed is now {'enabled' if not suppress else 'disabled'}."
        )
        await self.initialize()

    @tiktokset.command()
    async def settings(self, ctx):
        """Show the current settings for TikTokReposter."""
        auto_repost = await self.config.guild(ctx.guild).auto_repost()
        channels = await self.config.guild(ctx.guild).channels()
        channels = [ctx.guild.get_channel(c).mention for c in channels if ctx.guild.get_channel(c)]
        reply = await self.config.guild(ctx.guild).reply()
        delete = await self.config.guild(ctx.guild).delete()
        suppress = await self.config.guild(ctx.guild).suppress()
        await ctx.send(
            f"Automatic reposting: {'enabled' if auto_repost else 'disabled'}\nChannels: {', '.join(channels)}\nReplying: {'enabled' if reply else 'disabled'}\nDeleting: {'enabled' if delete else 'disabled'}\nSuppressing: {'enabled' if suppress else 'disabled'}"
        )
