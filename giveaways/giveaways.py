import asyncio
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.commands.converter import TimedeltaConverter

from .converter import Args
from .models import Giveaway, StatusMessage

log = logging.getLogger("red.flare.giveaways")
GIVEAWAY_KEY = "giveaways"

# TODO: Add a way to delete giveaways that have ended from the config


class Giveaways(commands.Cog):
    """Giveaway Commands"""

    __version__ = "0.2.0"
    __author__ = "flare"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808)
        self.config.init_custom(GIVEAWAY_KEY, 2)
        self.giveaways = {}
        self.giveaway_bgloop = asyncio.create_task(self.init())

    async def init(self) -> None:
        await self.bot.wait_until_ready()
        data = await self.config.custom(GIVEAWAY_KEY).all()
        for _, giveaways in data.items():
            for msgid, giveaway in giveaways.items():
                if datetime.now(timezone.utc) > datetime.fromtimestamp(
                    giveaway["endtime"]
                ).replace(tzinfo=timezone.utc):
                    continue
                self.giveaways[int(msgid)] = Giveaway(
                    guildid=giveaway["guildid"],
                    channelid=giveaway["channelid"],
                    messageid=msgid,
                    endtime=datetime.fromtimestamp(giveaway["endtime"]).replace(
                        tzinfo=timezone.utc
                    ),
                    prize=giveaway["prize"],
                    entrants=giveaway["entrants"],
                    **giveaway["kwargs"],
                )
        while True:
            try:
                await self.check_giveaways()
            except Exception as exc:
                log.error("Exception in bg_loop: ", exc_info=exc)
            await asyncio.sleep(60)

    def cog_unload(self) -> None:
        self.giveaway_bgloop.cancel()

    async def check_giveaways(self) -> None:
        to_clear = []
        for msgid, giveaway in self.giveaways.items():
            if giveaway.endtime < datetime.now(timezone.utc):
                await self.draw_winner(giveaway)
                to_clear.append(msgid)
        for msgid in to_clear:
            del self.giveaways[msgid]

    async def draw_winner(self, giveaway: Giveaway) -> StatusMessage:
        guild = self.bot.get_guild(giveaway.guildid)
        if guild is None:
            return StatusMessage.GuildNotFound
        channel_obj = guild.get_channel(giveaway.channelid)
        if channel_obj is None:
            return StatusMessage.ChannelNotFound

        winner, status = giveaway.draw_winner()
        if winner is None:
            winner_obj = None
            if status == StatusMessage.NotEnoughEntries:
                txt = "Not enough entries to roll the giveaway."
        else:
            winner_obj = guild.get_member(winner)
            if winner_obj is None:
                txt = f"Winner: {winner} (Not Found)"
            else:
                txt = f"Winner: {winner_obj.mention}!"

        msg = channel_obj.get_partial_message(giveaway.messageid)
        if msg is None:
            return StatusMessage.MessageNotFound
        embed = discord.Embed(
            title="Giveaway",
            description=f"{giveaway.prize}\n\n{txt}",
            color=await self.bot.get_embed_color(channel_obj),
            timestamp=giveaway.endtime,
        )
        embed.set_footer(
            text=f"Reroll: {(await self.bot.get_prefix(msg))[-1]}gw reroll {giveaway.messageid} | Ended at"
        )
        await msg.edit(content=winner_obj.mention if winner_obj is not None else "", embed=embed)
        await msg.clear_reactions()
        if winner_obj is not None:
            async with self.config.custom(
                GIVEAWAY_KEY, giveaway.guildid, int(giveaway.messageid)
            ).entrants() as entrants:
                entrants = [x for x in entrants if x != winner]
        return StatusMessage.WinnerDrawn

    @commands.group(aliases=["gw"])
    @commands.bot_has_permissions(add_reactions=True, manage_messages=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context):
        """
        Manage the giveaway system
        """

    @giveaway.command()
    async def start(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        time: TimedeltaConverter(default_unit="minutes"),
        *,
        prize: str,
    ):
        """
        Start a giveaway
        """
        channel = channel or ctx.channel
        end = datetime.now(timezone.utc) + time
        embed = discord.Embed(
            title="Giveaway",
            description=f"{prize}\n\nReact with 🎉 to enter\nEnds: <t:{int(end.timestamp())}:R>",
            color=await ctx.embed_color(),
        )
        msg = await channel.send(embed=embed)
        giveaway_obj = Giveaway(ctx.guild.id, channel.id, msg.id, end, prize)
        self.giveaways[msg.id] = giveaway_obj
        await msg.add_reaction("🎉")
        giveaway_dict = deepcopy(giveaway_obj.__dict__)
        giveaway_dict["endtime"] = giveaway_dict["endtime"].timestamp()
        await self.config.custom(GIVEAWAY_KEY, str(ctx.guild.id), str(msg.id)).set(giveaway_dict)

    @giveaway.command()
    async def reroll(self, ctx: commands.Context, msgid: int):
        """Reroll a giveaway."""
        data = await self.config.custom(GIVEAWAY_KEY, ctx.guild.id).all()
        if str(msgid) not in data:
            return await ctx.send("Giveaway not found.")
        if msgid in self.giveaways:
            return await ctx.send(
                f"Giveaway already running. Please wait for it to end or end it via `{ctx.clean_prefix}gw end {msgid}`."
            )
        giveaway = Giveaway(**data[str(msgid)])
        status = await self.draw_winner(giveaway)
        if status == StatusMessage.WinnerDrawn:
            await ctx.tick()
        elif status == StatusMessage.GuildNotFound:
            await ctx.send("Giveaway guild not found.")
        elif status == StatusMessage.ChannelNotFound:
            await ctx.send("Giveaway channel not found.")
        elif status == StatusMessage.MessageNotFound:
            await ctx.send("Giveaway message not found.")

    @giveaway.command()
    async def end(self, ctx: commands.Context, msgid: int):
        """End a giveaway."""
        if msgid in self.giveaways:
            await self.draw_winner(self.giveaways[msgid])
            del self.giveaways[msgid]
            await ctx.tick()
        else:
            await ctx.send("Giveaway not found.")

    @giveaway.command(aliases=["adv"])
    async def advanced(self, ctx: commands.Context, *, arguments: Args):
        """Advanced creation of Giveaways.


        Required arguments:
        `--prize`: The prize to be won.
        `--duration`: The duration of the giveaway.

        Optional arguments:
        `--channel`: The channel ID to post the giveaway in. Will default to this channel if not specified.
        `--restrict`: Roles that the giveaway will be restricted to. Must be IDs.
        `--multiplier`: Multiplier for those in specified roles.
        `--multi-roles`: Roles that will receive the multiplier. Must be IDs.
        `--cost`: Cost of credits to enter the giveaway.
        `--joined`: How long the user must be a member of the server for to enter the giveaway.
        `--created`: How long the user has been on discord for to enter the giveaway.
        `--blacklist`: Blacklisted roles that cannot enter the giveaway. Must be IDs.


        3rd party integrations:
        `--level-req`: The level required to enter the giveaway. Must be Fixator's leveler cog.

        Examples:
        gw advanced --prize A new sword --duration 1h30m --restrict Role ID --multiplier 2 --multi-roles RoleID RoleID2


        """
        prize = arguments["prize"]
        duration = arguments["duration"]
        channel = arguments["channel"] or ctx.channel

        end = datetime.now(timezone.utc) + duration
        embed = discord.Embed(
            title="Giveaway",
            description=f"{prize}\n\nReact with 🎉 to enter\nEnds: <t:{int(end.timestamp())}:R>",
            color=await ctx.embed_color(),
        )
        msg = await channel.send(embed=embed)
        giveaway_obj = Giveaway(
            ctx.guild.id,
            channel.id,
            msg.id,
            end,
            prize,
            **{k: v for k, v in arguments.items() if k not in ["prize", "duration", "channel"]},
        )
        self.giveaways[msg.id] = giveaway_obj
        await msg.add_reaction("🎉")
        giveaway_dict = deepcopy(giveaway_obj.__dict__)
        giveaway_dict["endtime"] = giveaway_dict["endtime"].timestamp()
        await self.config.custom(GIVEAWAY_KEY, str(ctx.guild.id), str(msg.id)).set(giveaway_dict)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id in self.giveaways:
            giveaway = self.giveaways[payload.message_id]
            status, msg = await giveaway.add_entrant(payload.member, bot=self.bot)
            if not status:
                if msg == StatusMessage.UserAlreadyEntered:
                    await payload.member.send(f"You have already entered this giveaway.")
                elif msg == StatusMessage.UserNotInRole:
                    await payload.member.send(
                        f"You are not in the required role(s) for this giveaway."
                    )
                elif msg == StatusMessage.UserDoesntMeetLevel:
                    await payload.member.send(
                        f"You do not meet the level requirement for this giveaway."
                    )
                elif msg == StatusMessage.UserNotEnoughCredits:
                    await payload.member.send(
                        f"You do not have enough credits to enter this giveaway."
                    )
                elif msg == StatusMessage.UserAccountTooYoung:
                    await payload.member.send(
                        f"Your account does not meet the age critera for this giveaway."
                    )
                elif msg == StatusMessage.UserNotMemberLongEnough:
                    await payload.member.send(
                        f"You have not been a member of the server long enough for this giveaway."
                    )
                elif msg == StatusMessage.UserInBlacklistedRole:
                    await payload.member.send(
                        f"You are in a blacklisted role for this giveaway and thus cannot enter."
                    )
                return
            await self.config.custom(
                GIVEAWAY_KEY, payload.guild_id, payload.message_id
            ).entrants.set(self.giveaways[payload.message_id].entrants)
