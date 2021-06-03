from .slashcommand import SlashCommand

__red_end_user_data_statement__ = "This cog does not store data about users."


async def setup(bot):
    cog = SlashCommand(bot)
    await cog.init()
    bot.add_cog(cog)