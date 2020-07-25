from .dankmemer import DankMemer

__end_user_data_statement__ = "This cog does not persistently store data about users."


async def setup(bot):
    cog = DankMemer(bot)
    bot.add_cog(cog)
    await cog.initalize()
