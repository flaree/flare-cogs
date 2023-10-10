from .rolehistory import RoleHistory


async def setup(bot):
    cog = RoleHistory(bot)
    await cog.initalize()
    await bot.add_cog(cog)
