from .embedcreator import EmbedCreator


def setup(bot):
    bot.add_cog(EmbedCreator(bot))
