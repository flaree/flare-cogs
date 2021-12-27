import argparse
from datetime import datetime, timezone

import dateparser
from discord.ext.commands.converter import RoleConverter, TextChannelConverter
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
        parser.add_argument("--restrict", "--r", dest="exclusive", nargs="*", default=[])
        parser.add_argument("--multiplier", "--m", dest="multi", default=None, type=int, nargs="?")
        parser.add_argument("--multi-roles", "--mr", nargs="*", dest="multi-roles", default=[])
        parser.add_argument("--cost", dest="cost", default=None, type=int, nargs="?")
        parser.add_argument("--joined", dest="joined", default=None, type=int, nargs="?")
        parser.add_argument("--created", dest="created", default=None, type=int, nargs="?")
        parser.add_argument("--blacklist", dest="blacklist", nargs="*", default=[])
        parser.add_argument("--winners", dest="winners", default=None, type=int, nargs="?")
        parser.add_argument("--mentions", dest="mentions", nargs="*", default=[])

        # Setting arguments
        parser.add_argument("--multientry", action="store_true")
        parser.add_argument("--notify", action="store_true")
        parser.add_argument("--congratulate", action="store_true")
        parser.add_argument("--announce", action="store_true")
        parser.add_argument("--ateveryone", action="store_true")

        # 3rd party arguments
        parser.add_argument(
            "--level-req", "--lq", dest="levelreq", default=None, type=int, nargs="?"
        )

        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as error:
            raise BadArgument() from error

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
        for role in vals["exclusive"]:
            try:
                role = await RoleConverter().convert(ctx, role)
                valid_exclusive_roles.append(role.id)
            except BadArgument:
                raise BadArgument(f"The role {role} does not exist within this server.")
        vals["multi-exclusive"] = valid_exclusive_roles

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

        if vals["levelreq"]:
            cog = ctx.bot.get_cog("Leveler")
            if not cog:
                raise BadArgument("Leveler cog not loaded.")
            if not hasattr(cog, "db"):
                raise BadArgument(
                    "This may be the wrong leveling cog. Ensure you are using Fixators."
                )

        if vals["multi"] or vals["multi-roles"]:
            if not (vals["multi"] and vals["multi-roles"]):
                raise BadArgument(
                    "You must specify a multiplier and roles. Use `--multiplier` or `-m` and `--multi-roles` or `-mr`"
                )

        vals["prize"] = " ".join(vals["prize"])
        if vals["duration"]:
            tc = TimedeltaConverter()
            try:
                vals["duration"] = await tc.convert(ctx, " ".join(vals["duration"]))
            except BadArgument:
                raise BadArgument("Invalid duration. Use `--duration` or `-d`")
        else:
            try:
                time = dateparser.parse(" ".join(vals["end"]))
                if time.tzinfo is None:
                    time = time.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > time:
                    raise BadArgument("End date must be in the future.")
                time = time - datetime.now(timezone.utc)
                vals["duration"] = time
            except Exception:
                raise BadArgument(
                    "Invalid end date. Use `--end` or `-e`. Ensure to pass a timezone, otherwise it defaults to UTC."
                )

        return vals
