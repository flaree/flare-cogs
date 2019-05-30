from .updatenotify import UpdateNotify


def setup(bot):
    bot.add_cog(UpdateNotify(bot))
