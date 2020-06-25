import discord
from redbot.core import Config, checks, commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import *
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import ReactionPredicate


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


class Modmail(commands.Cog):
    """Forward messages to set channels."""

    __version__ = "0.0.2"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476)
        self.config.register_guild(
            channel=None,
            toggle=False,
            ignored=[],
            message="Your message has been delivered.",
            respond=False,
            ignore=[],
        )

    async def initalize(self):
        await self.generate_cache()

    async def generate_cache(self):
        self.modmailcache = await self.config.all_guilds()

    async def channelsend(self, channels, message):
        pass

    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        if message.guild is not None:
            return
        if message.author == self.bot.user:
            return
        sharedguilds = [
            self.bot.get_guild(guild)
            async for guild in AsyncIter(self.modmailcache)
            if message.author in self.bot.get_guild(guild).members
            and self.modmailcache[guild]["toggle"]
        ]
        msgs = []
        for chunk in chunks(sharedguilds, 10):
            msg = "```Choose the server you wish to send the modmail to below:\n"
            for i, guild in enumerate(chunk):
                msg += f"{i}: {guild}\n"
            msg += "```"
            msgs.append(msg)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(autohelp=True)
    async def modmailset(self, ctx):
        """Modmail Commands."""

    @modmailset.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Setup the servers modmail channel..

        Not supplying a channel defaults to current channel.
        """
        channel = channel or ctx.channel
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"{ctx.guild}'s modmail channel has been set to post in {channel}.")
        await self.generate_cache()

    @modmailset.command()
    async def toggle(self, ctx, state: bool = None):
        """Toggle the modmail for the server on or off.

        Not supplying a bool will change the current setting.
        """
        if state is None:
            state = not await self.config.guild(ctx.guild).toggle()
        await self.config.guild(ctx.guild).toggle.set(state)
        await self.generate_cache()
        if state:
            await ctx.send(f"The modmail system in {ctx.guild} has been enabled.")
            return
        await ctx.send(f"The modmail system in {ctx.guild} has been disabled.")

    @modmailset.command()
    async def respond(self, ctx, mode: bool = None):
        """Toggle whether to send an automatic reply to modmail requests."""
        if state is None:
            state = not await self.config.guild(ctx.guild).respond()
        await self.config.guild(ctx.guild).respond.set(state)
        await self.generate_cache()
        if state:
            await ctx.send(f"The modmail system in {ctx.guild} has been enabled.")
            return
        await ctx.send(f"The modmail system in {ctx.guild} has been disabled.")

    @modmailset.command()
    async def respondmsg(self, ctx, *, message: str = None):
        """Set your response message for modmails.

        Not supplying a message will send the current configured one
        """
        if message is None:
            msg = await self.config.guild(ctx.guild).message()
            if msg is None:
                await ctx.send_help()
                return
            await ctx.send("Your current message being sent is:\n{}".format(msg))
            return
        await self.config.guild(ctx.guild).message.set(message)
        await ctx.send("Your message will be sent as:\n{}".format(message))
        await self.generate_cache()

    @modmailset.command()
    async def ignore(self, ctx, user: discord.Member):
        """Ignore a user from using the modmail."""

    @modmailset.command()
    async def unignore(self, ctx, user: discord.Member):
        """Remove user from the ignored list."""

    @modmailset.command()
    async def ignoredlist(self, ctx):
        """List ignored users."""

    @checks.mod()
    @commands.command()
    async def reply(self, ctx, user: discord.Member, *, message: str):
        """Reply to a modmail."""
        e = discord.Embed(colour=discord.Colour.red(), description=message)
        if ctx.bot.user.avatar_url:
            e.set_author(
                name=f"Message from {ctx.author} ({ctx.author.id}) on {ctx.guild}",
                icon_url=ctx.bot.user.avatar_url,
            )
        else:
            e.set_author(name=f"Message from {ctx.author} ({ctx.author.id}) on {ctx.guild}")

        try:
            await user.send(embed=e)
        except discord.HTTPException:
            await ctx.send("Sorry, I couldn't deliver your message to {}".format(user))
        else:
            await ctx.send("Message delivered to {}".format(user))

    # Owner Commands

    @checks.is_owner()
    @modmailset.command(name="list")
    async def _list(self, ctx):
        """List all current modmail channels."""
