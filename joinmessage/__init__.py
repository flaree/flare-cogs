from .joinmessage import JoinMessage

__end_user_data_statement__ = "This cog does not persistently store data about users."


def setup(bot):
    bot.add_cog(JoinMessage(bot))
