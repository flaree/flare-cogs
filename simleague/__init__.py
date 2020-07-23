from .simleague import SimLeague


async def setup(bot):
    cog = SimLeague(bot)
    bot.add_cog(cog)
