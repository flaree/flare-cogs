from .weather import Weather


def setup(bot):
    bot.add_cog(Weather(bot))
