from .r6 import R6


async def setup(bot):
    cog = R6(bot)
    await cog.initalize()
    bot.add_cog(cog)
