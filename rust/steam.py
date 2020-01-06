from redbot.core.commands import BadArgument
from redbot.core.i18n import Translator
from valve.steam.api.interface import API
from valve.steam.id import SteamID
from valve.steam.id import SteamIDError

_ = Translator("SteamCommunity", __file__)


class SteamUser:
    """SteamCommunity profile"""

    def __init__(self, steam: API, player_id: str):
        self._steam = steam
        self._user = self._steam["ISteamUser"]
        self._userdata = self._user.GetPlayerSummaries(player_id)["response"]["players"][0]
        self.steamid64 = self._userdata.get("steamid")
        self.personaname = self._userdata.get("personaname")
        self.realname = self._userdata.get("realname")
        self.avatar184 = self._userdata.get("avatarfull")

    @classmethod
    async def convert(cls, ctx, argument):
        steam = ctx.cog.steam
        if "ISteamUser" not in list(steam._interfaces.keys()):
            raise BadArgument(_("ApiKey not set or incorrect."))
        userapi = steam["ISteamUser"]
        if argument.startswith("http"):
            argument = argument.strip("/").split("/")[-1]
        if argument.isdigit():
            id64 = argument
        else:
            if argument.startswith("STEAM_"):
                try:
                    id64 = SteamID.from_text(argument).as_64()
                except SteamIDError:
                    raise BadArgument(_("Incorrect SteamID32 provided."))
            else:
                id64 = userapi.ResolveVanityURL(argument)["response"].get("steamid", "")
        if not id64.isnumeric():
            raise BadArgument(_("User with SteamID {} not found.").format(argument))
        try:
            profile = await ctx.bot.loop.run_in_executor(None, SteamUser, steam, id64)
        except IndexError:
            raise BadArgument(
                _(
                    "Unable to get profile for {} ({}). " "Check your input or try again later."
                ).format(argument, id64)
            )
        return profile
