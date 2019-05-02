from .verify import Verify


def setup(bot):
    bot.add_cog(Verify(bot))
