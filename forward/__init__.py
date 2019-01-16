from .forward import Forward


def setup(bot):
    n = Forward(bot)
    bot.add_cog(n)
