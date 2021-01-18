import logging

import discord
from redbot.core import Config, commands

log = logging.getLogger("red.flare.joinmessage")

CHANNELS = [
    "general",
    "general-chat",
    "основной",
    "основной-чат",
    "generell",
    "generell-chatt",
    "כללי",
    "צ'אט-כללי",
    "allgemein",
    "generale",
    "général",
    "općenito",
    "bendra",
    "általános",
    "algemeen",
    "generelt",
    "geral",
    "informații generale",
    "ogólny",
    "yleinen",
    "allmänt",
    "allmän-chat",
    "chung",
    "genel",
    "obecné",
    "obično",
    "Генерален чат",
    "общи",
    "загальний",
    "ทั่วไป",
    "常规",
]


class JoinMessage(commands.Cog):
    """Send a message on guild join."""

    __version__ = "0.0.10"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        self.config.register_global(message=None, toggle=False, embed=False, image=None)
        self.config.register_guild(notified=False)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if not await self.config.toggle():
            return
        if await self.config.guild(guild).notified():
            return
        msg = await self.config.message()
        if msg is None:
            log.info("No message setup, please set one up via the joinmessage message command.")
            return
        channel = (
            discord.utils.find(lambda x: x.name in CHANNELS, guild.text_channels)
            or guild.system_channel
            or next(
                (x for x in guild.text_channels if x.permissions_for(guild.me).send_messages), None
            )
        )
        if channel is None:
            log.debug("Couldn't find a channel to send join message in {}".format(guild))
            return
        if not channel.permissions_for(guild.me).send_messages:
            return
        if await self.config.embed() and channel.permissions_for(guild.me).embed_links:
            embed = discord.Embed(
                title=f"Thanks for inviting {guild.me.name}!",
                description=msg,
                colour=await self.bot.get_embed_colour(location=channel),
            )
            img = await self.config.image()
            if img is not None:
                embed.set_image(url=img)
            await channel.send(embed=embed)
        else:
            await channel.send(msg)
        await self.config.guild(guild).notified.set(True)
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

    @joinmessage.command(usage="type")
    async def embed(self, ctx, _type: bool = None):
        """Toggle sending of embed or not."""
        if _type is None:
            _type = not await self.config.embed()
        await self.config.embed.set(_type)
        if _type:
            await ctx.send("Server join messages will now be sent as an embed.")
            return
        await ctx.send("Server join messages will be sent in raw text.")

    @joinmessage.command(usage="raw")
    async def raw(self, ctx):
        """Send the configured message with markdown escaped."""
        msg = await self.config.message()
        if msg is None:
            await ctx.send(
                f"You do not have a message configured. Configure one using `{ctx.clean_prefix}joinmessage message`."
            )
            return
        raw = discord.utils.escape_markdown(msg)
        await ctx.send(f"```{raw}```")

    @joinmessage.command(usage="image")
    async def image(self, ctx, url: str = None):
        """Set image to be used when using embeds."""
        if url is None:
            await self.config.image.set(None)
        else:
            await self.config.image.set(url)
        await ctx.tick()

    @joinmessage.command()
    async def message(self, ctx, *, message: str = None):
        """Set the message to be sent on join.

        Sending no message will show the current message or help menu if
        none is set.
        """
        if message is None:
            msg = await self.config.message()
            if msg is None:
                await ctx.send_help()
                return
            await ctx.send("Your current message being sent is:\n{}".format(msg))
            return
        await self.config.message.set(message)
        await ctx.send("Your message will be sent as:\n{}".format(message))
