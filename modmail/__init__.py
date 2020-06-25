from .modmail import Modmail


async def setup(bot):
    cog = Modmail(bot)
    await cog.initalize()
    bot.add_cog(cog)
