from .permchecker import PermChecker


async def setup(bot):
    cog = PermChecker(bot)
    await bot.add_cog(cog)
