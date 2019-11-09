from .spammute import Spammute


async def setup(bot):
    cog = Spammute(bot)
    bot.add_cog(cog)
