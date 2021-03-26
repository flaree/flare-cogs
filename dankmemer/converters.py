# Taken and modified from Trustys NotSoBot cog.

import re

from discord.ext.commands.converter import Converter
from discord.ext.commands.errors import BadArgument

IMAGE_LINKS = re.compile(r"(https?:\/\/[^\"\'\s]*\.(?:png|jpg|jpeg|gif|png|svg)(\?size=[0-9]*)?)")
MENTION_REGEX = re.compile(r"<@!?([0-9]+)>")
ID_REGEX = re.compile(r"[0-9]{17,}")


class ImageFinder(Converter):
    """This is a class to convert notsobots image searching capabilities into a more general
    converter class."""

    async def convert(self, ctx, argument):
        attachments = ctx.message.attachments
        mentions = MENTION_REGEX.finditer(argument)
        matches = IMAGE_LINKS.finditer(argument)
        ids = ID_REGEX.finditer(argument)
        urls = []
        if matches:
            for match in matches:
                urls.append(match.group(1))
        if mentions:
            for mention in mentions:
                user = ctx.guild.get_member(int(mention.group(1)))
                if user is not None:
                    if user.is_avatar_animated():
                        url = IMAGE_LINKS.search(str(user.avatar_url_as(format="gif")))
                    else:
                        url = IMAGE_LINKS.search(str(user.avatar_url_as(format="png")))
                    urls.append(url.group(1))
        if not urls and ids:
            for possible_id in ids:
                user = ctx.guild.get_member(int(possible_id.group(0)))
                if user:
                    if user.is_avatar_animated():
                        url = IMAGE_LINKS.search(str(user.avatar_url_as(format="gif")))
                    else:
                        url = IMAGE_LINKS.search(str(user.avatar_url_as(format="png")))
                    urls.append(url.group(1))
        if attachments:
            for attachment in attachments:
                urls.append(attachment.url)

        if not urls and ctx.guild:
            user = ctx.guild.get_member_named(argument)
            if not user:
                raise BadArgument("No images provided.")
            if user.is_avatar_animated():
                url = user.avatar_url_as(format="gif")
            else:
                url = user.avatar_url_as(format="png")
            urls.append(url)
        if not urls:
            raise BadArgument("No images provided.")
        return urls[0]
