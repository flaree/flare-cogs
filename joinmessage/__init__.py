from .joinmessage import JoinMessage


def setup(bot):
    bot.add_cog(JoinMessage(bot))
