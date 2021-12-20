import random
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple

import discord


class StatusMessage(Enum):
    UserAlreadyEntered = 0
    UserNotInRole = 1
    UserEntered = 2
    NotEnoughEntries = 3
    WinningUser = 4
    GuildNotFound = 5
    ChannelNotFound = 6
    MessageNotFound = 7
    UserNotFound = 8
    WinnerDrawn = 9
    LevelCogNotFound = 10
    UserDoesntMeetLevel = 11


class Giveaway:
    def __init__(
        self,
        guildid: int,
        channelid: int,
        messageid: int,
        endtime: datetime,
        prize: str = None,
        *,
        entrants=None,
        **kwargs,
    ) -> None:
        self.guildid = guildid
        self.channelid = channelid
        self.messageid = messageid
        self.endtime = endtime
        self.prize = prize
        self.entrants = entrants or []
        self.kwargs = kwargs

    async def add_entrant(self, user: discord.Member, *, bot) -> Tuple[bool, StatusMessage]:
        if user.id in self.entrants:
            return False, StatusMessage.UserAlreadyEntered
        if self.kwargs.get("exclusive", []) and not any(
            int(role) in [x.id for x in user.roles] for role in self.kwargs.get("exclusive", [])
        ):
            return False, StatusMessage.UserNotInRole
        # if self.kwargs.get("levelreq", None) is not None:
        #     cog = self.bot.get_cog("Leveler")
        #     if cog is None:
        #         return False, StatusMessage.LevelCogNotFound
        #     userinfo = await cog.db.users.find_one({"user_id": str(user.id)})
        #     lvl = userinfo.get("servers", {}).get(str(self.guildid), {}).get("level", 0)
        #     if lvl < self.kwargs.get("levelreq", 0):
        #         return False, StatusMessage.UserDoesntMeetLevel

        self.entrants.append(user.id)
        if self.kwargs.get("multi", None) is not None and any(
            int(role) in [x.id for x in user.roles] for role in self.kwargs.get("multi-roles", [])
        ):
            for _ in range(self.kwargs["multi"] - 1):
                self.entrants.append(user.id)
        return True, StatusMessage.UserEntered

    def remove_entrant(self, userid: int) -> None:
        self.entrants = [x for x in self.entrants if x != userid]

    def draw_winner(self) -> Tuple[Optional[discord.Member], StatusMessage]:
        if len(self.entrants) == 0:
            return None, StatusMessage.NotEnoughEntries
        winner = random.choice(self.entrants)
        self.remove_entrant(winner)
        return winner, StatusMessage.WinningUser

    def __str__(self) -> str:
        return f"{self.prize} - {self.endtime}"
