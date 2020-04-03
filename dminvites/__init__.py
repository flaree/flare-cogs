from .dminvites import DmInvite


def setup(bot):
    bot.add_cog(DmInvite(bot))
