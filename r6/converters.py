import r6statsapi
from redbot.core.commands import BadArgument, Context

PLATFORMS = {
    "psn": r6statsapi.Platform.psn,
    "ps4": r6statsapi.Platform.psn,
    "ps": r6statsapi.Platform.psn,
    "xbl": r6statsapi.Platform.xbox,
    "xbox": r6statsapi.Platform.xbox,
    "uplay": r6statsapi.Platform.uplay,
    "pc": r6statsapi.Platform.uplay,
}

REGIONS = {
    "all": r6statsapi.Regions.all,
    "na": r6statsapi.Regions.ncsa,
    "eu": r6statsapi.Regions.emea,
    "asia": r6statsapi.Regions.apac,
    "us": r6statsapi.Regions.ncsa,
    "as": r6statsapi.Regions.apac,
    "europe": r6statsapi.Regions.emea,
}


class PlatformConverter:
    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        if argument.lower() in PLATFORMS:
            return PLATFORMS[argument.lower()]
        raise BadArgument("Platform isn't found, please specify either psn, xbox or pc.")


class RegionConverter:
    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        if argument.lower() in REGIONS:
            return REGIONS[argument.lower()]
        raise BadArgument("Region not found, please specify either na, eu or asia.")
