from .news import News


async def setup(bot):
    n = News(bot)
    bot.add_cog(n)
    await n.initalize()
