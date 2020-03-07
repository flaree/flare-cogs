from .covid import Covid

def setup(bot):
    bot.add_cog(Covid(bot))