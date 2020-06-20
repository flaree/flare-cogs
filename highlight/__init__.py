from .highlight import Highlight


async def setup(bot):
    cog = Highlight(bot)
    await cog.initalize()
    bot.add_cog(cog)
