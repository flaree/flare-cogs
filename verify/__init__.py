from .verify import Verify


async def setup(bot):
    cog = Verify(bot)
    bot.add_cog(cog)
