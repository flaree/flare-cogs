import asyncio
import contextlib
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import discord
from redbot.core import Config, app_commands, commands
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .converter import Args
from .objects import Giveaway, GiveawayEnterError, GiveawayExecError

log = logging.getLogger("red.flare.giveaways")
GIVEAWAY_KEY = "giveaways"

# TODO: Add a way to delete giveaways that have ended from the config


class Giveaways(commands.Cog):
    """Giveaway Commands"""

    __version__ = "0.13.0"
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
        self.session = aiohttp.ClientSession()
        with contextlib.suppress(Exception):
            self.bot.add_dev_env_value("giveaways", lambda x: self)

    async def init(self) -> None:
        await self.bot.wait_until_ready()
        data = await self.config.custom(GIVEAWAY_KEY).all()
        for _, giveaways in data.items():
            for msgid, giveaway in giveaways.items():
                if giveaway.get("ended", False):
                    continue
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
                    emoji=giveaway.get("emoji", "🎉"),
                    entrants=giveaway["entrants"],
                    **giveaway["kwargs"],
                )
        while True:
            try:
                await self.check_giveaways()
            except Exception as exc:
                log.error("Exception in giveaway loop: ", exc_info=exc)
            await asyncio.sleep(15)

    def cog_unload(self) -> None:
        with contextlib.suppress(Exception):
            self.bot.remove_dev_env_value("giveaways")
        self.giveaway_bgloop.cancel()
        asyncio.create_task(self.session.close())

    async def check_giveaways(self) -> None:
        to_clear = []
        for msgid, giveaway in self.giveaways.items():
            if giveaway.endtime < datetime.now(timezone.utc):
                await self.draw_winner(giveaway)
                to_clear.append(msgid)
                gw = await self.config.custom(GIVEAWAY_KEY, giveaway.guildid, str(msgid)).all()
                gw["ended"] = True
                await self.config.custom(GIVEAWAY_KEY, giveaway.guildid, str(msgid)).set(gw)
        for msgid in to_clear:
            del self.giveaways[msgid]

    async def draw_winner(self, giveaway: Giveaway):
        guild = self.bot.get_guild(giveaway.guildid)
        if guild is None:
            return
        channel_obj = guild.get_channel(giveaway.channelid)
        if channel_obj is None:
            return

        winners = giveaway.draw_winner()
        winner_objs = None
        if winners is None:
            txt = "Not enough entries to roll the giveaway."
        else:
            winner_objs = []
            txt = ""
            for winner in winners:
                winner_obj = guild.get_member(winner)
                if winner_obj is None:
                    txt += f"{winner} (Not Found)\n"
                else:
                    txt += f"{winner_obj.mention}\n"
                    winner_objs.append(winner_obj)

        msg = channel_obj.get_partial_message(giveaway.messageid)
        winners = giveaway.kwargs.get("winners", 1) or 1
        embed = discord.Embed(
            title=f"{f'{winners}x ' if winners > 1 else ''}{giveaway.prize}",
            description=f"Winner(s):\n{txt}",
            color=await self.bot.get_embed_color(channel_obj),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(
            text=f"Reroll: {(await self.bot.get_prefix(msg))[-1]}gw reroll {giveaway.messageid} | Ended at"
        )
        try:
            await msg.edit(
                content="🎉 Giveaway Ended 🎉",
                embed=embed,
            )
        except (discord.NotFound, discord.Forbidden) as exc:
            log.error("Error editing giveaway message: ", exc_info=exc)
            async with self.config.custom(
                GIVEAWAY_KEY, giveaway.guildid, int(giveaway.messageid)
            ).entrants() as entrants:
                entrants = [x for x in entrants if x != winner]
            del self.giveaways[giveaway.messageid]
            gw = await self.config.custom(
                GIVEAWAY_KEY, giveaway.guildid, str(giveaway.messageid)
            ).all()
            gw["ended"] = True
            await self.config.custom(GIVEAWAY_KEY, giveaway.guildid, str(giveaway.messageid)).set(
                gw
            )
            return
        if giveaway.kwargs.get("announce"):
            announce_embed = discord.Embed(
                title="Giveaway Ended",
                description=f"Congratulations to the {f'{str(winners)} ' if winners > 1 else ''}winner{'s' if winners > 1 else ''} of [{giveaway.prize}]({msg.jump_url}).\n{txt}",
                color=await self.bot.get_embed_color(channel_obj),
            )

            announce_embed.set_footer(
                text=f"Reroll: {(await self.bot.get_prefix(msg))[-1]}gw reroll {giveaway.messageid}"
            )
            await channel_obj.send(
                content="Congratulations " + ",".join([x.mention for x in winner_objs])
                if winner_objs is not None
                else "",
                embed=announce_embed,
            )
        if channel_obj.permissions_for(guild.me).manage_messages:
            await msg.clear_reactions()
        if winner_objs is not None:
            if giveaway.kwargs.get("congratulate", False):
                for winner in winner_objs:
                    with contextlib.suppress(discord.Forbidden):
                        await winner.send(
                            f"Congratulations! You won {giveaway.prize} in the giveaway on {guild}!"
                        )
            async with self.config.custom(
                GIVEAWAY_KEY, giveaway.guildid, int(giveaway.messageid)
            ).entrants() as entrants:
                entrants = [x for x in entrants if x != winner]
        return

    @commands.hybrid_group(aliases=["gw"])
    @commands.bot_has_permissions(add_reactions=True, embed_links=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context):
        """
        Manage the giveaway system
        """

    @giveaway.command()
    @app_commands.describe(
        channel="The channel in which to start the giveaway.",
        time="The time the giveaway should last.",
        prize="The prize for the giveaway.",
    )
    async def start(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        time: TimedeltaConverter(default_unit="minutes"),
        *,
        prize: str,
    ):
        """
        Start a giveaway.

        This by default will DM the winner and also DM a user if they cannot enter the giveaway.
        """
        channel = channel or ctx.channel
        end = datetime.now(timezone.utc) + time
        embed = discord.Embed(
            title=f"{prize}",
            description=f"\nReact with 🎉 to enter\n\n**Hosted by:** {ctx.author.mention}\n\nEnds: <t:{int(end.timestamp())}:R>",
            color=await ctx.embed_color(),
        )
        msg = await channel.send(embed=embed)
        giveaway_obj = Giveaway(
            ctx.guild.id,
            channel.id,
            msg.id,
            end,
            prize,
            "🎉",
            **{"congratulate": True, "notify": True},
        )
        if ctx.interaction:
            await ctx.send("Giveaway created!", ephemeral=True)
        self.giveaways[msg.id] = giveaway_obj
        await msg.add_reaction("🎉")
        giveaway_dict = deepcopy(giveaway_obj.__dict__)
        giveaway_dict["endtime"] = giveaway_dict["endtime"].timestamp()
        await self.config.custom(GIVEAWAY_KEY, str(ctx.guild.id), str(msg.id)).set(giveaway_dict)

    @giveaway.command()
    @app_commands.describe(msgid="The message ID of the giveaway to end.")
    async def reroll(self, ctx: commands.Context, msgid: int):
        """Reroll a giveaway."""
        data = await self.config.custom(GIVEAWAY_KEY, ctx.guild.id).all()
        if str(msgid) not in data:
            return await ctx.send("Giveaway not found.")
        if msgid in self.giveaways:
            return await ctx.send(
                f"Giveaway already running. Please wait for it to end or end it via `{ctx.clean_prefix}gw end {msgid}`."
            )
        giveaway_dict = data[str(msgid)]
        giveaway_dict["endtime"] = datetime.fromtimestamp(giveaway_dict["endtime"]).replace(
            tzinfo=timezone.utc
        )
        giveaway = Giveaway(**giveaway_dict)
        try:
            await self.draw_winner(giveaway)
        except GiveawayExecError as e:
            await ctx.send(e.message)
        else:
            await ctx.tick()

    @giveaway.command()
    @app_commands.describe(msgid="The message ID of the giveaway to end.")
    async def end(self, ctx: commands.Context, msgid: int):
        """End a giveaway."""
        if msgid in self.giveaways:
            if self.giveaways[msgid].guildid != ctx.guild.id:
                return await ctx.send("Giveaway not found.")
            await self.draw_winner(self.giveaways[msgid])
            del self.giveaways[msgid]
            gw = await self.config.custom(GIVEAWAY_KEY, ctx.guild.id, str(msgid)).all()
            gw["ended"] = True
            await self.config.custom(GIVEAWAY_KEY, ctx.guild.id, str(msgid)).set(gw)
            await ctx.tick()
        else:
            await ctx.send("Giveaway not found.")

    @giveaway.command(aliases=["adv"])
    @app_commands.describe(
        arguments="The arguments for the giveaway. See `[p]gw explain` for more info."
    )
    async def advanced(self, ctx: commands.Context, *, arguments: Args):
        """Advanced creation of Giveaways.


        `[p]gw explain` for a further full listing of the arguments.
        """
        prize = arguments["prize"]
        duration = arguments["duration"]
        channel = arguments["channel"] or ctx.channel

        winners = arguments.get("winners", 1) or 1
        end = datetime.now(timezone.utc) + duration
        description = arguments["description"] or ""
        if arguments["show_requirements"]:
            description += "\n\n**Requirements**:"
            for kwarg in set(arguments) - {
                "show_requirements",
                "prize",
                "duration",
                "channel",
                "winners",
                "description",
                "congratulate",
                "notify",
                "announce",
                "emoji",
                "thumbnail",
                "image",
            }:
                if arguments[kwarg]:
                    description += f"\n**{kwarg.title()}:** {arguments[kwarg]}"

        emoji = arguments["emoji"] or "🎉"
        if isinstance(emoji, int):
            emoji = self.bot.get_emoji(emoji)
        embed = discord.Embed(
            title=f"{f'{winners}x ' if winners > 1 else ''}{prize}",
            description=f"{description}\n\nReact with {emoji} to enter\n\n**Hosted by:** {ctx.author.mention}\n\nEnds: <t:{int(end.timestamp())}:R>",
            color=await ctx.embed_color(),
        )
        if arguments["image"] is not None:
            embed.set_image(url=arguments["image"])
        if arguments["thumbnail"] is not None:
            embed.set_thumbnail(url=arguments["thumbnail"])
        txt = "\n"
        if arguments["ateveryone"]:
            txt += "@everyone "
        if arguments["athere"]:
            txt += "@here "
        if arguments["mentions"]:
            for mention in arguments["mentions"]:
                role = ctx.guild.get_role(mention)
                if role is not None:
                    txt += f"{role.mention} "
        msg = await channel.send(
            content=f"🎉 Giveaway 🎉{txt}",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                roles=bool(arguments["mentions"]),
                everyone=bool(arguments["ateveryone"]),
            ),
        )
        if ctx.interaction:
            await ctx.send("Giveaway created!", ephemeral=True)

        giveaway_obj = Giveaway(
            ctx.guild.id,
            channel.id,
            msg.id,
            end,
            prize,
            str(emoji),
            **{
                k: v
                for k, v in arguments.items()
                if k not in ["prize", "duration", "channel", "emoji"]
            },
        )
        self.giveaways[msg.id] = giveaway_obj
        await msg.add_reaction(emoji)
        giveaway_dict = deepcopy(giveaway_obj.__dict__)
        giveaway_dict["endtime"] = giveaway_dict["endtime"].timestamp()
        await self.config.custom(GIVEAWAY_KEY, str(ctx.guild.id), str(msg.id)).set(giveaway_dict)

    @giveaway.command()
    @app_commands.describe(msgid="The message ID of the giveaway to edit.")
    async def entrants(self, ctx: commands.Context, msgid: int):
        """List all entrants for a giveaway."""
        if msgid not in self.giveaways:
            return await ctx.send("Giveaway not found.")
        giveaway = self.giveaways[msgid]
        if not giveaway.entrants:
            return await ctx.send("No entrants.")
        count = {}
        for entrant in giveaway.entrants:
            if entrant not in count:
                count[entrant] = 1
            else:
                count[entrant] += 1
        msg = ""
        for userid, count_int in count.items():
            user = ctx.guild.get_member(userid)
            msg += f"{user.mention} ({count_int})\n" if user else f"<{userid}> ({count_int})\n"
        embeds = []
        for page in pagify(msg, delims=["\n"], page_length=800):
            embed = discord.Embed(
                title="Entrants", description=page, color=await ctx.embed_color()
            )
            embed.set_footer(text=f"Total entrants: {len(count)}")
            embeds.append(embed)

        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])
        return await menu(ctx, embeds, DEFAULT_CONTROLS)

    @giveaway.command()
    @app_commands.describe(msgid="The message ID of the giveaway to edit.")
    async def info(self, ctx: commands.Context, msgid: int):
        """Information about a giveaway."""
        if msgid not in self.giveaways:
            return await ctx.send("Giveaway not found.")

        giveaway = self.giveaways[msgid]
        winners = giveaway.kwargs.get("winners", 1) or 1
        msg = f"**Entrants:**: {len(giveaway.entrants)}\n**End**: <t:{int(giveaway.endtime.timestamp())}:R>\n"
        for kwarg in giveaway.kwargs:
            if giveaway.kwargs[kwarg]:
                msg += f"**{kwarg.title()}:** {giveaway.kwargs[kwarg]}\n"
        embed = discord.Embed(
            title=f"{f'{winners}x ' if winners > 1 else ''}{giveaway.prize}",
            color=await ctx.embed_color(),
            description=msg,
        )
        embed.set_footer(text=f"Giveaway ID #{msgid}")
        await ctx.send(embed=embed)

    @giveaway.command(name="list")
    async def _list(self, ctx: commands.Context):
        """List all giveaways in the server."""
        if not self.giveaways:
            return await ctx.send("No giveaways are running.")
        giveaways = {
            x: self.giveaways[x]
            for x in self.giveaways
            if self.giveaways[x].guildid == ctx.guild.id
        }
        if not giveaways:
            return await ctx.send("No giveaways are running.")
        msg = "".join(
            f"{msgid}: [{giveaways[msgid].prize}](https://discord.com/channels/{value.guildid}/{giveaways[msgid].channelid}/{msgid})\n"
            for msgid, value in giveaways.items()
        )

        embeds = []
        for page in pagify(msg, delims=["\n"]):
            embed = discord.Embed(
                title=f"Giveaways in {ctx.guild}", description=page, color=await ctx.embed_color()
            )
            embeds.append(embed)
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])
        return await menu(ctx, embeds, DEFAULT_CONTROLS)

    @giveaway.command()
    async def explain(self, ctx: commands.Context):
        """Explanation of giveaway advanced and the arguements it supports."""

        msg = """
        Giveaway advanced creation.
        NOTE: Giveaways are checked every 20 seconds, this means that the giveaway may end up being slightly longer than the specified duration.

        Giveaway advanced contains many different flags that can be used to customize the giveaway.
        The flags are as follows:

        Required arguments:
        `--prize`: The prize to be won.

        Required Mutual Exclusive Arguments:
        You must one ONE of these, but not both:
        `--duration`: The duration of the giveaway. Must be in format such as `2d3h30m`.
        `--end`: The end time of the giveaway. Must be in format such as `2021-12-23T30:00:00.000Z`, `tomorrow at 3am`, `in 4 hours`. Defaults to UTC if no timezone is provided.

        Optional arguments:
        `--channel`: The channel to post the giveaway in. Will default to this channel if not specified.
        `--emoji`: The emoji to use for the giveaway.
        `--roles`: Roles that the giveaway will be restricted to. If the role contains a space, use their ID.
        `--multiplier`: Multiplier for those in specified roles. Must be a positive number.
        `--multi-roles`: Roles that will receive the multiplier. If the role contains a space, use their ID.
        `--cost`: Cost of credits to enter the giveaway. Must be a positive number.
        `--joined`: How long the user must be a member of the server for to enter the giveaway. Must be a positive number of days.
        `--created`: How long the user has been on discord for to enter the giveaway. Must be a positive number of days.
        `--blacklist`: Blacklisted roles that cannot enter the giveaway. If the role contains a space, use their ID.
        `--winners`: How many winners to draw. Must be a positive number.
        `--mentions`: Roles to mention in the giveaway notice.
        `--description`: Description of the giveaway.
        `--image`: Image URL to use for the giveaway embed.
        `--thumbnail`: Thumbnail URL to use for the giveaway embed.

        Setting Arguments:
        `--congratulate`: Whether or not to congratulate the winner. Not passing will default to off.
        `--notify`: Whether or not to notify a user if they failed to enter the giveaway. Not passing will default to off.
        `--multientry`: Whether or not to allow multiple entries. Not passing will default to off.
        `--announce`: Whether to post a seperate message when the giveaway ends. Not passing will default to off.
        `--ateveryone`: Whether to tag @everyone in the giveaway notice.
        `--show-requirements`: Whether to show the requirements of the giveaway.


        3rd party integrations:
        See `[p]gw integrations` for more information.

        Examples:
        `{prefix}gw advanced --prize A new sword --duration 1h30m --restrict Role ID --multiplier 2 --multi-roles RoleID RoleID2`
        `{prefix}gw advanced --prize A better sword --duration 2h3h30m --channel channel-name --cost 250 --joined 50 --congratulate --notify --multientry --level-req 100`""".format(
            prefix=ctx.clean_prefix
        )
        embed = discord.Embed(
            title="Giveaway Advanced Explanation", description=msg, color=await ctx.embed_color()
        )
        await ctx.send(embed=embed)

    @giveaway.command()
    async def integrations(self, ctx: commands.Context):
        """Various 3rd party integrations for giveaways."""

        msg = """
        3rd party integrations for giveaways.

        You can use these integrations to integrate giveaways with other 3rd party services.

        `--level-req`: Integrate with the Red Level system Must be Fixator's leveler.
        `--rep-req`: Integrate with the Red Level Rep system Must be Fixator's leveler.
        `--tatsu-level`: Integrate with the Tatsumaki's levelling system, must have a valid Tatsumaki API key set.
        `--tatsu-rep`: Integrate with the Tatsumaki's rep system, must have a valid Tatsumaki API key set.
        `--mee6-level`: Integrate with the MEE6 levelling system.
        `--amari-level`: Integrate with the Amari's levelling system.
        `--amari-weekly-xp`: Integrate with the Amari's weekly xp system.""".format(
            prefix=ctx.clean_prefix
        )
        if await self.bot.is_owner(ctx.author):
            msg += """
                **API Keys**
                Tatsu's API key can be set with the following command (You must find where this key is yourself): `{prefix}set api tatsumaki authorization <key>`
                Amari's API key can be set with the following command (Apply [here](https://docs.google.com/forms/d/e/1FAIpQLScQDCsIqaTb1QR9BfzbeohlUJYA3Etwr-iSb0CRKbgjA-fq7Q/viewform)): `{prefix}set api amari authorization <key>`


                For any integration suggestions, suggest them via the [#support-flare-cogs](https://discord.gg/GET4DVk) channel on the support server or [flare-cogs](https://github.com/flaree/flare-cogs/issues/new/choose) github.""".format(
                prefix=ctx.clean_prefix
            )

        embed = discord.Embed(
            title="3rd Party Integrations", description=msg, color=await ctx.embed_color()
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id in self.giveaways:
            giveaway = self.giveaways[payload.message_id]
            if payload.emoji.is_custom_emoji() and str(payload.emoji) != giveaway.emoji:
                return
            elif payload.emoji.is_unicode_emoji() and str(payload.emoji) != giveaway.emoji:
                return
            try:
                await giveaway.add_entrant(payload.member, bot=self.bot, session=self.session)
            except GiveawayEnterError as e:
                if giveaway.kwargs.get("notify", False):
                    with contextlib.suppress(discord.Forbidden):
                        await payload.member.send(e.message)
                return
            except GiveawayExecError as e:
                log.exception("Error while adding user to giveaway", exc_info=e)
                return
            await self.config.custom(
                GIVEAWAY_KEY, payload.guild_id, payload.message_id
            ).entrants.set(self.giveaways[payload.message_id].entrants)
