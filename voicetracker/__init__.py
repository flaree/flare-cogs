from .voicetracker import VoiceTracker


async def setup(bot):
    await bot.add_cog(VoiceTracker(bot))
