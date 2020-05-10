# https://github.com/panley01/misc-cord/blob/master/misccord/flags.py

import inspect
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

STAFF = 1
PARTNER = 1 << 1
HYPESQUAD_EVENTS = 1 << 2
BUG_HUNTER = 1 << 3
HYPESQUAD_BRAVERY = 1 << 6
HYPESQUAD_BRILLIANCE = 1 << 7
HYPESQUAD_BALANCE = 1 << 8
EARLY_SUPPORTER = 1 << 9
TEAM_USER = 1 << 10
SYSTEM = 1 << 12
BUG_HUNTER_2 = 1 << 14
VERIFIED_BOT = 1 << 16
VERIFIED_DEVELOPER = 1 << 17

EMOJIS = {
    "staff": 706198524156706917,
    "early_supporter": 706198530837970998,
    "hypesquad_balance": 706198531538550886,
    "hypesquad_bravery": 706198532998299779,
    "hypesquad_briliance": 706198535846101092,
    "hypesquad_events": 706198537049866261,
    "verified_developer": 706198727953612901,
    "bug_hunter": 706199712402898985,
    "bug_hunter_2": 706199774616879125,
    "partner": 706206032216457258,
}


class HypeSquadHouse(Enum):
    """An enum representing the 3 houses which HypeSquad members may be in."""

    BRAVERY = "bravery"
    BRILLIANCE = "brilliance"
    BALANCE = "balance"


class Flags:
    """
    Flags from a Discord user.
    Represents the flags returned from the Discord API in integer form
    as a class with attributes representing each flag.
    Attributes
    -----------
    list: :class:`list`
        A python list object of all flags the user has.
    """

    def __init__(self, flags: int) -> None:
        """Create a new Flags instance."""
        if not isinstance(flags, int):
            raise ValueError("flags must be an integer from the Discord API.")

        self.flags = flags

    def enabled(self) -> List[Tuple[str, bool]]:
        """
        Return a list of enabled flags on the value.
        :rtype: list[tuple[str, bool]]
        """
        flags = []

        for name, value in inspect.getmembers(self):
            if name.startswith("_"):
                continue

            if isinstance(value, bool):
                if value:
                    flags.append(name)

        return flags

    def __iter__(self) -> List[Tuple[str, bool]]:
        """
        Return a list of enabled flags on the value.
        Under the hood this just calls the enabled method.
        :rtype: list[tuple[str, bool]]
        """
        for flag in self.enabled():
            yield flag

    # Flag bitwise checks

    @property
    def staff(self) -> bool:
        """Discord staff."""
        return (self.flags & STAFF) == STAFF

    @property
    def partner(self) -> bool:
        """Discord Partner."""
        return (self.flags & PARTNER) == PARTNER

    @property
    def hypesquad_events(self) -> bool:
        """Hypesquad events."""
        return (self.flags & HYPESQUAD_EVENTS) == HYPESQUAD_EVENTS

    @property
    def bug_hunter(self) -> bool:
        """Bug Hunter (Level 1)."""
        return (self.flags & BUG_HUNTER) == BUG_HUNTER

    @property
    def hypesquad_bravery(self) -> bool:
        """Hypesquad Bravery."""
        return (self.flags & HYPESQUAD_BRAVERY) == HYPESQUAD_BRAVERY

    @property
    def hypesquad_brilliance(self) -> bool:
        """Hypesquad Brilliance."""
        return (self.flags & HYPESQUAD_BRILLIANCE) == HYPESQUAD_BRILLIANCE

    @property
    def hypesquad_balance(self) -> bool:
        """Hypesquad Balance."""
        return (self.flags & HYPESQUAD_BALANCE) == HYPESQUAD_BALANCE

    @property
    def early_supporter(self) -> bool:
        """Early supporter."""
        return (self.flags & EARLY_SUPPORTER) == EARLY_SUPPORTER

    # @property
    # def team_user(self) -> bool:
    #     """Team user."""
    #     return (self.flags & TEAM_USER) == TEAM_USER

    # @property
    # def system(self) -> bool:
    #     """System user."""
    #     return (self.flags & SYSTEM) == SYSTEM

    @property
    def bug_hunter_2(self) -> bool:
        """Bug Hunter (Level 2)."""
        return (self.flags & BUG_HUNTER_2) == BUG_HUNTER_2

    # @property
    # def verified_bot(self) -> bool:
    #     """Verified Bot."""  # noqa: D401
    #     return (self.flags & VERIFIED_BOT) == VERIFIED_BOT

    @property
    def verified_developer(self) -> bool:
        """Verified Developer."""  # noqa: D401
        return (self.flags & VERIFIED_DEVELOPER) == VERIFIED_DEVELOPER

    # Utility properties

    @property
    def hypesquad_house(self) -> Optional[HypeSquadHouse]:
        """Return hypesquad house of the flags."""
        if self.hypesquad_balance:
            return HypeSquadHouse.BALANCE
        elif self.hypesquad_brilliance:
            return HypeSquadHouse.BRILLIANCE
        elif self.hypesquad_bravery:
            return HypeSquadHouse.BRAVERY


def flags_from_json(user_json: Dict[str, Any]) -> Flags:
    """
    Convert a Discord API user object to a Flags instance.
    Takes in the JSON user from the Discord API response and
    searches for flags and public_flags within this.
    :param user_json: The JSON response from the Discord API.
    :type user_json: dict
    """
    flags = 0

    if "flags" in user_json:
        flags |= int(user_json["flags"])

    if "public_flags" in user_json:
        flags |= int(user_json["public_flags"])

    return Flags(flags)


async def discord_py(user) -> Flags:  # noqa: ANN001
    """
    Fetch the flags from a Discord.py user object.
    :param user: The user or member from discord.py
    :rtype: Flags
    """
    user_json = await user._state.http.get_user(user.id)
    return flags_from_json(user_json)
