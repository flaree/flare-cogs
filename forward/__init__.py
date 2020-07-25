from .forward import Forward

__end_user_data_statement__ = "This cog does not persistently store data about users."


def setup(bot):
    n = Forward(bot)
    bot.add_cog(n)
