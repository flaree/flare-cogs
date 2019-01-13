from .accounts import Accounts


def setup(bot):
    n = Accounts()
    bot.add_cog(n)
