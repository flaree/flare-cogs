import discord
from redbot.core import commands, Config
from redbot.core.utils.common_filters import INVITE_URL_RE
import re


class DmInvite(commands.Cog):
    """Respond to invites send in DMs"""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 1398467138476, force_registration=True)
        self.config.register_global(
            toggle=True,
            message="I've detected a discord server invite. If you'd like to invite me please click the link below.\n{link}",
        )

    async def invite_url(self):
        app_info = await self.bot.application_info()
        perms = await self.bot._config.invite_perm()
        permissions = discord.Permissions(perms)
        return discord.utils.oauth_url(app_info.id, permissions)

    @commands.group()
    async def dminvite(self, ctx):
        """Group Commands for DM Invites"""
        pass

    @dminvite.command()
    @commands.is_owner()
    async def toggle(self, ctx):
        """Turn DM responding on/off"""
        toggle = await self.config.toggle()
        if toggle:
            await self.config.toggle.set(False)
            await ctx.send(
                "{} will no longer auto-respond to invites sent in DMs.".format(ctx.me.name)
            )
        else:
            await self.config.toggle.set(True)
            await ctx.send("{} will auto-respond to invites sent in DMs.".format(ctx.me.name))

    @dminvite.command()
    @commands.is_owner()
    async def message(self, ctx, *, message: str):
        """Set the message that the bot will respond with. The message must contain {link}."""
        if "{link}" not in message:
            return await ctx.send("The message must contain `{link}`.")
        await self.config.message.set(message)
        await ctx.tick()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild:
            return
        if message.author.bot:
            return
        if await self.config.toggle():
            link_res = INVITE_URL_RE.findall(message.content)
            if link_res:
                msg = await self.config.message()
                await message.author.send(msg.format(link=await self.invite_url()))
