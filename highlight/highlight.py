import asyncio
import logging
import re
from io import BytesIO
from typing import Literal, Optional

import discord
import tabulate
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box, humanize_list, inline, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

logger = logging.getLogger("red.flare.highlight")


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


class Highlight(commands.Cog):
    """Be notified when keywords are sent."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        self.config.register_global(migrated=False)
        self.config.register_member(blacklist=[], whitelist=[])
        default_channel = {"highlight": {}}
        self.config.register_channel(**default_channel)
        self.highlightcache = {}
        self.whitelist_blacklist = {}
        self.recache = {}

    async def red_get_data_for_user(self, *, user_id: int):
        data = []
        config = await self.config.all_channels()
        for channel in config:
            if str(user_id) in config[channel]["highlight"]:
                data.append(channel, config[channel]["highlight"][str(user_id)])
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
        data = []
        config = await self.config.all_channels()
        for channel in config:
            if str(user_id) in config[channel]["highlight"]:
                data.append(channel)
        for channel in data:
            async with self.config.channel_from_id(channel).highlight() as highlight:
                del highlight[str(user_id)]
        await self.generate_cache()

    __version__ = "1.4.2"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    async def initalize(self):
        await self.migrate_config()
        await self.generate_cache()

    async def generate_cache(self):
        self.highlightcache = await self.config.all_channels()
        self.whitelist_blacklist = await self.config.all_members()
        # self.guildcache = await self.config.all_guilds()

    async def migrate_config(self):
        if not await self.config.migrated():
            a = {}
            conf = await self.config.all_channels()
            for channel in conf:
                a[channel] = {}
                for user in conf[channel]["highlight"]:
                    a[channel][user] = {}
                    for highlight in conf[channel]["highlight"][user]:
                        a[channel][user][highlight] = {
                            "toggle": conf[channel]["toggle"][user],
                            "bots": False,
                        }
            group = self.config._get_base_group(self.config.CHANNEL)
            async with group.all() as new_data:
                for channel in a:
                    new_data[channel] = {"highlight": a[channel]}
            await self.config.migrated.set(True)
            logger.info("Migration complete.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        highlight = self.highlightcache.get(message.channel.id)
        # highlight_guild = self.guildcache.get(message.guild.id)
        if highlight is None:
            return
        # highlight_guild = highlight_guild.get("highlight", [])
        highlight = highlight.get("highlight", [])
        for user in highlight:
            if int(user) == message.author.id:
                continue
            if self.whitelist_blacklist.get(message.guild.id, False):
                if self.whitelist_blacklist[message.guild.id].get(int(user), False):
                    if (
                        self.whitelist_blacklist[message.guild.id][int(user)]["whitelist"]
                        and message.author.id
                        not in self.whitelist_blacklist[message.guild.id][int(user)]["whitelist"]
                    ):
                        continue
                    elif (
                        self.whitelist_blacklist[message.guild.id][int(user)]["blacklist"]
                        and message.author.id
                        in self.whitelist_blacklist[message.guild.id][int(user)]["blacklist"]
                    ):
                        continue
            highlighted_words = []
            for word in highlight[user]:
                if word in highlighted_words:
                    continue
                if highlight[user][word].get("boundary", False):
                    if word.lower() in self.recache:
                        pattern = self.recache[word.lower()]
                    else:
                        pattern = re.compile(rf"\b{re.escape(word.lower())}\b", flags=re.I)
                        self.recache[word.lower()] = pattern
                    if set(pattern.findall(message.content.lower())):
                        highlighted_usr = message.guild.get_member(int(user))
                        if highlighted_usr is None:
                            continue
                        if not message.channel.permissions_for(highlighted_usr).read_messages:
                            continue
                        if message.author.bot:
                            if not highlight[user][word]["bots"]:
                                continue

                        if not highlight[user][word]["toggle"]:
                            continue
                        highlighted_words.append(word)
                elif word.lower() in message.content.lower():
                    highlighted_usr = message.guild.get_member(int(user))
                    if highlighted_usr is None:
                        continue
                    if not message.channel.permissions_for(highlighted_usr).read_messages:
                        continue
                    if message.author.bot:
                        if not highlight[user][word]["bots"]:
                            continue

                    if not highlight[user][word]["toggle"]:
                        continue
                    highlighted_words.append(word)
            if highlighted_words:
                msglist = []
                msglist.append(message)
                async for messages in message.channel.history(
                    limit=5, before=message, oldest_first=False
                ):
                    msglist.append(messages)
                msglist.reverse()
                context = "\n".join([f"**{x.author}**: {x.content}" for x in msglist])
                if len(context) > 2000:
                    context = "**Context omitted due to message size limits.\n**"
                embed = discord.Embed(
                    title="Context:",
                    colour=0xFF0000,
                    timestamp=message.created_at,
                    description="{}".format(context),
                )
                embed.add_field(name="Jump", value=f"[Click for context]({message.jump_url})")
                await highlighted_usr.send(
                    f"Your highlighted word{'s' if len(highlighted_words) > 1 else ''} {humanize_list(list(map(inline, highlighted_words)))} was mentioned in {message.channel.mention} in {message.guild.name} by {message.author.display_name}.\n",
                    embed=embed,
                )

    def channel_check(self, ctx, channel):
        return (
            channel.permissions_for(ctx.author).read_messages
            and channel.permissions_for(ctx.me).read_message_history
        )

    @commands.guild_only()
    @commands.group(autohelp=True)
    async def highlight(self, ctx):
        """Highlighting Commands."""

    @highlight.group()
    async def whitelist(self, ctx):
        """Manage highlight whitelist.

        Whitelist takes priority over blacklist."""

    @highlight.group()
    async def blacklist(self, ctx):
        """Manage highlight blacklist.

        Whitelist takes priority over blacklist."""

    @whitelist.command(name="user")
    async def whitelist_addremove(self, ctx, user: discord.Member):
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
    async def whitelist_list(self, ctx):
        """List those in your whitelist."""
        whitelist = await self.config.member(ctx.author).whitelist()
        if not whitelist:
            return await ctx.send("Your whitelist is empty.")
        msg = ""
        for _id in whitelist:
            msg += f" - {_id}\n"
        for page in pagify(msg):
            await ctx.send(box(page))

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx):
        """List those in your blacklist."""
        blacklist = await self.config.member(ctx.author).blacklist()
        if not blacklist:
            return await ctx.send("Your blacklist is empty.")
        msg = ""
        for _id in blacklist:
            msg += f" - {_id}\n"
        for page in pagify(msg):
            await ctx.send(box(page))

    @blacklist.command(name="user")
    async def blacklist_addremove(self, ctx, user: discord.Member):
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

    @highlight.command()
    async def add(self, ctx, channel: Optional[discord.TextChannel] = None, *text: str):
        """Add a word to be highlighted on.

        Text will be converted to lowercase.\nCan also provide an optional channel arguement for
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
    async def remove(self, ctx, channel: Optional[discord.TextChannel] = None, *text: str):
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
        self, ctx, state: bool, channel: Optional[discord.TextChannel] = None, *, word: str = None
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
        self, ctx, state: bool, channel: Optional[discord.TextChannel] = None, *, word: str = None
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
                return

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
    async def _list(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Current highlight settings for a channel.

        A channel arguement can be supplied to view settings for said channel.
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
        self, ctx, state: bool, channel: Optional[discord.TextChannel] = None, *, word: str = None
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
                return

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


def yes_or_no(boolean):
    if boolean:
        return "Yes"
    return "No"


def on_or_off(boolean):
    if boolean:
        return "On"
    return "Off"
