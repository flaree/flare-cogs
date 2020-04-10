from .faceit import Faceit


async def setup(bot):
    cog = Faceit(bot)
    bot.add_cog(cog)
    await cog.initalize()
