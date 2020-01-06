from .rust import Rust

async def setup(bot):
    cog = Rust(bot)
    await cog.initalize()
    bot.add_cog(cog)