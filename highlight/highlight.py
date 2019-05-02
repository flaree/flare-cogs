from redbot.core import commands, Config, checks
import discord
from typing import Optional


class Highlight(commands.Cog):
    """Be notified when keywords are sent.."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        default_channel = {"highlight": {}, "toggle": {}, "ignore": {}}
        self.config.register_channel(**default_channel)

    async def on_message(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        async with self.config.channel(message.channel).highlight() as highlight:
            for user in highlight:
                for word in highlight[user]:
                    if word.lower() in message.content.lower():
                        if message.author.bot:
                            async with self.config.channel(message.channel).ignore() as ignorebots:
                                if not ignorebots[user]:
                                    return
                        async with self.config.channel(message.channel).toggle() as toggle:
                            if not toggle[user]:
                                return
                        before = []
                        async for messages in message.channel.history(
                            limit=5, before=message, reverse=False
                        ):
                            before.append(messages)
                        highlighted = self.bot.get_user(int(user))
                        context = "\n".join([f"**{x.author}**: {x.content}" for x in before])
                        if len(context) > 2000:
                            context = "**Context omitted due to message size limits.\n**"
                        embed = discord.Embed(
                            title="Context:",
                            colour=0xFF0000,
                            timestamp=message.created_at,
                            description="{}\n{}".format(context,
                                f"**{message.author}**: {message.content}",
                            ),
                        )
                        embed.add_field(
                            name="Jump",
                            value=f"[Click for context](https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id})",
                        )
                        await highlighted.send(
                            f"Your highlighted word `{word}` was mentioned in <#{message.channel.id}> in {message.guild.name}.\n",
                            embed=embed,
                        )

    @commands.group(autohelp=True)
    async def highlight(self, ctx):
        """Highlighting Commands"""
        pass

    @highlight.command()
    async def add(self, ctx, *, text: str):
        """Add a word to be highlighted on."""
        async with self.config.channel(ctx.channel).highlight() as highlight:
            if str(ctx.author.id) not in highlight:
                highlight[f"{ctx.author.id}"] = {}
            if text not in highlight[f"{ctx.author.id}"]:
                highlight[f"{ctx.author.id}"][text] = None
                await ctx.send(f"The word `{text}` has been added to your highlight list.")
            else:
                await ctx.send(f"The word {text} is already in your highlight list.")
        async with self.config.channel(ctx.channel).toggle() as toggle:
            if str(ctx.author.id) not in toggle:
                toggle[f"{ctx.author.id}"] = False
        async with self.config.channel(ctx.channel).ignore() as ignore:
            if str(ctx.author.id) not in ignore:
                ignore[f"{ctx.author.id}"] = True

    @highlight.command()
    async def remove(self, ctx, *, word: str):
        """Remove highlighting in a certain channel"""
        channel = ctx.channel
        async with self.config.channel(channel).highlight() as highlight:
            try:
                if word in highlight[f"{ctx.author.id}"]:
                    await ctx.send(f"Highlighted word `{word}` has been removed successfully.")
                    del highlight[f"{ctx.author.id}"][word]

                else:
                    await ctx.send("Your word is not currently setup in this channel..")
            except KeyError:
                await ctx.send("You do not have any highlighted words in this channel.")

    @highlight.command()
    async def toggle(self, ctx, state: bool):
        """Toggle highlighting - must be a valid bool."""
        async with self.config.channel(ctx.channel).toggle() as toggle:
            if state:
                toggle[f"{ctx.author.id}"] = state
                await ctx.send("You've enabled highlighting on this channel.")
            elif not state:
                toggle[f"{ctx.author.id}"] = state
                await ctx.send("You've disabled highlighting on this channel.")

    @highlight.command()
    async def bots(self, ctx, state: bool):
        """Toggle highlighting on bot messages."""
        async with self.config.channel(ctx.channel).ignore() as ignore:
            if state:
                ignore[f"{ctx.author.id}"] = state
                await ctx.send("Bots messages will now be included in highlighted messages")
            elif not state:
                ignore[f"{ctx.author.id}"] = state
                await ctx.send("Bot messages will not longer be highlighted.")

    @highlight.command()
    async def list(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Current highlight settings for the current channel."""
        channel = channel or ctx.channel
        async with self.config.channel(channel).highlight() as highlight:
            if str(ctx.author.id) in highlight and highlight[f"{ctx.author.id}"]:
                async with self.config.channel(channel).toggle() as toggle:
                    async with self.config.channel(ctx.channel).ignore() as ignore:
                        words = [word for word in highlight[f"{ctx.author.id}"]]
                        words = "\n".join(words)
                        try:
                            embed = discord.Embed(
                                title=f"Current highlighted text for {ctx.author.display_name} in {channel}:",
                                description=f"**Word(s)**: {words}\n**Toggle**: {toggle[f'{ctx.author.id}']}\n**Ignoring Bots**: {not ignore[f'{ctx.author.id}']}",
                            )
                        except KeyError:
                            embed = discord.Embed(
                                title=f"Current highlighted text for {ctx.author.display_name} in {channel}:",
                                description=f"**Word(s)**: {words}\n**Toggle**: Use [p]highlight toggle",
                            )

                    await ctx.send(embed=embed)
            else:
                await ctx.send(
                    "You currently do not have any highlighted text set up in that channel."
                )
