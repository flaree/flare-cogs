from .covid import Covid


async def setup(bot):
    n = Covid(bot)
    bot.add_cog(n)
    await n.initalize()
