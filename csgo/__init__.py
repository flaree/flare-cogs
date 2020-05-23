from .csgo import Csgo


def setup(bot):
    bot.add_cog(Csgo(bot))
