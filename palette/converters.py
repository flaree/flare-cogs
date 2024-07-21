# Taken and modified from Trusty's NotSoBot cog.
import re

import discord
from redbot.core.commands import BadArgument, Converter

IMAGE_LINKS = re.compile(r"(https?:\/\/[^\"\'\s]*\.(?:png|jpg|jpeg|gif|png|svg)(\?size=[0-9]*)?)")
EMOJI_REGEX = re.compile(r"(<(a)?:[a-zA-Z0-9\_]+:([0-9]+)>)")
MENTION_REGEX = re.compile(r"<@!?([0-9]+)>")
ID_REGEX = re.compile(r"[0-9]{17,}")


class ImageFinder(Converter):
    """This is a class to convert notsobots image searching capabilities into a more general
    converter class."""

    async def convert(self, ctx, argument):
        mentions = MENTION_REGEX.finditer(argument)
        matches = IMAGE_LINKS.finditer(argument)
        emojis = EMOJI_REGEX.finditer(argument)
        ids = ID_REGEX.finditer(argument)
        urls = []
        if matches:
            urls.extend(match.group(1) for match in matches)
        if emojis:
            for emoji in emojis:
                partial_emoji = discord.PartialEmoji.from_str(emoji.group(1))
                if partial_emoji.is_custom_emoji():
                    urls.append(partial_emoji.url)
                else:
                    try:
                        """https://github.com/glasnt/emojificate/blob/master/emojificate/filter.py"""
                        cdn_fmt = (
                            "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{codepoint:x}.png"
                        )
                        urls.append(cdn_fmt.format(codepoint=ord(str(emoji))))
                    except TypeError:
                        continue
        if mentions:
            for mention in mentions:
                if user := ctx.guild.get_member(int(mention.group(1))):
                    urls.append(str(user.display_avatar))
        if not urls and ids:
            for possible_id in ids:
                if user := ctx.guild.get_member(int(possible_id.group(0))):
                    urls.append(str(user.display_avatar))
        if not urls and ctx.guild:
            if user := ctx.guild.get_member_named(argument):
                urls.append(str(user.display_avatar))
        if not urls:
            raise BadArgument("No images found.")
        return urls[0]
