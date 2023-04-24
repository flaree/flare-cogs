import discord
from redbot.core.errors import CogLoadError

from .threadbumper import ThreadBumper


async def setup(bot):
    await bot.add_cog(ThreadBumper(bot))
