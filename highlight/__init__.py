from .highlight import Highlight

__red_end_user_data_statement__ = (
    "This cog stores data provided by uses for the purpose of notifying a user when data they provide is said.\n"
    "It does not store user data which was not provided through a command and users may remove their own content without the use of a data removal request.\n"
    "This cog will support data removal requests."  # TODO: Add removal
)


async def setup(bot):
    cog = Highlight(bot)
    await cog.initalize()
    bot.add_cog(cog)
