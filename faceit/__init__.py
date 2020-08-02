from .faceit import Faceit

__red_end_user_data_statement__ = (
    "This cog stores data provided by uses for the purpose of displaying a users statistics.\n"
    "It does not store user data which was not provided through a command and users may remove their own content without the use of a data removal request.\n"
    "This cog supports data removal requests."
)


async def setup(bot):
    cog = Faceit(bot)
    bot.add_cog(cog)
    await cog.initalize()
