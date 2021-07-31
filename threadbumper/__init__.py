import discord
from redbot.core.errors import CogLoadError

from .threadbumper import ThreadBumper


def setup(bot):
    if discord.__version__[0] == "1":
        raise CogLoadError(
            "You need to run the bot with the redbot-py-experimental-repo "
            "version of discord.py. There is no support for this cog as of yet."
        )

    bot.add_cog(ThreadBumper(bot))
