import asyncio
import logging
from typing import Optional

import discord
import tabulate
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, humanize_list
from redbot.core.utils.predicates import MessagePredicate

logger = logging.getLogger("red.flare.highlight")


class Highlight(commands.Cog):
    """Be notified when keywords are sent."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        self.config.register_global(migrated=False)
        default_channel = {"highlight": {}, "toggle": {}, "bots": {}}
        self.config.register_channel(**default_channel)
        self.highlightcache = {}

    __version__ = "1.3.0"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    async def initalize(self):
        await self.bot.wait_until_ready()
        await self.migrate_config()
        await self.generate_cache()

    async def generate_cache(self):
        self.highlightcache = await self.config.all_channels()

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
        highlight = self.highlightcache.get(message.channel.id)
        if highlight is None:
            return
        highlight = highlight.get("highlight", [])
        for user in highlight:
            if int(user) == message.author.id:
                continue
            highlited_words = []
            for word in highlight[user]:
                if word.lower() in message.content.lower():
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
                    highlited_words.append(word)
            if highlited_words:
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
                    f"Your highlighted word(s) `{humanize_list(highlited_words)}` was mentioned in <#{message.channel.id}> in {message.guild.name} by {message.author.display_name}.\n",
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

    @highlight.command()
    async def add(self, ctx, channel: Optional[discord.TextChannel] = None, *, text: str):
        """Add a word to be highlighted on.

        Text will be converted to lowercase.\nCan also provide an optional channel arguement for
        the highlight to be applied to that channel.
        """
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        async with self.config.channel(channel).highlight() as highlight:
            if str(ctx.author.id) not in highlight:
                highlight[f"{ctx.author.id}"] = {}
            if text.lower() not in highlight[f"{ctx.author.id}"]:
                highlight[f"{ctx.author.id}"][text.lower()] = {"toggle": False, "bots": False}
                await ctx.send(
                    f"The word `{text}` has been added to your highlight list for {channel}."
                )
            else:
                await ctx.send(f"The word {text} is already in your highlight list for {channel}.")
        await self.generate_cache()

    @highlight.command()
    async def remove(self, ctx, channel: Optional[discord.TextChannel] = None, *, word: str):
        """Remove highlighting in a channel.

        An optional channel can be provided to remove a highlight from that channel.
        """
        word = word.lower()
        channel = channel or ctx.channel
        check = self.channel_check(ctx, channel)
        if not check:
            await ctx.send("Either you or the bot does not have permission for that channel.")
            return
        async with self.config.channel(channel).highlight() as highlight:
            highlights = highlight.get(str(ctx.author.id))
            if not highlights:
                return await ctx.send(f"You don't have any highlights setup in {channel}")
            if word in highlight[f"{ctx.author.id}"]:
                await ctx.send(
                    f"Highlighted word `{word}` has been removed from {channel} successfully."
                )
                del highlight[f"{ctx.author.id}"][word]

            else:
                await ctx.send("Your word is not currently setup in that channel..")
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
                return
            await ctx.send("All your highlights have been disabled.")
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
                return await ctx.send(f"The highlight `{word}` has been enabled in {channel}.")
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
                    return
                await ctx.send("Bots will no longer trigger on any of your highlights.")
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
                return await ctx.send(
                    f"The highlight `{word}` will now be triggered by bots in {channel}."
                )
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
                ]
                for word in highlight[f"{ctx.author.id}"]
            ]
            embed = discord.Embed(
                title=f"Current highlighted text for {ctx.author.display_name} in {channel}:",
                colour=ctx.author.colour,
                description=box(
                    tabulate.tabulate(
                        sorted(words, key=lambda x: x[1], reverse=True),
                        headers=["Word", "Toggle", "Ignoring Bots"],
                    ),
                    lang="prolog",
                ),
            )

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"You currently do not have any highlighted words set up in {channel}.")


def yes_or_no(boolean):
    if boolean:
        return "Yes"
    return "No"


def on_or_off(boolean):
    if boolean:
        return "On"
    return "Off"
