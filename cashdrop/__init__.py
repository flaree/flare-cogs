from .cashdrop import Cashdrop


async def setup(bot):
    await bot.add_cog(Cashdrop(bot))
