from .highlight import Highlight


async def setup(bot):
    cog = Highlight(bot)
    await cog.migrate_config()
    bot.add_cog(cog)
