from .overwatch import Overwatch


def setup(bot):
    bot.add_cog(Overwatch(bot))
