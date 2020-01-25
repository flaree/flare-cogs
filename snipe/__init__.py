from .snipe import Snipe


def setup(bot):
    n = Snipe
    bot.add_cog(n(bot))
