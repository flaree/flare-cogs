from .wcrp import Wcrp


def setup(bot):
    bot.add_cog(Wcrp(bot))
