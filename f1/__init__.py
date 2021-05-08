from .f1 import F1


async def setup(bot):
    cog = F1(bot)
    bot.add_cog(cog)
