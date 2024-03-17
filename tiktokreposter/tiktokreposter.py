import functools
import os
import re
from io import BytesIO
from logging import getLogger

import aiohttp
import discord
from redbot.core import Config, commands, data_manager
from yt_dlp import YoutubeDL

log = getLogger("red.flare.tiktokreposter")


class TikTokReposter(commands.Cog):
    """Repost TikTok videos to a channel."""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: .flare."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_guild(
            auto_repost=False,
            channels=[],
            interval=0,
        )
        self.path = data_manager.cog_data_path(self)
        self.pattern = re.compile(r"\bhttps?://.*[(tiktok|douyin)]\S+")
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

    async def dl_tiktok(self, channel, url):
        with self.ytdl as ytdl:
            try:
                ytdl.download([url])
            except Exception as e:
                log.error(f"Error downloading TikTok video: {e}")
                return
        log.debug(f"Downloaded TikTok video from {url}")
        info = ytdl.extract_info(url, download=False)
        video_id = info["id"]
        task = functools.partial(
            self.convert_video, f"{self.path}/{video_id}.mp4", f"{self.path}/{video_id}_conv.mp4"
        )
        video = await self.bot.loop.run_in_executor(None, task)
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
        link = re.findall(self.pattern, message.content)
        if link:
            await self.dl_tiktok(message.channel, link[0])

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
    async def settings(self, ctx):
        """Show the current settings for TikTokReposter."""
        auto_repost = await self.config.guild(ctx.guild).auto_repost()
        channels = await self.config.guild(ctx.guild).channels()
        channels = [ctx.guild.get_channel(c).mention for c in channels]
        await ctx.send(
            f"Automatic reposting: {'enabled' if auto_repost else 'disabled'}\nChannels: {', '.join(channels)}"
        )
