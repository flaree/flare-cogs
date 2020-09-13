from .jishaku_cog import Jishaku


def setup(bot):
    bot.add_cog(Jishaku(bot))
