from .nsfw import NSFW

def setup(bot):
    bot.add_cog(NSFW(bot))
