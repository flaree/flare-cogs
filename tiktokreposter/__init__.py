import os

from .tiktokreposter import TikTokReposter

try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


async def setup(bot):
    # check if ffmpeg is installed
    if os.system("ffmpeg -version") != 0:
        raise CogLoadError("FFmpeg is not installed. Please install it before running this cog.")

    cog = TikTokReposter(bot)
    await cog.initialize()
    await bot.add_cog(cog)
