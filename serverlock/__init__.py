from .serverlock import ServerLock

def setup(bot):
    bot.add_cog(ServerLock(bot))