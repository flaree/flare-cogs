import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from typing import Literal, Optional

import discord
import tabulate
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box, humanize_list, inline
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.mod import is_mod_or_superior
from redbot.core.utils.predicates import MessagePredicate

logger = logging.getLogger("red.flare.highlight")


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


async def restrictedhighlight_check(ctx):
    cog = ctx.bot.get_cog("Highlight")
    if cog is None:
        return False
    restricted = await cog.config.restricted()
    return await is_mod_or_superior(ctx.bot, ctx.author) if restricted else True


class Highlight(commands.Cog):
    """Be notified when keywords are sent."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        self.config.register_global(
            migrated=False,
            min_len=5,
            max_highlights=10,
            default_cooldown=60,
            colour=discord.Color.red().value,
            restricted=False,
        )
        self.config.register_member(blacklist=[], whitelist=[], cooldown=60, channel_blacklist=[])
        default_channel = {"highlight": {}}
        self.config.register_channel(**default_channel)
        self.config.register_guild(**default_channel)
        self.highlightcache = {}
        self.member_cache = {}
        self.cooldowns = {}
        self.recache = {}
        self.guildcache = {}
        self.global_conf = {}
        self.cooldown = 60

    async def red_get_data_for_user(self, *, user_id: int):
        config = await self.config.all_channels()
        data = [channel for channel in config if str(user_id) in config[channel]["highlight"]]

        if data is None:
            return {}
        contents = f"Highlight Data for Discord user with ID {user_id}:\n"
        for highlight in data:
            contents += f"- Channel: {highlight[0]} | Highlighted Word: {highlight[1]}\n"
        return {"user_data.txt": BytesIO(contents.encode())}

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ) -> None:
        config = await self.config.all_channels()
        data = [channel for channel in config if str(user_id) in config[channel]["highlight"]]

        for channel in data:
            async with self.config.channel_from_id(channel).highlight() as highlight:
                del highlight[str(user_id)]
        await self.generate_cache()

    __version__ = "1.9.1"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx: commands.Context):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    async def initalize(self):
        await self.migrate_config()
        await self.generate_cache()

    async def generate_cache(self):
        self.cooldown = await self.config.default_cooldown()
        self.global_conf = await self.config.all()
        self.highlightcache = await self.config.all_channels()
        self.member_cache = await self.config.all_members()
        self.guildcache = await self.config.all_guilds()

    async def migrate_config(self):
        if await self.config.migrated():
            return

        conf = await self.config.all_channels()
        a = {
            channel: {
                user: {
                    highlight: {
                        "toggle": conf[channel]["toggle"][user],
                        "bots": False,
                    }
                    for highlight in conf[channel]["highlight"][user]
                }
                for user in conf[channel]["highlight"]
            }
            for channel in conf
        }

        group = self.config._get_base_group(self.config.CHANNEL)
        async with group.all() as new_data:
            for channel in a:
                new_data[channel] = {"highlight": a[channel]}
        await self.config.migrated.set(True)
        logger.info("Migration complete.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        highlight, highlightguild = (
            self.highlightcache.get(message.channel.id),
            self.guildcache.get(message.guild.id),
        )
        # highlight_guild = self.guildcache.get(message.guild.id)
        if highlight is None:
            highlight = {}
        if highlightguild is None:
            highlightguild = {}
        highlight_guild = highlightguild.get("highlight", {})
        highlight = highlight.get("highlight", {})
        highlighted_dict = defaultdict(dict)
        for d in (highlight, highlight_guild):
            for key, value in d.items():
                for val in value:
                    highlighted_dict[key][val] = value[val]
        for user in highlighted_dict:
            if int(user) == message.author.id:
                continue
            if self.global_conf.get("restricted") and not await is_mod_or_superior(
                self.bot, message.guild.get_member(int(user))
            ):
                continue
            if self.cooldowns.get(int(user)):
                seconds = (
                    datetime.now(tz=timezone.utc) - self.cooldowns[int(user)]
                ).total_seconds()
                cooldown = (
                    self.member_cache.get(message.guild.id, {})
                    .get(int(user), {})
                    .get("cooldown", self.cooldown)
                )
                if cooldown < self.cooldown:
                    cooldown = self.cooldown
                if seconds < cooldown:
                    continue
            if self.member_cache.get(message.guild.id, False) and self.member_cache[
                message.guild.id
            ].get(int(user), False):
                if (
                    self.member_cache[message.guild.id][int(user)]["whitelist"]
                    and message.author.id
                    not in self.member_cache[message.guild.id][int(user)]["whitelist"]
                ):
                    continue
                elif (
                    self.member_cache[message.guild.id][int(user)]["blacklist"]
                    and message.author.id
                    in self.member_cache[message.guild.id][int(user)]["blacklist"]
                ):
                    continue
                elif (
                    self.member_cache[message.guild.id][int(user)]["channel_blacklist"]
                    and message.channel.id
                    in self.member_cache[message.guild.id][int(user)]["channel_blacklist"]
                ):
                    continue
            highlighted_words = []
            for word in highlighted_dict[user]:
                if not highlighted_dict[user][word]["toggle"]:
                    continue
                if word in highlighted_words:
                    continue

                highlighted_usr = message.guild.get_member(int(user))
                if highlighted_usr is None:
                    continue
                if not await self.bot.allowed_by_whitelist_blacklist(highlighted_usr):
                    continue
                if not message.channel.permissions_for(highlighted_usr).read_messages:
                    continue
                if message.author.bot and not highlighted_dict[user][word]["bots"]:
                    continue
                if highlighted_dict[user][word].get("boundary", False):
                    if word.lower() in self.recache:
                        pattern = self.recache[word.lower()]
                    else:
                        pattern = re.compile(rf"\b{re.escape(word.lower())}\b", flags=re.I)
                        self.recache[word.lower()] = pattern
                    if set(pattern.findall(message.content.lower())):
                        highlighted_words.append(word)
                elif word.lower() in message.content.lower():
                    highlighted_words.append(word)
            if highlighted_words:
                msglist = [message]
                async for messages in message.channel.history(
                    limit=5, before=message, oldest_first=False
                ):
                    msglist.append(messages)
                msglist.reverse()
                context = "\n".join(f"**{x.author}**: {x.content}" for x in msglist)
                if len(context) > 2000:
                    context = "**Context omitted due to message size limits.\n**"
                embed = discord.Embed(
                    title="Context:",
                    colour=self.global_conf.get("colour", 0xFFFFFF),
                    timestamp=message.created_at,
                    description="{}".format(context),
                )
                embed.add_field(name="Jump", value=f"[Click for context]({message.jump_url})")
                await highlighted_usr.send(
                    f"Your highlighted word{'s' if len(highlighted_words) > 1 else ''} {humanize_list(list(map(inline, highlighted_words)))} was mentioned in {message.channel.mention} in {message.guild.name} by {message.author.display_name}.\n",
                    embed=embed,
                )
                self.cooldowns[highlighted_usr.id] = datetime.now(tz=timezone.utc)

    def channel_check(self, ctx: commands.Context, channel: discord.TextChannel):
        return (
            channel.permissions_for(ctx.author).read_messages
            and channel.permissions_for(ctx.me).read_message_history
        )

    @commands.guild_only()
    @commands.group(autohelp=True)
    @commands.check(restrictedhighlight_check)
    async def highlight(self, ctx: commands.Context):
        """Highlighting Commands."""

    @highlight.group()
    async def whitelist(self, ctx: commands.Context):
        """Manage highlight whitelist.

        Whitelist takes priority over blacklist."""

    @highlight.group()
    async def blacklist(self, ctx: commands.Context):
        """Manage highlight blacklist.

        Whitelist takes priority over blacklist."""

    @whitelist.command(name="user")
    async def whitelist_addremove(self, ctx: commands.Context, user: discord.Member):
        """Add or remove a member from highlight whitelist.

        This is per guild."""
        async with self.config.member(ctx.author).whitelist() as whitelist:
            if user.id in whitelist:
                whitelist.remove(user.id)
                await ctx.send(
                    f"{ctx.author.name} has removed {user} from their highlight whitelist."
                )
            else:
                whitelist.append(user.id)
                await ctx.send(f"{ctx.author.name} has added {user} to their highlight whitelist.")
        await self.generate_cache()

    @whitelist.command(name="list")
    async def whitelist_list(self, ctx: commands.Context):
        """List those in your whitelist."""
        whitelist = await self.config.member(ctx.author).whitelist()
        if not whitelist:
            return await ctx.send("Your whitelist is empty.")
        embed = discord.Embed(
            title="Whitelist",
            colour=self.global_conf.get("colour", await self.bot.get_embed_color(ctx)),
        )
        embed.add_field(name="Users", value="".join(f" - <@{_id}>\n" for _id in whitelist))
        await ctx.send(embed=embed)

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx: commands.Context):
        """List your blacklist."""
        blacklist = await self.config.member(ctx.author).blacklist()
        channel_blacklist = await self.config.member(ctx.author).channel_blacklist()
        if not blacklist and not channel_blacklist:
            return await ctx.send("Your blacklist is empty.")
        embed = discord.Embed(
            title="Blacklist",
            colour=self.global_conf.get("colour", await self.bot.get_embed_color(ctx)),
        )
        if blacklist:
            embed.add_field(name="Users", value="".join(f" - <@{_id}>\n" for _id in blacklist))
        if channel_blacklist:
            embed.add_field(
                name="Channels", value="".join(f" - <#{_id}>\n" for _id in channel_blacklist)
            )
        await ctx.send(embed=embed)

    @blacklist.command(name="user")
    async def blacklist_addremove(self, ctx: commands.Context, user: discord.Member):
        """Add or remove a member from highlight blacklist.

        This is per guild."""
        async with self.config.member(ctx.author).blacklist() as blacklist:
            if user.id in blacklist:
                blacklist.remove(user.id)
                await ctx.send(
                    f"{ctx.author.name} has removed {user} from their highlight blacklist."
                )
            else:
                blacklist.append(user.id)
                await ctx.send(f"{ctx.author.name} has added {user} to their highlight blacklist.")
        await self.generate_cache()

    @blacklist.command(name="channel")
    async def channel_blacklist_addremove(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Add or remove a channel from highlight blacklist.

        This is per guild."""
        async with self.config.member(ctx.author).channel_blacklist() as blacklist:
            if channel.id in blacklist:
                blacklist.remove(channel.id)
                await ctx.send(
                    f"{ctx.author.name} has removed {channel} from their highlight blacklist."
                )
            else:
                blacklist.append(channel.id)
                await ctx.send(
                    f"{ctx.author.name} has added {channel} to their highlight blacklist."
                )
        await self.generate_cache()

    @highlight.command(name="cooldown")
    async def cooldown(self, ctx: commands.Context, seconds: int = None):
        """Set the cooldown for highlighted messages to be sent. Default is 60 seconds.

        This is per guild.
        Not providing a value will send the current set value."""
        if seconds is None:
            value = await self.config.member(ctx.author).cooldown()
            await ctx.send(f"Your current cooldown time is {value} seconds.")
            return
        if seconds < 0 or seconds > 600:
            await ctx.send("Cooldown seconds must be greater or equal to 0 or less than 600.")
            return
        default = await self.config.default_cooldown()
        if seconds < default:
            await ctx.send(
                f"Cooldown seconds must be greater or equal to the default setting of {default}"
            )
            return
        await self.config.member(ctx.author).cooldown.set(seconds)
        await ctx.send(f"Your highlight cooldown time has been set to {seconds} seconds.")
        await self.generate_cache()

    @highlight.command()
    async def add(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, *text: str
    ):
        """Add a word to be highlighted on.

        Text will be converted to lowercase.\nCan also provide an optional channel argument for
        the highlight to be applied to that channel.
        """
        if not text:
            return await ctx.send_help()
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        async with self.config.channel(channel).highlight() as highlight:
            if str(ctx.author.id) not in highlight:
                highlight[f"{ctx.author.id}"] = {}
            passed = []
            failed = []
            for word in text:
                if len(word) < int(await self.config.min_len()):
                    await ctx.send("Your highlight does not meet the minimum length requirement.")
                    return
                if len(highlight[f"{ctx.author.id}"]) >= int(await self.config.max_highlights()):
                    await ctx.send("You have reached the maximum number of highlights.")
                    return
                if word.lower() not in highlight[f"{ctx.author.id}"]:
                    highlight[f"{ctx.author.id}"][word.lower()] = {
                        "toggle": True,
                        "bots": False,
                        "boundary": False,
                    }
                    passed.append(word)
                else:
                    failed.append(word)
        msg = ""
        if passed:
            msg += f"The word{'s' if len(passed) > 1 else ''} {humanize_list(list(map(inline, passed)))} was added to {ctx.author}'s highlight list in {channel}.\n"
        if failed:
            msg += f"The word{'s' if len(failed) > 1 else ''} {humanize_list(list(map(inline, failed)))} {'are' if len(failed) > 1 else 'is'} already in your highlight list for {channel}."
        await ctx.send(msg)
        await self.generate_cache()

    @highlight.command()
    async def remove(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None, *text: str
    ):
        """Remove highlighting in a channel.

        An optional channel can be provided to remove a highlight from that channel.
        """
        if not text:
            return await ctx.send_help()
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        async with self.config.channel(channel).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send(f"You don't have any highlights setup in {channel}")
            passed = []
            failed = []
            for word in text:
                if word.lower() in highlight[f"{ctx.author.id}"]:
                    del highlight[f"{ctx.author.id}"][word.lower()]
                    passed.append(word)
                else:
                    failed.append(word)
        msg = ""
        if passed:
            msg += f"The word{'s' if len(passed) > 1 else ''} {humanize_list(list(map(inline, passed)))} {'were' if len(failed) > 1 else 'was'} removed from {ctx.author}'s highlight list in {channel}.\n"
        if failed:
            a = "doesn't"
            msg += f"The word{'s' if len(failed) > 1 else ''} {humanize_list(list(map(inline, failed)))} {a if len(failed) > 1 else 'do not'} exist in your highlight list for {channel}."
        await ctx.send(msg)
        await self.generate_cache()

    @highlight.command()
    async def toggle(
        self,
        ctx: commands.Context,
        state: bool,
        channel: Optional[discord.TextChannel] = None,
        *,
        word: str = None,
    ):
        """Toggle highlighting.

        Must be a valid bool. Not passing a word will enable/disable highlighting for all
        highlights.
        """
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        if word is None:
            async with self.config.channel(channel).highlight() as highlight:
                highlights = highlight.get(str(ctx.author.id))
                if not highlights:
                    return await ctx.send("You do not have any highlights setup.")
                for word in highlights:
                    highlight[str(ctx.author.id)][word]["toggle"] = state
            if state:
                await ctx.send("All your highlights have been enabled.")
            else:
                await ctx.send("All your highlights have been disabled.")
            await self.generate_cache()
            return
        word = word.lower()
        async with self.config.channel(channel).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send("You do not have any highlights setup.")
            if word not in highlight[str(ctx.author.id)]:
                return await ctx.send(
                    f"You do not have a highlight for `{word}` setup in {channel}"
                )
            highlight[str(ctx.author.id)][word]["toggle"] = state
            if state:
                await ctx.send(f"The highlight `{word}` has been enabled in {channel}.")
            else:
                await ctx.send(f"The highlight `{word}` has been disabled in {channel}.")
        await self.generate_cache()

    @highlight.command()
    async def bots(
        self,
        ctx: commands.Context,
        state: bool,
        channel: Optional[discord.TextChannel] = None,
        *,
        word: str = None,
    ):
        """Enable highlighting of bot messages.

        Expects a valid bool. Not passing a word will enable/disable bot highlighting for all
        highlights.
        """
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        if word is None:
            msg = "enable" if state else "disable"
            await ctx.send(
                f"Are you sure you wish to {msg} the highlighting of bot messages for all your highlights? Type yes to confirm otherwise type no."
            )
            try:
                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=pred, timeout=20)
            except asyncio.TimeoutError:
                await ctx.send("Exiting operation.")
                return

            if pred.result:
                async with self.config.channel(channel).highlight() as highlight:
                    highlights = highlight.get(str(ctx.author.id))
                    if not highlights:
                        return await ctx.send("You do not have any highlights setup.")
                    for word in highlights:
                        highlight[str(ctx.author.id)][word]["bots"] = state
                if state:
                    await ctx.send("Bots will now trigger all of your highlights.")
                else:
                    await ctx.send("Bots will no longer trigger on any of your highlights.")

                await self.generate_cache()
            else:
                await ctx.send("Cancelling.")
            return

        word = word.lower()
        async with self.config.channel(channel).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send("You do not have any highlights setup.")
            if word not in highlight[str(ctx.author.id)]:
                return await ctx.send(
                    f"You do not have a highlight for `{word}` setup in {channel}"
                )
            highlight[str(ctx.author.id)][word]["bots"] = state
            if state:
                await ctx.send(
                    f"The highlight `{word}` will now be triggered by bots in {channel}."
                )
            else:
                await ctx.send(
                    f"The highlight `{word}` will no longer be trigged by bots in {channel}."
                )

        await self.generate_cache()

    @highlight.command(name="list")
    async def _list(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Current highlight settings for a channel.

        A channel argument can be supplied to view settings for said channel.
        """
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        highlight = await self.config.channel(channel).highlight()
        if str(ctx.author.id) in highlight and highlight[f"{ctx.author.id}"]:
            words = [
                [
                    word,
                    on_or_off(highlight[f"{ctx.author.id}"][word]["toggle"]),
                    yes_or_no(not highlight[f"{ctx.author.id}"][word]["bots"]),
                    on_or_off(highlight[f"{ctx.author.id}"][word].get("boundary", False)),
                ]
                for word in highlight[f"{ctx.author.id}"]
            ]
            ems = []
            for page in chunks(words, 10):
                embed = discord.Embed(
                    title=f"Current highlighted text for {ctx.author.display_name} in {channel}:",
                    colour=ctx.author.colour,
                    description=box(
                        tabulate.tabulate(
                            sorted(page, key=lambda x: x[1], reverse=True),
                            headers=["Word", "Toggle", "Ignoring Bots", "Word Boundaries"],
                        ),
                        lang="prolog",
                    ),
                )
                ems.append(embed)
            if len(ems) == 1:
                await ctx.send(embed=ems[0])
            else:
                await menu(ctx, ems, DEFAULT_CONTROLS)
        else:
            await ctx.send(f"You currently do not have any highlighted words set up in {channel}.")

    @highlight.command()
    async def boundary(
        self,
        ctx: commands.Context,
        state: bool,
        channel: Optional[discord.TextChannel] = None,
        *,
        word: str = None,
    ):
        """Use word boundaries for highlighting.

        Expects a valid bool. Not passing a word will enable/disable word boundaries for all
        highlights.
        """
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        if word is None:
            msg = "enable" if state else "disable"
            await ctx.send(
                f"Are you sure you wish to {msg} word bounderies for all your highlights? Type yes to confirm otherwise type no."
            )
            try:
                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=pred, timeout=20)
            except asyncio.TimeoutError:
                await ctx.send("Exiting operation.")
                return

            if pred.result:
                async with self.config.channel(channel).highlight() as highlight:
                    highlights = highlight.get(str(ctx.author.id))
                    if not highlights:
                        return await ctx.send("You do not have any highlights setup.")
                    for word in highlights:
                        highlight[str(ctx.author.id)][word]["boundary"] = state
                if state:
                    await ctx.send("All your highlights will now use word boundaries.")
                else:
                    await ctx.send("None of your highlights will use word boundaries.")

                await self.generate_cache()
            else:
                await ctx.send("Cancelling.")
            return

        word = word.lower()
        async with self.config.channel(channel).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send("You do not have any highlights setup.")
            if word not in highlight[str(ctx.author.id)]:
                return await ctx.send(
                    f"You do not have a highlight for `{word}` setup in {channel}"
                )
            highlight[str(ctx.author.id)][word]["boundary"] = state
            if state:
                await ctx.send(
                    f"The highlight `{word}` will now use word boundaries in {channel}."
                )
            else:
                await ctx.send(
                    f"The highlight `{word}` will no longer use word boundaries in {channel}."
                )

        await self.generate_cache()

    @commands.guild_only()
    @highlight.group(autohelp=True)
    async def guild(self, ctx: commands.Context):
        """Guild based highlighting commands.

        Guild highlights take precedence over channel based."""

    @guild.command(name="add")
    async def guild_add(self, ctx: commands.Context, *text: str):
        """Add a word to be highlighted on for thhe guild.

        Text will be converted to lowercase.\nCan also provide an optional channel argument for
        the highlight to be applied to that channel.
        """
        if not text:
            return await ctx.send_help()
        async with self.config.guild(ctx.guild).highlight() as highlight:
            if str(ctx.author.id) not in highlight:
                highlight[f"{ctx.author.id}"] = {}
            passed = []
            failed = []
            for word in text:
                if len(word) < int(await self.config.min_len()):
                    await ctx.send("Your highlight does not meet the minimum length requirement.")
                    return
                if len(highlight[f"{ctx.author.id}"]) >= int(await self.config.max_highlights()):
                    await ctx.send("You have reached the maximum number of highlights.")
                    return
                if word.lower() not in highlight[f"{ctx.author.id}"]:
                    highlight[f"{ctx.author.id}"][word.lower()] = {
                        "toggle": True,
                        "bots": False,
                        "boundary": False,
                    }
                    passed.append(word)
                else:
                    failed.append(word)
        msg = ""
        if passed:
            msg += f"The word{'s' if len(passed) > 1 else ''} {humanize_list(list(map(inline, passed)))} was added to {ctx.author}'s highlight list for {ctx.guild}.\n"
        if failed:
            msg += f"The word{'s' if len(failed) > 1 else ''} {humanize_list(list(map(inline, failed)))} {'are' if len(failed) > 1 else 'is'} already in your highlight list for {ctx.guild}."
        await ctx.send(msg)
        await self.generate_cache()

    @guild.command(name="remove")
    async def guild_remove(self, ctx: commands.Context, *text: str):
        """Remove highlighting for a guild.

        An optional channel can be provided to remove a highlight from that channel.
        """
        if not text:
            return await ctx.send_help()
        async with self.config.guild(ctx.guild).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send(f"You don't have any highlights setup for {ctx.guild}")
            passed = []
            failed = []
            for word in text:
                if word.lower() in highlight[f"{ctx.author.id}"]:
                    del highlight[f"{ctx.author.id}"][word.lower()]
                    passed.append(word)
                else:
                    failed.append(word)
        msg = ""
        if passed:
            msg += f"The word{'s' if len(passed) > 1 else ''} {humanize_list(list(map(inline, passed)))} {'were' if len(failed) > 1 else 'was'} removed from {ctx.author}'s highlight list for {ctx.guild}.\n"
        if failed:
            a = "doesn't"
            msg += f"The word{'s' if len(failed) > 1 else ''} {humanize_list(list(map(inline, failed)))} {a if len(failed) > 1 else 'do not'} exist in your highlight list for {ctx.guild}."
        await ctx.send(msg)
        await self.generate_cache()

    @guild.command(name="toggle")
    async def guild_toggle(
        self,
        ctx: commands.Context,
        state: bool,
        *,
        word: str = None,
    ):
        """Toggle highlighting for guild highlights.

        Must be a valid bool. Not passing a word will enable/disable highlighting for all
        highlights.
        """
        if word is None:
            async with self.config.guild(ctx.guild).highlight() as highlight:
                highlights = highlight.get(str(ctx.author.id))
                if not highlights:
                    return await ctx.send("You do not have any highlights setup.")
                for word in highlights:
                    highlight[str(ctx.author.id)][word]["toggle"] = state
            if state:
                await ctx.send("All your highlights have been enabled.")
            else:
                await ctx.send("All your highlights have been disabled.")
            await self.generate_cache()
            return
        word = word.lower()
        async with self.config.guild(ctx.guild).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send("You do not have any highlights setup.")
            if word not in highlight[str(ctx.author.id)]:
                return await ctx.send(
                    f"You do not have a highlight for `{word}` setup for {ctx.guild}"
                )
            highlight[str(ctx.author.id)][word]["toggle"] = state
            if state:
                await ctx.send(f"The highlight `{word}` has been enabled for {ctx.guild}.")
            else:
                await ctx.send(f"The highlight `{word}` has been disabled for {ctx.guild}.")
        await self.generate_cache()

    @guild.command(name="bots")
    async def guild_bots(
        self,
        ctx: commands.Context,
        state: bool,
        *,
        word: str = None,
    ):
        """Enable highlighting of bot messages for guild highlights.

        Expects a valid bool. Not passing a word will enable/disable bot highlighting for all
        highlights.
        """
        if word is None:
            msg = "enable" if state else "disable"
            await ctx.send(
                f"Are you sure you wish to {msg} the highlighting of bot messages for all your highlights? Type yes to confirm otherwise type no."
            )
            try:
                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=pred, timeout=20)
            except asyncio.TimeoutError:
                await ctx.send("Exiting operation.")
                return

            if pred.result:
                async with self.config.guild(ctx.guild).highlight() as highlight:
                    highlights = highlight.get(str(ctx.author.id))
                    if not highlights:
                        return await ctx.send("You do not have any highlights setup.")
                    for word in highlights:
                        highlight[str(ctx.author.id)][word]["bots"] = state
                if state:
                    await ctx.send("Bots will now trigger all of your highlights.")
                else:
                    await ctx.send("Bots will no longer trigger on any of your highlights.")

                await self.generate_cache()
            else:
                await ctx.send("Cancelling.")
            return

        word = word.lower()
        async with self.config.guild(ctx.guild).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send("You do not have any highlights setup.")
            if word not in highlight[str(ctx.author.id)]:
                return await ctx.send(
                    f"You do not have a highlight for `{word}` setup for {ctx.guild}"
                )
            highlight[str(ctx.author.id)][word]["bots"] = state
            if state:
                await ctx.send(
                    f"The highlight `{word}` will now be triggered by bots for {ctx.guild}."
                )
            else:
                await ctx.send(
                    f"The highlight `{word}` will no longer be trigged by bots for {ctx.guild}."
                )

        await self.generate_cache()

    @guild.command(name="list")
    async def _guild_list(self, ctx: commands.Context):
        """Current highlight settings for a channel.

        A channel argument can be supplied to view settings for said channel.
        """
        highlight = await self.config.guild(ctx.guild).highlight()
        if str(ctx.author.id) in highlight and highlight[f"{ctx.author.id}"]:
            words = [
                [
                    word,
                    on_or_off(highlight[f"{ctx.author.id}"][word]["toggle"]),
                    yes_or_no(not highlight[f"{ctx.author.id}"][word]["bots"]),
                    on_or_off(highlight[f"{ctx.author.id}"][word].get("boundary", False)),
                ]
                for word in highlight[f"{ctx.author.id}"]
            ]
            ems = []
            for page in chunks(words, 10):
                embed = discord.Embed(
                    title=f"Current highlighted text for {ctx.author.display_name} for {ctx.guild}:",
                    colour=ctx.author.colour,
                    description=box(
                        tabulate.tabulate(
                            sorted(page, key=lambda x: x[1], reverse=True),
                            headers=["Word", "Toggle", "Ignoring Bots", "Word Boundaries"],
                        ),
                        lang="prolog",
                    ),
                )
                ems.append(embed)
            if len(ems) == 1:
                await ctx.send(embed=ems[0])
            else:
                await menu(ctx, ems, DEFAULT_CONTROLS)
        else:
            await ctx.send(
                f"You currently do not have any highlighted words set up for {ctx.guild}."
            )

    @guild.command(name="boundary")
    async def guild_boundary(
        self,
        ctx: commands.Context,
        state: bool,
        *,
        word: str = None,
    ):
        """Use word boundaries for guild highlighting.

        Expects a valid bool. Not passing a word will enable/disable word boundaries for all
        highlights.
        """
        if word is None:
            msg = "enable" if state else "disable"
            await ctx.send(
                f"Are you sure you wish to {msg} word bounderies for all your highlights? Type yes to confirm otherwise type no."
            )
            try:
                pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
                await ctx.bot.wait_for("message", check=pred, timeout=20)
            except asyncio.TimeoutError:
                await ctx.send("Exiting operation.")
                return

            if pred.result:
                async with self.config.guild(ctx.guild).highlight() as highlight:
                    highlights = highlight.get(str(ctx.author.id))
                    if not highlights:
                        return await ctx.send("You do not have any highlights setup.")
                    for word in highlights:
                        highlight[str(ctx.author.id)][word]["boundary"] = state
                if state:
                    await ctx.send("All your highlights will now use word boundaries.")
                else:
                    await ctx.send("None of your highlights will use word boundaries.")

                await self.generate_cache()
            else:
                await ctx.send("Cancelling.")
            return

        word = word.lower()
        async with self.config.guild(ctx.guild).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send("You do not have any highlights setup.")
            if word not in highlight[str(ctx.author.id)]:
                return await ctx.send(
                    f"You do not have a highlight for `{word}` setup for {ctx.guild}"
                )
            highlight[str(ctx.author.id)][word]["boundary"] = state
            if state:
                await ctx.send(
                    f"The highlight `{word}` will now use word boundaries for {ctx.guild}."
                )
            else:
                await ctx.send(
                    f"The highlight `{word}` will no longer use word boundaries for {ctx.guild}."
                )

        await self.generate_cache()

    @commands.group()
    @commands.is_owner()
    async def highlightset(self, ctx):
        """Manage highlight settings."""

    @highlightset.command(usage="<max number>")
    async def max(self, ctx, max_num: int):
        """Set the max number of highlights a user can have."""
        if max_num < 1:
            return await ctx.send("Max number must be greater than 0.")
        await self.config.max_highlights.set(max_num)
        await ctx.send(f"Max number of highlights set to {max_num}.")
        await self.generate_cache()

    @highlightset.command()
    async def minlen(self, ctx, min_len: int):
        """Set the minimum length of a highlight."""
        if min_len < 1:
            return await ctx.send("Minimum length cannot be less than 1.")
        await self.config.min_len.set(min_len)
        await ctx.send(f"Minimum length of highlight set to {min_len}.")
        await self.generate_cache()

    @highlightset.command(name="cooldown")
    async def _cooldown(self, ctx, cooldown: int):
        """Set the default cooldown of a highlight. (in seconds)

        Users can override this by using the `highlight cooldown` command, but cannot go lower that what it defined."""
        if cooldown < 1 or cooldown > 600:
            return await ctx.send("Cooldown cannot be less than 1 or greater than 600.")
        await self.config.default_cooldown.set(cooldown)
        await ctx.send(f"Default cooldown set to {cooldown}.")
        self.cooldown = cooldown

    @highlightset.command(aliases=["color"])
    async def colour(self, ctx, *, colour: discord.Colour = None):
        """Set the colour for the highlight embed."""

        if colour is None:
            await self.config.colour.set(discord.Color.red().value)
            await ctx.send("The color has been reset.")
        else:
            await self.config.colour.set(colour.value)
            await ctx.send("The color has been set.")
        await self.generate_cache()

    @highlightset.command()
    async def restrict(self, ctx, toggle: bool):
        """Restrict the use of highlights to users with mod/admin permissions."""

        await self.config.restricted.set(toggle)
        if toggle:
            await ctx.send("Highlights can now only be used by users with mod/admin permissions.")
        else:
            await ctx.send("Highlights can now be used by all users.")
        await self.generate_cache()


def yes_or_no(boolean: bool):
    return "Yes" if boolean else "No"


def on_or_off(boolean: bool):
    return "On" if boolean else "Off"
