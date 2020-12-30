from redbot.core import commands


@commands.group(name="embed")
async def embed(self, ctx: commands.Context):
    """
    EmbedCreator commands
    """


class EmbedMixin:
    """ This is mostly here to easily mess with things... """

    c = embed
