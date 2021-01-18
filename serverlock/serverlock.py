import discord
import jsonpickle
from redbot.core import Config, commands


class ServerLock(commands.Cog):
    """Lock a server down."""

    __version__ = "0.0.3"

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
        self.perms3 = discord.PermissionOverwrite(
            send_messages=None, add_reactions=None, connect=None
        )

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

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
        try:
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
                    overwrite = channels.get(str(channel.id))
                    channeloverwrite = (
                        jsonpickle.decode(overwrite) if overwrite is not None else None
                    )
                    if channeloverwrite is not None and channeloverwrite.read_messages is False:
                        await channel.set_permissions(
                            muted_role, overwrite=channeloverwrite, reason="Remove Lockdown."
                        )
                    else:
                        await channel.set_permissions(
                            muted_role, overwrite=self.perms3, reason="Remove Lockdown."
                        )
                await self.config.guild(guild).channels.set({})
                await msg.edit(content="Server is unlocked.")
                await ctx.tick()
                await self.config.guild(guild).locked.set(False)
        except discord.Forbidden:
            await ctx.send("Oops, I'm missing access to perform this operation.")
