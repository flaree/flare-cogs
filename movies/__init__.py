from .movies import Movies


def setup(bot):
    bot.add_cog(Movies(bot))
