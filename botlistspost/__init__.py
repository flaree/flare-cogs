from .botlistspost import BotListsPost

__red_end_user_data_statement__ = "This cog does not persistently store data about users."


async def setup(bot):
    cog = BotListsPost(bot)
    await cog.init()
    bot.add_cog(cog)
