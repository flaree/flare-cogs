import contextlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional, Tuple, Union

import discord
import TagScriptEngine as tse
from redbot.cogs.mod.mod import Mod as ModClass
from redbot.cogs.mod.utils import is_allowed_by_hierarchy
from redbot.core import Config, app_commands, checks, commands, modlog
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold, box, humanize_timedelta
from redbot.core.utils.mod import get_audit_reason

from ._tagscript import (
    TagScriptConverter,
    ban_message,
    kick_message,
    process_tagscript,
    tempban_message,
    unban_message,
)

log = logging.getLogger("red.flarecogs.mod")

from discord.ext import commands as dpy_commands
from discord.ext.commands import BadArgument

ID_REGEX = re.compile(r"([0-9]{15,20})")
USER_MENTION_REGEX = re.compile(r"<@!?([0-9]{15,21})>$")


# https://github.com/flaree/Red-DiscordBot/blob/FR-custom-bankick-msgs/redbot/core/commands/converter.py#L207
class RawUserIdConverter(dpy_commands.Converter):
    """
    Converts ID or user mention to an `int`.
    Useful for commands like ``[p]ban`` or ``[p]unban`` where the bot is not necessarily
    going to share any servers with the user that a moderator wants to ban/unban.
    This converter doesn't check if the ID/mention points to an actual user
    but it won't match IDs and mentions that couldn't possibly be valid.
    For example, the converter will not match on "123" because the number doesn't have
    enough digits to be valid ID but, it will match on "12345678901234567" even though
    there is no user with such ID.
    """

    async def convert(self, ctx, argument: str) -> int:
        # This is for the hackban and unban commands, where we receive IDs that
        # are most likely not in the guild.
        # Mentions are supported, but most likely won't ever be in cache.

        if match := ID_REGEX.match(argument) or USER_MENTION_REGEX.match(argument):
            return int(match.group(1))

        raise BadArgument(("'{input}' doesn't look like a valid user ID.").format(input=argument))


