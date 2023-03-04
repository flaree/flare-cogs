from .palette import Palette


async def setup(bot):
    await bot.add_cog(Palette(bot))
