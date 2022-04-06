from .f1 import F1


async def setup(bot):
    cog = F1(bot)
    await bot.add_cog(cog)