class Mod(ModClass):
    """Mod with custom messages."""

    modset = ModClass.modset.copy()

    __version__ = "1.3.0"

    def format_help_for_context(self, ctx: commands.Context):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red):
        super().__init__(bot)
        self.bot: Red = bot
        self._config: Config = Config.get_conf(self, 95932766180343808, force_registration=True)
        self._config.register_guild(
            **{
                "kick_message": kick_message,
                "ban_message": ban_message,
                "tempban_message": tempban_message,
                "unban_message": unban_message,
                "require_reason": False,
            }
        )

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        return None

    @modset.command()
    @commands.guild_only()
    async def kickmessage(self, ctx: commands.Context, *, message: TagScriptConverter):
        """Set the message sent when a user is kicked.

        **Blocks:**
        - [Assignment Block](https://seina-cogs.readthedocs.io/en/latest/tags/tse_blocks.html#assignment-block)
        - [Embed Block](https://seina-cogs.readthedocs.io/en/latest/tags/parsing_blocks.html#embed-block)

        **Variables:**
        - `{user}`: [member that was kicked.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{moderator}`: [modrator that kicked the member.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{reason}`: reason for the kick.
        - `{guild}`: [server](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#server-block)
        """
        guild = ctx.guild
        await self._config.guild(guild).kick_message.set(message)
        await ctx.send("Kick message updated:\n{}".format(box(str(message), lang="json")))

    @modset.command()
    @commands.guild_only()
    async def banmessage(self, ctx: commands.Context, *, message: TagScriptConverter):
        """Set the message sent when a user is banned.

        **Blocks:**
        - [Assignment Block](https://seina-cogs.readthedocs.io/en/latest/tags/tse_blocks.html#assignment-block)
        - [Embed Block](https://seina-cogs.readthedocs.io/en/latest/tags/parsing_blocks.html#embed-block)

        **Variables:**
        - `{user}`: [member that was banned.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{moderator}`: [modrator that banned the member.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{reason}`: reason for the ban.
        - `{guild}`: [server](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#server-block)
        - `{days}`: number of days of messages deleted.
        """
        guild = ctx.guild
        await self._config.guild(guild).ban_message.set(message)
        await ctx.send("Ban message updated:\n{}".format(box(str(message), lang="json")))

    @modset.command()
    @commands.guild_only()
    async def tempbanmessage(self, ctx: commands.Context, *, message: TagScriptConverter):
        """Set the message sent when a user is tempbanned.

        **Blocks:**
        - [Assignment Block](https://seina-cogs.readthedocs.io/en/latest/tags/tse_blocks.html#assignment-block)
        - [Embed Block](https://seina-cogs.readthedocs.io/en/latest/tags/parsing_blocks.html#embed-block)

        **Variables:**
        - `{user}`: [member that was tempbanned.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{moderator}`: [modrator that tempbanned the member.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{reason}`: reason for the tempban.
        - `{guild}`: [server](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#server-block)
        - `{days}`: number of days of messages deleted.
        - `{duration}`: duration of the tempban.
        """
        guild = ctx.guild
        await self._config.guild(guild).tempban_message.set(message)
        await ctx.send("Tempban message updated:\n{}".format(box(str(message), lang="json")))

    @modset.command()
    @commands.guild_only()
    async def unbanmessage(self, ctx: commands.Context, *, message: TagScriptConverter):
        """Set the message sent when a user is unbanned.

        **Blocks:**
        - [Assignment Block](https://seina-cogs.readthedocs.io/en/latest/tags/tse_blocks.html#assignment-block)
        - [Embed Block](https://seina-cogs.readthedocs.io/en/latest/tags/parsing_blocks.html#embed-block)

        **Variables:**
        - `{user}`: [member that was tempbanned.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{moderator}`: [modrator that tempbanned the member.](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#author-block)
        - `{reason}`: reason for the tempban.
        - `{guild}`: [server](https://seina-cogs.readthedocs.io/en/latest/tags/default_variables.html#server-block)
        """
        guild = ctx.guild
        await self._config.guild(guild).unban_message.set(message)
        await ctx.send("Unban message updated:\n{}".format(box(str(message), lang="json")))

    @modset.command(name="showmessages")
    async def modset_showmessages(self, ctx: commands.Context):
        """Show the current messages for moderation commands."""
        messageData = await self._config.guild(ctx.guild).all()
        msg = "Kick Message: {kick_message}\n".format(kick_message=messageData["kick_message"])
        msg += "Ban Message: {ban_message}\n".format(ban_message=messageData["ban_message"])
        msg += "Tempban Message: {tempban_message}\n".format(
            tempban_message=messageData["tempban_message"]
        )
        msg += "Unban Message: {unban_message}\n".format(
            unban_message=messageData["unban_message"]
        )
        await ctx.send(box(msg))

    @modset.command(name="reasons")
    async def modset_require_reason(self, ctx: commands.Context, value: bool):
        """Set whether a reason is required for moderation actions."""
        await self._config.guild(ctx.guild).require_reason.set(value)
        await ctx.send(f"Reason requirement set to {value}")

    kick = None

    @commands.hybrid_command()
    @app_commands.describe(member="The member to kick.", reason="The reason for kicking the user.")
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        Kick a user.
        Examples:
           - `[p]kick 428675506947227648 wanted to be kicked.`
            This will kick the user with ID 428675506947227648 from the server.
           - `[p]kick @Twentysix wanted to be kicked.`
            This will kick Twentysix from the server.
        If a reason is specified, it will be the reason that shows up
        in the audit log.
        """
        require_reason = await self._config.guild(ctx.guild).require_reason()
        if require_reason and reason is None:
            await ctx.send("You must provide a reason for this action.")
            return
        author = ctx.author
        guild = ctx.guild

        if author == member:
            await ctx.send(
                ("I cannot let you do that. Self-harm is bad {emoji}").format(
                    emoji="\N{PENSIVE FACE}"
                )
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                (
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif ctx.guild.me.top_role <= member.top_role or member == ctx.guild.owner:
            await ctx.send(("I cannot do that due to Discord hierarchy rules."))
            return
        audit_reason = get_audit_reason(author, reason, shorten=True)
        toggle = await self.config.guild(guild).dm_on_kickban()
        if toggle:
            with contextlib.suppress(discord.HTTPException):
                em = discord.Embed(
                    title=bold(("You have been kicked from {guild}.").format(guild=guild)),
                    color=await self.bot.get_embed_color(member),
                )
                em.add_field(
                    name=("**Reason**"),
                    value=reason if reason is not None else ("No reason was given."),
                    inline=False,
                )
                await member.send(embed=em)
        try:
            await guild.kick(member, reason=audit_reason)
            log.info("{}({}) kicked {}({})".format(author.name, author.id, member.name, member.id))
        except discord.errors.Forbidden:
            await ctx.send("I'm not allowed to do that.")
        except Exception:
            log.exception(
                "{}({}) attempted to kick {}({}), but an error occurred.".format(
                    author.name, author.id, member.name, member.id
                )
            )
        else:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "kick",
                member,
                author,
                reason,
                until=None,
                channel=None,
            )
            message = await self._config.guild(ctx.guild).kick_message()
            kwargs = process_tagscript(
                message,
                {
                    "user": tse.MemberAdapter(member),
                    "moderator": tse.MemberAdapter(author),
                    "reason": tse.StringAdapter(str(reason)),
                    "guild": tse.GuildAdapter(guild),
                },
            )
            if not kwargs:
                await self._config.guild(ctx.guild).kick_message.clear()
                kwargs = process_tagscript(
                    kick_message,
                    {
                        "user": tse.MemberAdapter(member),
                        "moderator": tse.MemberAdapter(author),
                        "reason": tse.StringAdapter(str(reason)),
                        "guild": tse.GuildAdapter(guild),
                    },
                )
            await ctx.send(**kwargs)

    tempban = None

    @commands.hybrid_command()
    @app_commands.describe(
        member="The member to tempban.",
        reason="The reason for tempbanning the user.",
        duration="The duration of the tempban.",
        days="The number of days of messages to delete.",
    )
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def tempban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: Optional[commands.TimedeltaConverter] = None,
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Temporarily ban a user from this server.
        `duration` is the amount of time the user should be banned for.
        `days` is the amount of days of messages to cleanup on tempban.
        Examples:
           - `[p]tempban @Twentysix Because I say so`
            This will ban Twentysix for the default amount of time set by an administrator.
           - `[p]tempban @Twentysix 15m You need a timeout`
            This will ban Twentysix for 15 minutes.
           - `[p]tempban 428675506947227648 1d2h15m 5 Evil person`
            This will ban the user with ID 428675506947227648 for 1 day 2 hours 15 minutes and will delete the last 5 days of their messages.
        """
        require_reason = await self._config.guild(ctx.guild).require_reason()
        if require_reason and reason is None:
            await ctx.send("You must provide a reason for this action.")
            return
        guild = ctx.guild
        author = ctx.author

        if author == member:
            await ctx.send(
                ("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}")
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                (
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif guild.me.top_role <= member.top_role or member == guild.owner:
            await ctx.send(("I cannot do that due to Discord hierarchy rules."))
            return

        guild_data = await self.config.guild(guild).all()

        if duration is None:
            duration = timedelta(seconds=guild_data["default_tempban_duration"])
        unban_time = datetime.now(timezone.utc) + duration

        if days is None:
            days = guild_data["default_days"]

        if not (0 <= days <= 7):
            await ctx.send(("Invalid days. Must be between 0 and 7."))
            return
        invite = await self.get_invite_for_reinvite(ctx, int(duration.total_seconds() + 86400))

        await self.config.member(member).banned_until.set(unban_time.timestamp())
        async with self.config.guild(guild).current_tempbans() as current_tempbans:
            current_tempbans.append(member.id)

        with contextlib.suppress(discord.HTTPException):
            # We don't want blocked DMs preventing us from banning
            msg = ("You have been temporarily banned from {server_name} until {date}.").format(
                server_name=guild.name, date=discord.utils.format_dt(unban_time)
            )
            if guild_data["dm_on_kickban"] and reason:
                msg += ("\n\n**Reason:** {reason}").format(reason=reason)
            if invite:
                msg += ("\n\nHere is an invite for when your ban expires: {invite_link}").format(
                    invite_link=invite
                )
            await member.send(msg)

        audit_reason = get_audit_reason(author, reason, shorten=True)

        try:
            await guild.ban(member, reason=audit_reason, delete_message_days=days)
        except discord.Forbidden:
            await ctx.send(("I can't do that for some reason."))
        except discord.HTTPException:
            await ctx.send(("Something went wrong while banning."))
        else:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "tempban",
                member,
                author,
                reason,
                unban_time,
            )
            message = await self._config.guild(ctx.guild).tempban_message()
            humanized_duration = humanize_timedelta(timedelta=duration)
            kwargs = process_tagscript(
                message,
                {
                    "user": tse.MemberAdapter(member),
                    "moderator": tse.MemberAdapter(author),
                    "reason": tse.StringAdapter(str(reason)),
                    "guild": tse.GuildAdapter(guild),
                    "duration": tse.StringAdapter(humanized_duration),
                    "days": tse.IntAdapter(days),
                },
            )
            if not kwargs:
                await self._config.guild(ctx.guild).tempban_message.clear()
                kwargs = process_tagscript(
                    tempban_message,
                    {
                        "user": tse.MemberAdapter(member),
                        "moderator": tse.MemberAdapter(author),
                        "reason": tse.StringAdapter(str(reason)),
                        "guild": tse.GuildAdapter(guild),
                        "duration": tse.StringAdapter(humanized_duration),
                        "days": tse.IntAdapter(days),
                    },
                )
            await ctx.send(**kwargs)

    softban = None

    @commands.hybrid_command()
    @app_commands.describe(
        member="The member to softban.", reason="The reason for softbanning the user."
    )
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """Kick a user and delete 1 day's worth of their messages."""
        require_reason = await self._config.guild(ctx.guild).require_reason()
        if require_reason and reason is None:
            await ctx.send("You must provide a reason for this action.")
            return
        guild = ctx.guild
        author = ctx.author

        if author == member:
            await ctx.send(
                ("I cannot let you do that. Self-harm is bad {emoji}").format(
                    emoji="\N{PENSIVE FACE}"
                )
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, member):
            await ctx.send(
                (
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return

        audit_reason = get_audit_reason(author, reason, shorten=True)

        invite = await self.get_invite_for_reinvite(ctx)

        try:  # We don't want blocked DMs preventing us from banning
            msg = await member.send(
                (
                    "You have been banned and "
                    "then unbanned as a quick way to delete your messages.\n"
                    "You can now join the server again. {invite_link}"
                ).format(invite_link=invite)
            )
        except discord.HTTPException:
            msg = None
        try:
            await guild.ban(member, reason=audit_reason, delete_message_days=1)
        except discord.errors.Forbidden:
            await ctx.send(("My role is not high enough to softban that user."))
            if msg is not None:
                await msg.delete()
            return
        except discord.HTTPException:
            log.exception(
                "{}({}) attempted to softban {}({}), but an error occurred trying to ban them.".format(
                    author.name, author.id, member.name, member.id
                )
            )
            return
        try:
            await guild.unban(member)
        except discord.HTTPException:
            log.exception(
                "{}({}) attempted to softban {}({}), but an error occurred trying to unban them.".format(
                    author.name, author.id, member.name, member.id
                )
            )
            return
        else:
            log.info(
                "{}({}) softbanned {}({}), deleting 1 day worth "
                "of messages.".format(author.name, author.id, member.name, member.id)
            )
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "softban",
                member,
                author,
                reason,
                until=None,
                channel=None,
            )
            message = await self._config.guild(ctx.guild).kick_message()
            kwargs = process_tagscript(
                message,
                {
                    "user": tse.MemberAdapter(member),
                    "moderator": tse.MemberAdapter(author),
                    "reason": tse.StringAdapter(str(reason)),
                    "guild": tse.GuildAdapter(guild),
                },
            )
            if not kwargs:
                await self._config.guild(ctx.guild).kick_message.clear()
                kwargs = process_tagscript(
                    kick_message,
                    {
                        "user": tse.MemberAdapter(member),
                        "moderator": tse.MemberAdapter(author),
                        "reason": tse.StringAdapter(str(reason)),
                        "guild": tse.GuildAdapter(guild),
                    },
                )
            await ctx.send(**kwargs)

    @commands.hybrid_command()
    @app_commands.describe(
        user="The member to ban.",
        reason="The reason for banning the user.",
        days="The number of days of messages to delete.",
    )
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        user: discord.Member,
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Ban a user from this server and optionally delete days of messages.

        `days` is the amount of days of messages to cleanup on ban.

        Examples:
           - `[p]ban 428675506947227648 7 Continued to spam after told to stop.`
            This will ban the user with ID 428675506947227648 and it will delete 7 days worth of messages.
           - `[p]ban @Twentysix 7 Continued to spam after told to stop.`
            This will ban Twentysix and it will delete 7 days worth of messages.

        A user ID should be provided if the user is not a member of this server.
        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. If not specified, the defaultdays setting will be used instead.
        """
        require_reason = await self._config.guild(ctx.guild).require_reason()
        if require_reason and reason is None:
            await ctx.send("You must provide a reason for this action.")
            return
        guild = ctx.guild
        if days is None:
            days = await self.config.guild(guild).default_days()
        if isinstance(user, int):
            user = self.bot.get_user(user) or discord.Object(id=user)

        success, message = await self.ban_user(
            user=user, ctx=ctx, days=days, reason=reason, create_modlog_case=True
        )

        if not success:
            await ctx.send(message)
            return

        kwargs = process_tagscript(
            message,
            {
                "user": tse.MemberAdapter(user),
                "moderator": tse.MemberAdapter(ctx.author),
                "reason": tse.StringAdapter(str(reason)),
                "guild": tse.GuildAdapter(guild),
                "days": tse.IntAdapter(int(days)),
            },
        )
        if not kwargs:
            await self._config.guild(ctx.guild).ban_message.clear()
            kwargs = process_tagscript(
                ban_message,
                {
                    "user": tse.MemberAdapter(user),
                    "moderator": tse.MemberAdapter(ctx.author),
                    "reason": tse.StringAdapter(str(reason)),
                    "guild": tse.GuildAdapter(guild),
                    "days": tse.IntAdapter(int(days)),
                },
            )

        await ctx.send(**kwargs)

    ban_user = None

    async def ban_user(
        self,
        user: Union[discord.Member, discord.User, discord.Object],
        ctx: commands.Context,
        days: int = 0,
        reason: str = None,
        create_modlog_case=False,
    ) -> Tuple[bool, str]:
        author = ctx.author
        guild = ctx.guild

        removed_temp = False

        if not (0 <= days <= 7):
            return False, ("Invalid days. Must be between 0 and 7.")

        if isinstance(user, discord.Member):
            if author == user:
                return (
                    False,
                    ("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}"),
                )
            elif not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
                return (
                    False,
                    (
                        "I cannot let you do that. You are "
                        "not higher than the user in the role "
                        "hierarchy."
                    ),
                )
            elif guild.me.top_role <= user.top_role or user == guild.owner:
                return False, ("I cannot do that due to Discord hierarchy rules.")

            toggle = await self.config.guild(guild).dm_on_kickban()
            if toggle:
                with contextlib.suppress(discord.HTTPException):
                    em = discord.Embed(
                        title=bold(("You have been banned from {guild}.").format(guild=guild)),
                        color=await self.bot.get_embed_color(user),
                    )
                    em.add_field(
                        name=("**Reason**"),
                        value=reason if reason is not None else ("No reason was given."),
                        inline=False,
                    )
                    await user.send(embed=em)

            ban_type = "ban"
        else:
            tempbans = await self.config.guild(guild).current_tempbans()

            try:
                await guild.fetch_ban(user)
            except discord.NotFound:
                pass
            else:
                if user.id in tempbans:
                    async with self.config.guild(guild).current_tempbans() as tempbans:
                        tempbans.remove(user.id)
                    removed_temp = True
                else:
                    return (
                        False,
                        ("User with ID {user_id} is already banned.").format(user_id=user.id),
                    )

            ban_type = "hackban"

        audit_reason = get_audit_reason(author, reason, shorten=True)

        if removed_temp:
            log.info(
                "{}({}) upgraded the tempban for {} to a permaban.".format(
                    author.name, author.id, user.id
                )
            )
            success_message = (
                "User with ID {user(id)} was upgraded from a temporary to a permanent ban."
            )
        else:
            username = user.name if hasattr(user, "name") else "Unknown"
            try:
                await guild.ban(user, reason=audit_reason, delete_message_days=days)
                log.info(
                    "{}({}) {}ned {}({}), deleting {} days worth of messages.".format(
                        author.name, author.id, ban_type, username, user.id, str(days)
                    )
                )
                success_message = await self._config.guild(ctx.guild).ban_message()
            except discord.Forbidden:
                return False, ("I'm not allowed to do that.")
            except discord.NotFound:
                return False, ("User with ID {user_id} not found").format(user_id=user.id)
            except Exception:
                log.exception(
                    "{}({}) attempted to {} {}({}), but an error occurred.".format(
                        author.name, author.id, ban_type, username, user.id
                    )
                )
                return False, ("An unexpected error occurred.")
        if create_modlog_case:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                ban_type,
                user,
                author,
                reason,
                until=None,
                channel=None,
            )

        return True, success_message

    unban = None

    @commands.hybrid_command()
    @app_commands.describe(
        user_id="The ID of the user to unban.", reason="The reason for unbanning the user."
    )
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def unban(
        self, ctx: commands.Context, user_id: RawUserIdConverter, *, reason: str = None
    ):
        """Unban a user from this server.
        Requires specifying the target user's ID. To find this, you may either:
         1. Copy it from the mod log case (if one was created), or
         2. enable developer mode, go to Bans in this server's settings, right-
        click the user and select 'Copy ID'."""
        require_reason = await self._config.guild(ctx.guild).require_reason()
        if require_reason and reason is None:
            await ctx.send("You must provide a reason for this action.")
            return
        guild = ctx.guild
        author = ctx.author
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        try:
            ban_entry = await guild.fetch_ban(discord.Object(user_id))
        except discord.NotFound:
            await ctx.send(("It seems that user isn't banned!"))
            return
        try:
            await guild.unban(ban_entry.user, reason=audit_reason)
        except discord.HTTPException:
            await ctx.send(("Something went wrong while attempting to unban that user."))
            return
        else:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "unban",
                ban_entry.user,
                author,
                reason,
                until=None,
                channel=None,
            )
            message = await self._config.guild(ctx.guild).unban_message()
            kwargs = process_tagscript(
                message,
                {
                    "user": tse.MemberAdapter(ban_entry.user),
                    "moderator": tse.MemberAdapter(author),
                    "reason": tse.StringAdapter(str(reason)),
                    "guild": tse.GuildAdapter(guild),
                },
            )
            if not kwargs:
                await self._config.guild(ctx.guild).unban_message.clear()
                kwargs = process_tagscript(
                    ban_message,
                    {
                        "user": tse.MemberAdapter(user),
                        "moderator": tse.MemberAdapter(ctx.author),
                        "reason": tse.StringAdapter(str(reason)),
                        "guild": tse.GuildAdapter(guild),
                    },
                )
            await ctx.send(**kwargs)

        if await self.config.guild(guild).reinvite_on_unban():
            user = ctx.bot.get_user(user_id)
            if not user:
                await ctx.send(
                    ("I don't share another server with this user. I can't reinvite them.")
                )
                return

            invite = await self.get_invite_for_reinvite(ctx)
            if invite:
                try:
                    await user.send(
                        (
                            "You've been unbanned from {server}.\n"
                            "Here is an invite for that server: {invite_link}"
                        ).format(server=guild.name, invite_link=invite)
                    )
                except discord.Forbidden:
                    await ctx.send(
                        (
                            "I failed to send an invite to that user. "
                            "Perhaps you may be able to send it for me?\n"
                            "Here's the invite link: {invite_link}"
                        ).format(invite_link=invite)
                    )
                except discord.HTTPException:
                    await ctx.send(
                        (
                            "Something went wrong when attempting to send that user "
                            "an invite. Here's the link so you can try: {invite_link}"
                        ).format(invite_link=invite)
                    )
