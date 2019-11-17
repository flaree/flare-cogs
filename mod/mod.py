import asyncio
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import tasks
from redbot.cogs.mod import Mod as ModClass
from redbot.core import Config, checks, commands
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_list, humanize_timedelta
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("red.mod")


class Mod(ModClass):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        defaultsguild = {"muterole": None}
        defaults = {"muted": {}}
        self.config.register_guild(**defaultsguild)
        self.config.register_global(**defaults)
        self.unmute_loop.start()  # pylint: disable=E1101

    voice_mute = None
    channel_mute = None
    guild_mute = None
    unmute_voice = None
    unmute_channel = None
    unmute_guild = None

    def cog_unload(self):
        self.unmute_loop.cancel()  # pylint: disable=E1101

    @tasks.loop(seconds=20)
    async def unmute_loop(self):
        muted = await self.config.muted()
        for guild in muted:
            for user in muted[guild]:
                if datetime.utcfromtimestamp(muted[guild][user]["expiry"]) < datetime.utcnow():
                    await self.unmute(user, guild)

    async def unmute(self, user, guildid):
        guild = self.bot.get_guild(int(guildid))
        if guild is None:
            return
        mutedroleid = await self.config.guild(guild).muterole()
        muterole = guild.get_role(mutedroleid)
        member = guild.get_member(int(user))
        await member.remove_roles(muterole, reason="Mute expired.")
        log.info("Unmuted {} in {}".format(member, guild))
        async with self.config.muted() as muted:
            del muted[guildid][user]

    async def create_muted_role(self, guild):
        muted_role = await guild.create_role(
            name="Muted", reason="Muted role created by Pikachu for timed mutes."
        )
        await self.config.guild(guild).muterole.set(muted_role.id)
        o = discord.PermissionOverwrite(send_messages=False, add_reactions=False, connect=False)
        for channel in guild.channels:
            mr_overwrite = channel.overwrites.get(muted_role)
            if not mr_overwrite or o != mr_overwrite:
                await channel.set_permissions(
                    muted_role,
                    overwrite=o,
                    reason="Ensures that Muted users won't be able to talk here.",
                )

    @checks.mod()
    @checks.bot_has_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True)
    async def mute(
        self,
        ctx,
        users: commands.Greedy[discord.Member],
        duration: TimedeltaConverter(
            minimum=timedelta(), maximum=timedelta(weeks=99999), default_unit="minutes"
        ),
    ):
        """Mute users."""
        if not users or duration is None:
            return
        guild = ctx.guild
        roleid = await self.config.guild(guild).muterole()
        if roleid is None:
            await ctx.send(
                "There is currently no mute role set for this server. If you would like one to be automatically setup then type yes, otherwise one can be set via {}mute setrole <role>".format(
                    ctx.prefix
                )
            )
            try:
                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                msg = await ctx.bot.wait_for("message", check=pred, timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send("Alright, cancelling the operation.")

            if pred.result:
                await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
                await self.create_muted_role(guild)
                roleid = await self.config.guild(guild).muterole()
                await ctx.send(roleid if roleid else "None")
            else:
                await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
                return
        mutedrole = guild.get_role(roleid)
        if mutedrole is None:
            return await ctx.send(
                f"The mute role for this server is invalid. Please set one up using {ctx.prefix}mute roleset <role>."
            )
        async with self.config.muted() as muted:
            if str(ctx.guild.id) not in muted:
                muted[str(ctx.guild.id)] = {}
            for user in users:
                await user.add_roles(
                    mutedrole,
                    reason="Muted by {} for {}".format(
                        ctx.author, humanize_timedelta(timedelta=duration)
                    ),
                )
                expiry = datetime.utcnow() + timedelta(seconds=duration.total_seconds())
                muted[str(ctx.guild.id)][str(user.id)] = {
                    "time": datetime.utcnow().timestamp(),
                    "expiry": int(expiry.timestamp()),
                }
        await ctx.send(
            f"`{humanize_list([str(x) for x in users])}` has been muted for {humanize_timedelta(timedelta=duration)}"
        )

    @checks.admin()
    @mute.command()
    async def roleset(self, ctx, role: discord.Role):
        """Set a mute role."""
        await self.config.guild(ctx.guild).muterole.set(role.id)
        await ctx.send("The muted role has been set to {}".format(role.name))

    @checks.mod()
    @checks.bot_has_permissions(manage_roles=True)
    @commands.group(invoke_without_command=True, name="unmute")
    async def _unmute(self, ctx, user: discord.Member):
        """Unmute usuers."""
        muted = await self.config.muted()
        if str(ctx.guild.id) not in muted:
            return await ctx.send("There is nobody currently muted in this server.")
        if str(user.id) not in muted[str(ctx.guild.id)]:
            return await ctx.send("That user is currently not muted.")
        await self.unmute(str(user.id), str(ctx.guild.id))
        await ctx.tick()
