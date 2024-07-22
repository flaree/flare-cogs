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
from .menu import GiveawayButton, GiveawayView
from .objects import Giveaway, GiveawayEnterError, GiveawayExecError

log = logging.getLogger("red.flare.giveaways")
GIVEAWAY_KEY = "giveaways"

# TODO: Add a way to delete giveaways that have ended from the config


class Giveaways(commands.Cog):
    """Giveaway Commands"""

    __version__ = "1.3.3"
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
        self.view = GiveawayView(self)
        bot.add_view(self.view)

    async def init(self) -> None:
        await self.bot.wait_until_ready()
        data = await self.config.custom(GIVEAWAY_KEY).all()
        for _, guild in data.items():
            for msgid, giveaway in guild.items():
                try:
                    if giveaway.get("ended", False):
                        continue
                    giveaway["endtime"] = datetime.fromtimestamp(giveaway["endtime"]).replace(
                        tzinfo=timezone.utc
                    )
                    giveaway_obj = Giveaway(
                        giveaway["guildid"],
                        giveaway["channelid"],
                        giveaway["messageid"],
                        giveaway["endtime"],
                        giveaway["prize"],
                        giveaway["emoji"],
                        **giveaway["kwargs"],
                    )
                    self.giveaways[int(msgid)] = giveaway_obj
                    view = GiveawayView(self)
                    view.add_item(
                        GiveawayButton(
                            label=giveaway["kwargs"].get("button-text", "Join Giveaway"),
                            style=giveaway["kwargs"].get("button-style", "green"),
                            emoji=giveaway["emoji"],
                            cog=self,
                            id=giveaway["messageid"],
                        )
                    )
                    self.bot.add_view(view)
                except Exception as exc:
                    log.error(f"Error loading giveaway {msgid}: ", exc_info=exc)
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
        giveaways = deepcopy(self.giveaways)
        for msgid, giveaway in giveaways.items():
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
                    txt += f"{winner_obj.mention} ({winner_obj.display_name})\n"
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
            await msg.edit(content="🎉 Giveaway Ended 🎉", embed=embed, view=None)
        except (discord.NotFound, discord.Forbidden) as exc:
            log.error("Error editing giveaway message: ", exc_info=exc)
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
                content=(
                    "Congratulations " + ",".join([x.mention for x in winner_objs])
                    if winner_objs is not None
                    else ""
                ),
                embed=announce_embed,
            )
        if winner_objs is not None:
            if giveaway.kwargs.get("congratulate", False):
                for winner in winner_objs:
                    with contextlib.suppress(discord.Forbidden):
                        await winner.send(
                            f"Congratulations! You won {giveaway.prize} in the giveaway on {guild}!"
                        )
        del self.giveaways[giveaway.messageid]
        gw = await self.config.custom(
            GIVEAWAY_KEY, giveaway.guildid, str(giveaway.messageid)
        ).all()
        gw["ended"] = True
        await self.config.custom(GIVEAWAY_KEY, giveaway.guildid, str(giveaway.messageid)).set(gw)
        return

    @commands.hybrid_group(aliases=["gw"])
    @commands.bot_has_permissions(add_reactions=True, embed_links=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context):
        """
        Manage the giveaway system
        """

    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
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
            description=f"\nClick the button below to enter\n\n**Hosted by:** {ctx.author.mention}\n\nEnds: <t:{int(end.timestamp())}:R>",
            color=await ctx.embed_color(),
        )
        view = GiveawayView(self)

        msg = await channel.send(embed=embed)
        view.add_item(
            GiveawayButton(
                label="Join Giveaway",
                style="green",
                emoji="🎉",
                cog=self,
                id=msg.id,
            )
        )
        self.bot.add_view(view)
        await msg.edit(view=view)
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
        giveaway_dict = deepcopy(giveaway_obj.__dict__)
        giveaway_dict["endtime"] = giveaway_dict["endtime"].timestamp()
        await self.config.custom(GIVEAWAY_KEY, str(ctx.guild.id), str(msg.id)).set(giveaway_dict)

    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
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
    @commands.has_permissions(manage_guild=True)
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
    @commands.has_permissions(manage_guild=True)
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
            description += "\n\n**Requirements:**\n" + self.generate_settings_text(ctx, arguments)

        emoji = arguments["emoji"] or "🎉"
        if isinstance(emoji, int):
            emoji = self.bot.get_emoji(emoji)
        hosted_by = ctx.guild.get_member(arguments.get("hosted-by", ctx.author.id)) or ctx.author
        embed = discord.Embed(
            title=f"{f'{winners}x ' if winners > 1 else ''}{prize}",
            description=f"{description}\n\nClick the button below to enter\n\n**Hosted by:** {hosted_by.mention}\n\nEnds: <t:{int(end.timestamp())}:R>",
            color=arguments.get("colour", await ctx.embed_color()),
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

        view = GiveawayView(self)
        msg = await channel.send(
            content=f"🎉 Giveaway 🎉{txt}",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                roles=bool(arguments["mentions"]),
                everyone=bool(arguments["ateveryone"]),
            ),
        )
        view.add_item(
            GiveawayButton(
                label=arguments["button-text"] or "Join Giveaway",
                style=arguments["button-style"] or "green",
                emoji=emoji,
                cog=self,
                update=arguments.get("update_button", False),
                id=msg.id,
            )
        )
        self.bot.add_view(view)
        await msg.edit(view=view)
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
        giveaway_dict = deepcopy(giveaway_obj.__dict__)
        giveaway_dict["endtime"] = giveaway_dict["endtime"].timestamp()
        del giveaway_dict["kwargs"]["colour"]
        await self.config.custom(GIVEAWAY_KEY, str(ctx.guild.id), str(msg.id)).set(giveaway_dict)

    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
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
    @commands.has_permissions(manage_guild=True)
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
    @commands.has_permissions(manage_guild=True)
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
    @commands.has_permissions(manage_guild=True)
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
        `--button-text`: Text to use for the button.
        `--button-style`: Style to use for the button.
        `--image`: Image URL to use for the giveaway embed.
        `--thumbnail`: Thumbnail URL to use for the giveaway embed.
        `--hosted-by`: User of the user hosting the giveaway. Defaults to the author of the command.
        `--colour`: Colour to use for the giveaway embed.
        `--bypass-roles`: Roles that bypass the requirements. If the role contains a space, use their ID.
        `--bypass-type`: Type of bypass to use. Must be one of `or` or `and`. Defaults to `or`.

        Setting Arguments:
        `--congratulate`: Whether or not to congratulate the winner. Not passing will default to off.
        `--notify`: Whether or not to notify a user if they failed to enter the giveaway. Not passing will default to off.
        `--multientry`: Whether or not to allow multiple entries. Not passing will default to off.
        `--announce`: Whether to post a seperate message when the giveaway ends. Not passing will default to off.
        `--ateveryone`: Whether to tag @everyone in the giveaway notice.
        `--show-requirements`: Whether to show the requirements of the giveaway.
        `--athere`: Whether to tag @here in the giveaway notice.
        `--update-button`: Whether to update the button with the number of entrants.


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
    @commands.has_permissions(manage_guild=True)
    async def edit(self, ctx, msgid: int, *, flags: Args):
        """Edit a giveaway.

        See `[p]gw explain` for more info on the flags.
        """
        if msgid not in self.giveaways:
            return await ctx.send("Giveaway not found.")
        giveaway = self.giveaways[msgid]
        if giveaway.guildid != ctx.guild.id:
            return await ctx.send("Giveaway not found.")
        for flag in flags:
            if flags[flag]:
                if flag in ["prize", "duration", "end", "channel", "emoji"]:
                    setattr(giveaway, flag, flags[flag])
                elif flag in ["roles", "multi_roles", "blacklist", "mentions"]:
                    giveaway.kwargs[flag] = [x.id for x in flags[flag]]
                else:
                    giveaway.kwargs[flag] = flags[flag]
        giveaway.endtime = datetime.now(timezone.utc) + giveaway.duration
        self.giveaways[msgid] = giveaway
        giveaway_dict = deepcopy(giveaway.__dict__)
        giveaway_dict["endtime"] = giveaway_dict["endtime"].timestamp()
        giveaway_dict["duration"] = giveaway_dict["duration"].total_seconds()
        del giveaway_dict["kwargs"]["colour"]
        await self.config.custom(GIVEAWAY_KEY, ctx.guild.id, str(msgid)).set(giveaway_dict)
        message = ctx.guild.get_channel(giveaway.channelid).get_partial_message(giveaway.messageid)
        hosted_by = (
            ctx.guild.get_member(giveaway.kwargs.get("hosted-by", ctx.author.id)) or ctx.author
        )
        new_embed = discord.Embed(
            title=f"{giveaway.prize}",
            description=f"\nClick the button below to enter\n\n**Hosted by:** {hosted_by.mention}\n\nEnds: <t:{int(giveaway_dict['endtime'])}:R>",
            color=flags.get("colour", await ctx.embed_color()),
        )
        await message.edit(embed=new_embed)
        await ctx.tick()

    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
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

    def generate_settings_text(self, ctx: commands.Context, args):
        msg = ""
        if args.get("roles"):
            msg += (
                f"**Roles:** {', '.join([ctx.guild.get_role(x).mention for x in args['roles']])}\n"
            )
        if args.get("multi"):
            msg += f"**Multiplier:** {args['multi']}\n"
        if args.get("multi-roles"):
            msg += f"**Multiplier Roles:** {', '.join([ctx.guild.get_role(x).mention for x in args['multi-roles']])}\n"
        if args.get("cost"):
            msg += f"**Cost:** {args['cost']}\n"
        if args.get("joined"):
            msg += f"**Joined:** {args['joined']} days\n"
        if args.get("created"):
            msg += f"**Created:** {args['created']} days\n"
        if args.get("blacklist"):
            msg += f"**Blacklist:** {', '.join([ctx.guild.get_role(x).mention for x in args['blacklist']])}\n"
        if args.get("winners"):
            msg += f"**Winners:** {args['winners']}\n"
        if args.get("mee6_level"):
            msg += f"**MEE6 Level:** {args['mee6_level']}\n"
        if args.get("amari_level"):
            msg += f"**Amari Level:** {args['amari_level']}\n"
        if args.get("amari_weekly_xp"):
            msg += f"**Amari Weekly XP:** {args['amari_weekly_xp']}\n"
        if args.get("tatsu_level"):
            msg += f"**Tatsu Level:** {args['tatsu_level']}\n"
        if args.get("tatsu_rep"):
            msg += f"**Tatsu Rep:** {args['tatsu_rep']}\n"
        if args.get("level_req"):
            msg += f"**Level Requirement:** {args['level_req']}\n"
        if args.get("rep_req"):
            msg += f"**Rep Requirement:** {args['rep_req']}\n"
        if args.get("bypass-roles"):
            msg += f"**Bypass Roles:** {', '.join([ctx.guild.get_role(x).mention for x in args['bypass-roles']])} ({args['bypass-type']})\n"

        return msg
