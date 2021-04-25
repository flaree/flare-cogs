from .apitools import ApiTools


def setup(bot):
    bot.add_cog(ApiTools(bot))
