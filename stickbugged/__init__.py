from .stickbugged import StickBugged


async def setup(bot):
    await bot.add_cog(StickBugged(bot))
