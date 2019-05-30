from .b44 import B44


def setup(bot):
    bot.add_cog(B44(bot))
