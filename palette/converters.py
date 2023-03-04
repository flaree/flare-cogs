# Taken and modified from Trustys NotSoBot cog.
import re

from redbot.core.commands import BadArgument, Converter

_id_regex = re.compile(r"([0-9]{15,21})$")
_mention_regex = re.compile(r"<@!?([0-9]{15,21})>$")

IMAGE_LINKS = re.compile(r"(https?:\/\/[^\"\'\s]*\.(?:png|jpg|jpeg|gif|png|svg)(\?size=[0-9]*)?)")
EMOJI_REGEX = re.compile(r"(<(a)?:[a-zA-Z0-9\_]+:([0-9]+)>)")
MENTION_REGEX = re.compile(r"<@!?([0-9]+)>")
ID_REGEX = re.compile(r"[0-9]{17,}")


class ImageFinder(Converter):
    """This is a class to convert notsobots image searching capabilities into a more general
    converter class."""

    async def convert(self, ctx, argument):
        attachments = ctx.message.attachments
        mentions = MENTION_REGEX.finditer(argument)
        matches = IMAGE_LINKS.finditer(argument)
        emojis = EMOJI_REGEX.finditer(argument)
        ids = ID_REGEX.finditer(argument)
        urls = []
        if matches:
            urls.extend(match.group(1) for match in matches)
        if emojis:
            for emoji in emojis:
                ext = "gif" if emoji.group(2) else "png"
                url = "https://cdn.discordapp.com/emojis/{id}.{ext}?v=1".format(
                    id=emoji.group(3), ext=ext
                )
                urls.append(url)
        if mentions:
            for mention in mentions:
                user = ctx.guild.get_member(int(mention.group(1)))
                if user is not None:
                    url = IMAGE_LINKS.search(str(user.display_avatar))
                    urls.append(url.group(1))
        if not urls and ids:
            for possible_id in ids:
                if user := ctx.guild.get_member(int(possible_id.group(0))):
                    url = IMAGE_LINKS.search(str(user.display_avatar))
                    urls.append(url.group(1))
        if attachments:
            urls.extend(attachment.url for attachment in attachments)
        if not urls and ctx.guild:
            if user := ctx.guild.get_member_named(argument):
                url = user.display_avatar
                urls.append(url)
        if not urls:
            raise BadArgument("No images found.")
        return urls[0]
