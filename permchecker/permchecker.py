import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

perms = [x[0] for x in discord.Permissions.all()]


class PermChecker(commands.Cog):
    __version__ = "0.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group()
    async def permcheck(self, ctx):
        """Check permissions"""

    @permcheck.command(name="user")
    async def permcheck_user(self, ctx, user: discord.Member, permission: str):
        """Check if a user has a permission"""
        if permission not in perms:
            await ctx.send(f"Invalid permission, valid permissions are:\n{', '.join(perms)}")
            return
        msg = "```diff\nRoles with permission:\n"
        found = False
        for role in user.roles:
            if getattr(role.permissions, permission):
                found = True
                msg += f"+ {role.name}\n"
        msg += "```"
        if not found:
            msg = "```diff\nNo roles with permission```"
        await ctx.send(msg)

    @permcheck.command(name="channel")
    async def permcheck_channel(self, ctx, permission: str):
        """Check if a channel has a permission"""
        if permission not in perms:
            await ctx.send(f"Invalid permission, valid permissions are:\n{', '.join(perms)}")
            return
        msg = "```diff\nRoles with permission:\n"
        found = False
        for channel in ctx.guild.channels:
            for obj in channel.overwrites:
                if getattr(channel.overwrites[obj], permission):
                    found = True
                    msg += f"+ {channel.name} - {obj.name}\n"
        msg += "```"
        if not found:
            msg = "```diff\nNo roles with permission```"
        await ctx.send(msg)

    @permcheck.command(name="role")
    async def permcheck_role(self, ctx, permission: str):
        """Check if a role has a permission"""
        if permission not in perms:
            await ctx.send(f"Invalid permission, valid permissions are:\n{', '.join(perms)}")
            return
        msg = "```diff\nRoles with permission:\n"
        found = False
        for role in ctx.guild.roles:
            if getattr(role.permissions, permission):
                found = True
                msg += f"+ {role.name}\n"
        msg += "```"
        if not found:
            msg = "```diff\nNo roles with permission```"
        await ctx.send(msg)
