from .cashdrop import Cashdrop


def setup(bot):
    bot.add_cog(Cashdrop(bot))
