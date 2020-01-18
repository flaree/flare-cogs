from .commandstats import CommandStats


def setup(bot):
    bot.add_cog(CommandStats(bot))
