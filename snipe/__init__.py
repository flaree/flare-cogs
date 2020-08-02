from .snipe import Snipe

__red_end_user_data_statement__ = "This cog does not persistently store data about users."


async def setup(bot):
    n = Snipe(bot)
    await n.init()
    bot.add_cog(n)
