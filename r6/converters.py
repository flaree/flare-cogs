from redbot.core.commands import Conext, BadArguement
import r6statsapi

PLATFORMS = {
            "psn": r6statsapi.Platform.psn,
            "ps4": r6statsapi.Platform.psn,
            "ps": r6statsapi.Platform.psn,
            "xbl": r6statsapi.Platform.xbox,
            "xbox": r6statsapi.Platform.xbox,
            "uplay": r6statsapi.Platform.uplay,
            "pc": r6statsapi.Platform.uplay,
        }

class PlatformConverter:


    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        if arguement in PLATFORMS: 
			return cls(PLATFORMS[arguement])
		raise BadArguement("Platform isn't found, please specify either psn, xbox or pc.")