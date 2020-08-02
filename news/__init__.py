from .news import News

__red_end_user_data_statement__ = "This cog does not persistently store data about users."


async def setup(bot):
    n = News(bot)
    bot.add_cog(n)
    await n.initalize()
