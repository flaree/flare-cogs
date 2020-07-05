from .snipe import Snipe


async def setup(bot):
    n = Snipe(bot)
    await n.init()
    bot.add_cog(n)
