from .staff import Staff


def setup(bot):
    bot.add_cog(Staff(bot))
