from .trigger import Trigger


async def setup(bot):
    await bot.add_cog(Trigger(bot))
