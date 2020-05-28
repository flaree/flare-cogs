import discord
from redbot.core import commands, Config
import jsonpickle


class ServerLock(commands.Cog):
    """Lock a server down."""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, 1398467138476, force_registration=True)
        self.config.register_guild(channels={}, locked=False)
        self.perms = discord.PermissionOverwrite(
            send_messages=False, add_reactions=False, connect=False
        )
        self.perms2 = discord.PermissionOverwrite(
            send_messages=False, add_reactions=False, connect=False, read_messages=False
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    @commands.has_permissions(manage_guild=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def lockdown(self, ctx):
        """Lock down an entire server.

        This command relies on no overwrites allowing to speak. It sets the @everyone role to not
        able to send, react or connect. Reissuing this command will unlock the server
        """
        guild = ctx.guild
        locked = await self.config.guild(guild).locked()
        muted_role = guild.default_role
        if not locked:
            channels = {}
            msg = await ctx.send("Server is being locked. Please wait")
            for channel in guild.channels:
                channeloverwrite = channel.overwrites.get(muted_role)
                channels[str(channel.id)] = jsonpickle.encode(channeloverwrite)
                if channeloverwrite is not None and channeloverwrite.read_messages is False:
                    await channel.set_permissions(
                        muted_role, overwrite=self.perms2, reason="Lockdown."
                    )
                else:
                    await channel.set_permissions(
                        muted_role, overwrite=self.perms, reason="Lockdown."
                    )
            await self.config.guild(guild).channels.set(channels)
            await msg.edit(content="Server is locked down.")
            await ctx.tick()
            await self.config.guild(guild).locked.set(True)
        else:
            channels = await self.config.guild(guild).channels()
            msg = await ctx.send("Server is being unlocked. Please wait.")
            for channel in guild.channels:
                channeloverwrite = jsonpickle.decode(channels[str(channel.id)])
                await channel.set_permissions(
                    muted_role, overwrite=channeloverwrite, reason="Remove lockdown."
                )
            await self.config.guild(guild).channels.set(channels)
            await msg.edit(content="Server is unlocked.")
            await ctx.tick()
            await self.config.guild(guild).locked.set(False)
