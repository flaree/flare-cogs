from .livescores import Livescores


def setup(bot):
    bot.add_cog(Livescores(bot))
