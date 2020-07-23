from .simleague import SimLeague

try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


async def setup(bot):
    if "Leveler" not in bot.cogs:
        raise CogLoadError(
            "A mongodb instance and leveler by fixator/aikaterna is **REQUIRED** for this cog to function."
        )
    cog = SimLeague(bot)
    bot.add_cog(cog)
