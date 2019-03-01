from .highlight import Highlight


def setup(bot):
    bot.add_cog(Highlight(bot))
