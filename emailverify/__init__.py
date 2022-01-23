from .emailverify import EmailVerify


async def setup(bot):
    cog = EmailVerify(bot)
    bot.add_cog(cog)
