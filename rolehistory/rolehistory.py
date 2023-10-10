from datetime import datetime

import discord
from discord.utils import format_dt, utcnow
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu


class RoleHistory(commands.Cog):
    __version__ = "0.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808)
        default_member = {"history": [], "toggle": False}
        default_guild = {"toggle": False}
        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)
        self.guild_cache = {}
        self.toggle_cache = {}

    async def initalize(self):
        await self.bot.wait_until_ready()
        self.guild_cache = await self.config.all_guilds()
        self.toggle_cache = await self.config.all_members()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        guild = before.guild
        if before.guild.id not in self.guild_cache:
            return
        if not self.guild_cache[before.guild.id]["toggle"]:
            return
        if guild.id not in self.toggle_cache:
            return
        if not self.toggle_cache[guild.id].get(before.id, {}).get("toggle", False):
            return
        if before.roles != after.roles:
            roles = []
            if len(before.roles) > len(after.roles):
                roles.extend(
                    (role.id, role.name, "removed", utcnow().timestamp())
                    for role in before.roles
                    if role not in after.roles
                )
            elif len(before.roles) < len(after.roles):
                roles.extend(
                    (role.id, role.name, "added", utcnow().timestamp())
                    for role in after.roles
                    if role not in before.roles
                )
            if roles:
                async with self.config.member(before).history() as history:
                    for role in roles:
                        history.append(role)

    @commands.hybrid_group()
    async def rolehistory(self, ctx):
        """Role History Commands"""

    @rolehistory.command()
    async def toggle(self, ctx):
        """Toggle Role History"""
        guild_toggle = await self.config.guild(ctx.guild).toggle()
        if not guild_toggle:
            return await ctx.send("Role History is disabled for this guild", ephemeral=True)
        toggle = await self.config.member(ctx.author).toggle()
        await self.config.member(ctx.author).toggle.set(not toggle)
        await ctx.send(f"Role History is now {not toggle}", ephemeral=True)
        self.toggle_cache = await self.config.all_members()

    @rolehistory.command()
    async def show(self, ctx):
        """Show Role History"""
        history = await self.config.member(ctx.author).history()
        if not history:
            return await ctx.send("You have no role history", ephemeral=True)
        minus = "\\-"
        msg = "".join(
            f"{'+' if role[2] == 'added' else minus} {role[1]} | {format_dt(datetime.fromtimestamp(role[3]), style='F')}\n"
            for role in history
        )
        embeds = []
        for i, page in enumerate(pagify(msg, page_length=1000)):
            embed = discord.Embed(title=f"{ctx.author}'s Role History", description=page)
            embed.set_footer(text=f"Page {i}")
            embeds.append(embed)
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @rolehistory.command()
    @commands.admin_or_permissions(manage_roles=True)
    async def guildtoggle(self, ctx):
        """Toggle Role History for the guild"""
        toggle = await self.config.guild(ctx.guild).toggle()
        await self.config.guild(ctx.guild).toggle.set(not toggle)
        await ctx.send(f"Role History is now {not toggle}", ephemeral=True)
        self.guild_cache = await self.config.all_guilds()
