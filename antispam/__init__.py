from .antispam import AntiSpam


async def setup(bot):
    cog = AntiSpam(bot)
    await cog.gen_cache()
    bot.add_cog(cog)
