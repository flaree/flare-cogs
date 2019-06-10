from .simleague import SimLeague


def setup(bot):
    bot.add_cog(SimLeague(bot))
