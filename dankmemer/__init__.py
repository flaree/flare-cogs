from .dankmemer import DankMemer

async def setup(bot):
    cog = DankMemer(bot)
    bot.add_cog(cog)
    await cog.initalize()