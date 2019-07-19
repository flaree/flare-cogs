from .connect4 import Connect4


def setup(bot):
    n = Connect4(bot)
    bot.add_cog(n)
