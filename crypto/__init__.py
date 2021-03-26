from .crypto import Crypto


def setup(bot):
    bot.add_cog(Crypto(bot))
