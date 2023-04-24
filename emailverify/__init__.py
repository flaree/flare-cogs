from .emailverify import EmailVerify


async def setup(bot):
    cog = EmailVerify(bot)
    await bot.add_cog(cog)
