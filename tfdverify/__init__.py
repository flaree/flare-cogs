from .tfdverify import TFDVerify


async def setup(bot):
    cog = TFDVerify(bot)
    bot.add_cog(cog)
