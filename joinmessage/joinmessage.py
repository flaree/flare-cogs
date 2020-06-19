import discord
from redbot.core import commands, Config
import logging

log = logging.getLogger("red.flare.joinmessage")


class JoinMessage(commands.Cog):
    """Send a message on guild join."""

    __version__ = "0.0.1"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        self.config.register_global(message=None, toggle=False)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if not await self.config.toggle():
            return
        msg = await self.config.message()
        if msg is None:
            log.info("No message setup, please set one up via the joinmessage message command.")
            return
        channel = discord.utils.find(
            lambda x: x.name in ["general", "general-chat"], guild.text_channels
        )
        if channel is None:
            channel = next(
                (x for x in guild.text_channels if x.permissions_for(guild.me).send_messages), None
            )
            if channel is None:
                log.debug("Couldn't find a channel to send join message in {}".format(guild))
        await channel.send(msg)
        log.debug("Guild welcome message sent in {}".format(guild))

    @commands.group()
    @commands.is_owner()
    async def joinmessage(self, ctx):
        """Options for sending messages on server join."""

    @joinmessage.command(usage="type")
    async def toggle(self, ctx, _type: bool = None):
        """Toggle server join messages on or off."""
        if _type is None:
            _type = not await self.config.toggle()
        await self.config.toggle.set(_type)
        if _type:
            await ctx.send("Server join messages have been enabled.")
            return
        await ctx.send("Server join messages have been disabled.")

    @joinmessage.command()
    async def message(self, ctx, *, message: str):
        """Set the message to be sent on join."""
        await self.config.message.set(message)
        await ctx.send("Your message will be sent as:\n{}".format(message))
