from .pokecordnotifier import PokecordNotifier


def setup(bot):
    bot.add_cog(PokecordNotifier(bot))
