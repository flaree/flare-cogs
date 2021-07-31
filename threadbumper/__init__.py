import discord
from redbot.core.errors import CogLoadError

from .threadbumper import ThreadBumper


def setup(bot):
    if discord.__version__[0] == "1":
        raise CogLoadError("You need to use discord.py 2.0.0 minimum to use this cog")

    bot.add_cog(ThreadBumper(bot))
