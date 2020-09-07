from .dankmemer import DankMemer

__red_end_user_data_statement__ = "This cog does not persistently store data about users."

# Thanks Fixator for the changing name code.
async def setup(bot):
    cog = DankMemer(bot)
    for name, command in cog.all_commands.items():
        if bot.get_command(name):
            command.name = f"dm{command.name}"
        for alias in command.aliases:
            if bot.get_command(alias):
                command.aliases[command.aliases.index(alias)] = f"dm{alias}"
    bot.add_cog(cog)
    await cog.initalize()
