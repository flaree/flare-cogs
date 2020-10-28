from .mod import Mod

__red_end_user_data_statement__ = (
    "This cog stores user data to actively maintain server moderation.\n"
    "It will not respect data deletion by end users as the data kept is the minimum "
    "needed for operation of an anti-abuse measure, nor can end users request "
    "their data from this cog since it only stores a discord ID.\n"
)


async def setup(bot):
    cog = Mod(bot)
    bot.add_cog(cog)
    await cog.initialize()
    await cog.notify()
