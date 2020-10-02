from asyncio import create_task

from .dankmemer import DankMemer

__red_end_user_data_statement__ = "This cog does not persistently store data about users."


async def setup_after_ready(bot):
    await bot.wait_until_red_ready()
    cog = DankMemer(bot)
    await cog.initalize()
    for name, command in cog.all_commands.items():
        if not command.parent:
            if bot.get_command(name):
                command.name = f"dm{command.name}"
            for alias in command.aliases:
                if bot.get_command(alias):
                    command.aliases[command.aliases.index(alias)] = f"dm{alias}"
    bot.add_cog(cog)


# Thanks Fixator for the changing name code.


def setup(bot):
    create_task(setup_after_ready(bot))
