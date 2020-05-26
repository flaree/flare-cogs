from .redditpost import RedditPost


def setup(bot):
    cog = RedditPost(bot)
    cog.init()
    bot.add_cog(cog)
