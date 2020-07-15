from .botlistspost import BotListsPost


async def setup(bot):
    cog = BotListsPost(bot)
    await cog.init()
    bot.add_cog(cog)
