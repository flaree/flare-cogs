from .redditpost import RedditPost

__red_end_user_data_statement__ = "This cog does not persistently store data about users."


async def setup(bot):
    cog = RedditPost(bot)
    bot.add_cog(cog)
