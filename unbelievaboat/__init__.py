from .unbelievaboat import Unbelievaboat

__red_end_user_data_statement__ = (
    "This cog stores data attached to a users ID for intent of showing a balance.\n"
    "It does not store user data.\n"
    "This cog supports data removal requests."
)


async def setup(bot):
    await bot.add_cog(Unbelievaboat(bot))
