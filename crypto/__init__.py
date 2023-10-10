from .crypto import Crypto


async def setup(bot):
    await bot.add_cog(Crypto(bot))
