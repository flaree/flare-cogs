import asyncio
import logging
import os
from io import BytesIO

import aiohttp
import discord
from gsbl.stick_bug import StickBug
from PIL import Image
from redbot.core import commands
from redbot.core.data_manager import cog_data_path

from .converters import ImageFinder

log = logging.getLogger("redbot.flare.stick")


class StickBugged(commands.Cog):

    __version__ = "0.0.1"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot) -> None:
        self.bot = bot
        self._session = aiohttp.ClientSession()

    def blocking(self, io, id):
        sb = StickBug(Image.open(io))

        sb.video_resolution = (1280, 720)
        sb.lsd_scale = 0.5

        video = sb.video
        video.write_videofile(
            str(cog_data_path(self)) + f"/{id}stick.mp4",
            threads=1,
            preset="superfast",
            verbose=False,
            logger=None,
            temp_audiofile=str(cog_data_path(self) / f"{id}stick.mp3"),
        )
        return sb.video

    @commands.max_concurrency(2, commands.BucketType.default)
    @commands.command(aliases=["stickbug", "stickbugged"])
    async def stick(self, ctx, image: ImageFinder):
        """get stick bugged lol"""
        async with ctx.typing():
            io = BytesIO()
            if isinstance(image, discord.Asset):
                await image.save(io, seek_begin=True)
            else:
                async with self._session.get(str(image)) as resp:
                    if resp.status == 200:
                        io.write(await resp.read())
                        io.seek(0)
                    else:
                        return await ctx.send("The picture returned an unknown status code.")
            await asyncio.sleep(0.2)
            try:
                await self.bot.loop.run_in_executor(None, self.blocking, io, ctx.message.id)
            except Exception as e:
                log.error("Error sending stick bugged video", exc_info=e)
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
