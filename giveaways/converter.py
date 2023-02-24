import argparse
from datetime import datetime, timezone

import dateparser
from discord.ext.commands.converter import EmojiConverter, RoleConverter, TextChannelConverter
from redbot.core.commands import BadArgument, Converter
from redbot.core.commands.converter import TimedeltaConverter


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class Args(Converter):
    async def convert(self, ctx, argument):
        argument = argument.replace("—", "--")
        parser = NoExitParser(description="Giveaway Created", add_help=False)

        # Required Arguments

        parser.add_argument("--prize", "--p", dest="prize", nargs="*", default=[])

        timer = parser.add_mutually_exclusive_group()
        timer.add_argument("--duration", "--d", dest="duration", nargs="*", default=[])
        timer.add_argument("--end", "--e", dest="end", nargs="*", default=[])

        # Optional Arguments
        parser.add_argument("--channel", dest="channel", default=None, nargs="?")
        parser.add_argument("--roles", "--r", "--restrict", dest="roles", nargs="*", default=[])
        parser.add_argument("--multiplier", "--m", dest="multi", default=None, type=int, nargs="?")
        parser.add_argument("--multi-roles", "--mr", nargs="*", dest="multi-roles", default=[])
        parser.add_argument("--joined", dest="joined", default=None, type=int, nargs="?")
        parser.add_argument("--created", dest="created", default=None, type=int, nargs="?")
        parser.add_argument("--blacklist", dest="blacklist", nargs="*", default=[])
        parser.add_argument("--winners", dest="winners", default=None, type=int, nargs="?")
        parser.add_argument("--mentions", dest="mentions", nargs="*", default=[])
        parser.add_argument("--description", dest="description", default=[], nargs="*")
        parser.add_argument("--emoji", dest="emoji", default=None, nargs="*")
        parser.add_argument("--image", dest="image", default=None, nargs="*")
        parser.add_argument("--thumbnail", dest="thumbnail", default=None, nargs="*")

        # Setting arguments
        parser.add_argument("--multientry", action="store_true")
        parser.add_argument("--notify", action="store_true")
        parser.add_argument("--congratulate", action="store_true")
        parser.add_argument("--announce", action="store_true")
        parser.add_argument("--ateveryone", action="store_true")
        parser.add_argument("--athere", action="store_true")
        parser.add_argument("--show-requirements", action="store_true")

        # Integrations
        parser.add_argument("--cost", dest="cost", default=None, type=int, nargs="?")
        parser.add_argument("--level-req", dest="levelreq", default=None, type=int, nargs="?")
        parser.add_argument("--rep-req", dest="repreq", default=None, type=int, nargs="?")
        parser.add_argument("--tatsu-level", default=None, type=int, nargs="?")
        parser.add_argument("--tatsu-rep", default=None, type=int, nargs="?")
        parser.add_argument("--mee6-level", default=None, type=int, nargs="?")
        parser.add_argument("--amari-level", default=None, type=int, nargs="?")
        parser.add_argument("--amari-weekly-xp", default=None, type=int, nargs="?")

        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as error:
            raise BadArgument(
                "Could not parse flags correctly, ensure flags are correctly used."
            ) from error

        if not vals["prize"]:
            raise BadArgument("You must specify a prize. Use `--prize` or `-p`")  #

        if not any([vals["duration"], vals["end"]]):
            raise BadArgument(
                "You must specify a duration or end date. Use `--duration` or `-d` or `--end` or `-e`"
            )

        nums = [vals["cost"], vals["joined"], vals["created"], vals["winners"]]
        for val in nums:
            if val is None:
                continue
            if val < 1:
                raise BadArgument("Number must be greater than 0")

        valid_multi_roles = []
        for role in vals["multi-roles"]:
            try:
                role = await RoleConverter().convert(ctx, role)
                valid_multi_roles.append(role.id)
            except BadArgument:
                raise BadArgument(f"The role {role} does not exist within this server.")
        vals["multi-roles"] = valid_multi_roles

        valid_exclusive_roles = []
        for role in vals["roles"]:
            try:
                role = await RoleConverter().convert(ctx, role)
                valid_exclusive_roles.append(role.id)
            except BadArgument:
                raise BadArgument(f"The role {role} does not exist within this server.")
        vals["roles"] = valid_exclusive_roles

        valid_blacklist_roles = []
        for role in vals["blacklist"]:
            try:
                role = await RoleConverter().convert(ctx, role)
                valid_blacklist_roles.append(role.id)
            except BadArgument:
                raise BadArgument(f"The role {role} does not exist within this server.")
        vals["blacklist"] = valid_blacklist_roles = []

        valid_mentions = []
        for role in vals["mentions"]:
            try:
                role = await RoleConverter().convert(ctx, role)
                valid_mentions.append(role.id)
            except BadArgument:
                raise BadArgument(f"The role {role} does not exist within this server.")
        vals["mentions"] = valid_mentions

        if vals["channel"]:
            try:
                vals["channel"] = await TextChannelConverter().convert(ctx, vals["channel"])
            except BadArgument:
                raise BadArgument("Invalid channel.")

        if vals["levelreq"] or vals["repreq"]:
            cog = ctx.bot.get_cog("Leveler")
            if not cog:
                raise BadArgument("Leveler cog not loaded.")
            if not hasattr(cog, "db"):
                raise BadArgument(
                    "This may be the wrong leveling cog. Ensure you are using Fixators."
                )

        if vals["tatsu_level"] or vals["tatsu_rep"]:
            token = await ctx.bot.get_shared_api_tokens("tatsumaki")
            if not token.get("authorization"):
                raise BadArgument(
                    f"You do not have a valid Tatsumaki API token. Check `{ctx.clean_prefix}gw integrations` for more info."
                )

        if vals["amari_level"] or vals["amari_weekly_xp"]:
            token = await ctx.bot.get_shared_api_tokens("amari")
            if not token.get("authorization"):
                raise BadArgument(
                    f"You do not have a valid Amari API token. Check `{ctx.clean_prefix}gw integrations` for more info."
                )

        if (vals["multi"] or vals["multi-roles"]) and not (vals["multi"] and vals["multi-roles"]):
            raise BadArgument(
                "You must specify a multiplier and roles. Use `--multiplier` or `-m` and `--multi-roles` or `-mr`"
            )

        if (
            (vals["ateveryone"] or vals["athere"])
            and not ctx.channel.permissions_for(ctx.me).mention_everyone
            and not ctx.channel.permissions_for(ctx.author).mention_everyone
        ):
            raise BadArgument(
                "You do not have permission to mention everyone. Please ensure the bot and you have `Mention Everyone` permission."
            )

        if vals["description"]:
            vals["description"] = " ".join(vals["description"])
            if len(vals["description"]) > 1000:
                raise BadArgument("Description must be less than 1000 characters.")

        if vals["emoji"]:
            vals["emoji"] = " ".join(vals["emoji"]).rstrip().lstrip()
            custom = False
            try:
                vals["emoji"] = await EmojiConverter().convert(ctx, vals["emoji"])
                custom = True
            except Exception:
                vals["emoji"] = str(vals["emoji"]).replace("\N{VARIATION SELECTOR-16}", "")
            try:
                await ctx.message.add_reaction(vals["emoji"])
                await ctx.message.remove_reaction(vals["emoji"], ctx.me)
            except Exception:
                raise BadArgument("Invalid emoji.")
            if custom:
                vals["emoji"] = vals["emoji"].id

        vals["prize"] = " ".join(vals["prize"])
        if vals["duration"]:
            tc = TimedeltaConverter()
            try:
                duration = await tc.convert(ctx, " ".join(vals["duration"]))
                vals["duration"] = duration
            except BadArgument:
                raise BadArgument("Invalid duration. Use `--duration` or `-d`")
            else:
                if duration.total_seconds() < 60:
                    raise BadArgument("Duration must be greater than 60 seconds.")
        else:
            try:
                time = dateparser.parse(" ".join(vals["end"]))
                if time.tzinfo is None:
                    time = time.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > time:
                    raise BadArgument("End date must be in the future.")
                time = time - datetime.now(timezone.utc)
                vals["duration"] = time
                if time.total_seconds() < 60:
                    raise BadArgument("End date must be at least 1 minute in the future.")
            except Exception:
                raise BadArgument(
                    "Invalid end date. Use `--end` or `-e`. Ensure to pass a timezone, otherwise it defaults to UTC."
                )
        vals["image"] = " ".join(vals["image"]) if vals["image"] else None
        vals["thumbnail"] = " ".join(vals["thumbnail"]) if vals["thumbnail"] else None
        return vals
