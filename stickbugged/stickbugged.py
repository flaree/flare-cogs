import asyncio
import functools
import logging
import os
from io import BytesIO
from typing import Optional

import aiohttp
import discord
from gsbl.stick_bug import StickBug
from PIL import Image
from redbot.core import commands
from redbot.core.data_manager import cog_data_path

from .converters import ImageFinder

log = logging.getLogger("red.flare.stick")


class StickBugged(commands.Cog):

    __version__ = "0.0.1"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot) -> None:
        self.bot = bot
        self._stickbug = StickBug()

    def blocking(self, io, id):
        io = Image.open(io)
        self._stickbug.image = io

        self._stickbug.video_resolution = max(min(1280, io.width), 128), max(
            min(720, io.height), 72
        )
        self._stickbug.lsd_scale = 0.35
        video = self._stickbug.video
        video.write_videofile(
            str(cog_data_path(self)) + f"/{id}stick.mp4",
            threads=1,
            preset="superfast",
            verbose=False,
            logger=None,
            temp_audiofile=str(cog_data_path(self) / f"{id}stick.mp3"),
        )
        video.close()
        return

    @commands.max_concurrency(1, commands.BucketType.default)
    @commands.command(aliases=["stickbug", "stickbugged"])
    async def stick(self, ctx, images: Optional[ImageFinder]):
        """get stick bugged lol"""
        if images is None:
            images = await ImageFinder().search_for_images(ctx)
        if not images:
            return await ctx.send_help()
        image = images
        async with ctx.typing():
            io = BytesIO()
            if isinstance(image, discord.Asset):
                await image.save(io, seek_begin=True)
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(image)) as resp:
                        if resp.status == 200:
                            io.write(await resp.read())
                            io.seek(0)
                        else:
                            return await ctx.send("The picture returned an unknown status code.")
            await asyncio.sleep(0.2)
            fake_task = functools.partial(self.blocking, io=io, id=ctx.message.id)
            task = self.bot.loop.run_in_executor(None, fake_task)
            try:
                video_file = await asyncio.wait_for(task, timeout=300)
            except asyncio.TimeoutError as e:
                log.error("Timeout creating stickbug video", exc_info=e)
                return await ctx.send("Timeout creating stickbug video.")
            except Exception as e:
                log.exception("Error sending stick bugged video")
                return await ctx.send(
                    "An error occured during the creation of the stick bugged video"
                )
            fp = cog_data_path(self) / f"{ctx.message.id}stick.mp4"
            file = discord.File(str(fp), filename="stick.mp4")
            try:
                await ctx.send(files=[file])
            except Exception as e:
                log.error("Error sending stick bugged video", exc_info=e)
            try:
                os.remove(fp)
            except Exception as e:
                log.error("Error deleting stick bugged video", exc_info=e)
