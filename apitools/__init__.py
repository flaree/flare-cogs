from .apitools import ApiTools


async def setup(bot):
    await bot.add_cog(ApiTools(bot))
