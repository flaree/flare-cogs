from redbot.core.bot import Red

from .tips import Tips


async def setup(bot: Red) -> None:
    cog = Tips(bot)
    bot.add_cog(cog)
    await cog.initialize()
