from .voicetracker import VoiceTracker


def setup(bot):
    bot.add_cog(VoiceTracker(bot))
