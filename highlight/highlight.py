from redbot.core import commands, Config, checks
import discord
from typing import Optional, Union


class Highlight(commands.Cog):
    """Be notified when keywords are sent."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        default_channel = {"highlight": {}, "toggle": {}}
        self.config.register_channel(**default_channel)

    __version__ = "1.1.3"

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        highlight = await self.config.channel(message.channel).highlight()
        for user in highlight:
            if int(user) == message.author.id:
                continue
            for word in highlight[user]:
                if word.lower() in message.content.lower():
                    if message.author.bot:
                        return
                    toggle = await self.config.channel(message.channel).toggle()
                    if not toggle[user]:
                        continue
                    msglist = []
                    async for messages in message.channel.history(
                        limit=5, before=message, oldest_first=False
                    ):
                        msglist.append(messages)
                    msglist.reverse()
                    msglist.append(message)
                    highlighted = self.bot.get_user(int(user))
                    if highlighted is None:
                        highlighted = await self.bot.fetch_user(int(user))
                    if highlighted not in message.guild.members:
                        continue
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
                    await highlighted.send(
                        f"Your highlighted word `{word}` was mentioned in <#{message.channel.id}> in {message.guild.name} by {message.author.display_name}.\n",
                        embed=embed,
                    )

    @commands.group(autohelp=True)
    async def highlight(self, ctx):
        """Highlighting Commands"""
        pass

    @highlight.command()
    async def add(self, ctx, channel: Optional[discord.TextChannel] = None, *, text: str):
        """Add a word to be highlighted on."""
        if channel is None:
            channel = ctx.channel
        async with self.config.channel(channel).highlight() as highlight:
            if str(ctx.author.id) not in highlight:
                highlight[f"{ctx.author.id}"] = {}
            if text not in highlight[f"{ctx.author.id}"]:
                highlight[f"{ctx.author.id}"][text] = None
                await ctx.send(
                    f"The word `{text}` has been added to your highlight list for {channel}."
                )
            else:
                await ctx.send(f"The word {text} is already in your highlight list for {channel}.")
        async with self.config.channel(channel).toggle() as toggle:
            if str(ctx.author.id) not in toggle:
                toggle[f"{ctx.author.id}"] = False

    @highlight.command()
    async def remove(self, ctx, channel: Optional[discord.TextChannel] = None, *, word: str):
        """Remove highlighting in a certain channel"""
        if channel is None:
            channel = ctx.channel
        async with self.config.channel(channel).highlight() as highlight:
            try:
                if word in highlight[f"{ctx.author.id}"]:
                    await ctx.send(
                        f"Highlighted word `{word}` has been removed from {channel} successfully."
                    )
                    del highlight[f"{ctx.author.id}"][word]

                else:
                    await ctx.send("Your word is not currently setup in that channel..")
            except KeyError:
                await ctx.send("You do not have any highlighted words in that channel.")

    @highlight.command()
    async def toggle(self, ctx, state: bool):
        """Toggle highlighting - must be a valid bool."""
        async with self.config.channel(ctx.channel).toggle() as toggle:
            if state:
                toggle[f"{ctx.author.id}"] = state
                await ctx.send(
                    "{} has enabled their highlighting in this channel.".format(ctx.author.name)
                )
            elif not state:
                toggle[f"{ctx.author.id}"] = state
                await ctx.send(
                    "{} has disabled their highlighting in this channel.".format(ctx.author.name)
                )

    @highlight.command(name="list")
    async def _list(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Current highlight settings for the current channel."""
        channel = channel or ctx.channel
        highlight = await self.config.channel(channel).highlight()
        if str(ctx.author.id) in highlight and highlight[f"{ctx.author.id}"]:
            toggle = await self.config.channel(channel).toggle()
            words = [word for word in highlight[f"{ctx.author.id}"]]
            words = "\n".join(words)
            embed = discord.Embed(
                title=f"Current highlighted text for {ctx.author.display_name} in {channel}:",
                colour=ctx.author.colour,
            )
            embed.add_field(name="Words:", value=words)
            embed.add_field(name="Toggled:", value="Yes" if toggle[f"{ctx.author.id}"] else "No")

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"You currently do not have any highlighted words set up in {channel}.")
