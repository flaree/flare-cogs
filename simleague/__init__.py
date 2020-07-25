from .simleague import SimLeague

__end_user_data_statement__ = (
    "This cog stores a discord User id for when a user wishes to be notified on an action.\n"
    "The user can turn this notification off without the use of a data removal request.\n"
    "This cog supports data removal requests."
)

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
