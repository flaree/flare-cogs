from .antispam import AntiSpam

__red_end_user_data_statement__ = "This cog does not persistently store data about users."


async def setup(bot):
    cog = AntiSpam(bot)
    await cog.init()
    bot.add_cog(cog)
