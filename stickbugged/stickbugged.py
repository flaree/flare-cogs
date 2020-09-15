import logging
import os
from io import BytesIO

import discord
from gsbl.stick_bug import StickBug
from PIL import Image
from redbot.core import commands
from redbot.core.data_manager import cog_data_path

log = logging.getLogger("redbot.flare.stick")


class StickBugged(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

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

    @commands.command(aliases=["stickbug", "stickbugged"])
    async def stick(self, ctx, user: discord.Member = None):
        """get stick bugged lol"""
        async with ctx.typing():
            user = user or ctx.author
            io = BytesIO()
            await user.avatar_url_as(format="png").save(io, seek_begin=True)
            await self.bot.loop.run_in_executor(None, self.blocking, io, ctx.message.id)
            fp = cog_data_path(self) / f"{ctx.message.id}stick.mp4"
            file = discord.File(str(fp), filename="stick.mp4")
            try:
                await ctx.send(files=[file])
            except Exception:
                log.error("Error sending stick bugged video", exc_info=True)
            try:
                os.remove(fp)
            except Exception:
                log.error("Error deleting stick bugged video", exc_info=True)
