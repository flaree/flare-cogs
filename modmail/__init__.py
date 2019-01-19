from .modmail import Modmail


def setup(bot):
    n = Modmail(bot)
    bot.add_cog(n)
