from .trigger import Trigger


def setup(bot):
    bot.add_cog(Trigger(bot))
