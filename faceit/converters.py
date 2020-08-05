import re

from discord.ext.commands.converter import Converter
from discord.ext.commands.errors import BadArgument

MENTION_REGEX = re.compile(r"<@!?([0-9]+)>")
ID_REGEX = re.compile(r"[0-9]{17,}")


class StrUser(Converter):
    """This is a class to convert mentions/ids to users or return a string."""

    async def convert(self, ctx, argument):
        mentions = MENTION_REGEX.finditer(argument)
        ids = ID_REGEX.finditer(argument)
        users = []
        if mentions:
            for mention in mentions:
                user = ctx.bot.get_user(int(mention.group(1)))
                if user:
                    users.append(user)
        if not users and ids:
            for possible_id in ids:
                user = ctx.bot.get_user(int(possible_id.group(0)))
                if user:
                    users.append(user)
        if not users:
            raise BadArgument("No user provided.")
        return users[0]
