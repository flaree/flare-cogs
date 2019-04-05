from redbot.core import commands, Config, checks
import discord


class Highlight(commands.Cog):
    """Be notified when keywords are sent.."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476, force_registration=True)
        default_channel = {"highlight": {}, "toggle": {}}
        self.config.register_channel(**default_channel)

    async def on_message(self, message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        async with self.config.channel(message.channel).highlight() as highlight:
            for user in highlight:
                if highlight[user].lower() in message.content.lower():
                    async with self.config.channel(message.channel).toggle() as toggle:
                        if not toggle[user]:
                            return
                    before = []
                    async for messages in message.channel.history(limit=5, before=message, reverse=False):
                        before.append(messages)
                    highlighted = self.bot.get_user(int(user))
                    embed = discord.Embed(
                        title="Context:", colour=0xFF0000, timestamp=message.created_at,
                        description="{}\n{}".format("\n".join([f"**{x.author}**: {x.content}" for x in before]),
                                                    f"**{message.author}**: {message.content}")
                    )
                    embed.add_field(name="Jump",
                                    value=f"[Click for context](https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id})")
                    await highlighted.send(
                        "Your highligted word `{}` was mention in <#{}> on {}.\n".format(
                            highlight[user],
                            message.channel.id,
                            message.guild.name
                        )
                    )
                    await highlighted.send(embed=embed)

    @commands.group(autohelp=True)
    async def highlight(self, ctx):
        """Highlighting Commands"""
        pass

    @highlight.command()
    async def add(self, ctx, *, text: str):
        """Add a word to be highlighted on.
           Note: 1 notification setting per channel."""
        async with self.config.channel(ctx.channel).highlight() as highlight:
            highlight[f"{ctx.author.id}"] = text
            await ctx.send(f"The word `{text}` has been added to your highlight list.")
        async with self.config.channel(ctx.channel).toggle() as toggle:
            if str(ctx.author.id) not in toggle:
                toggle[f"{ctx.author.id}"] = False

    @highlight.command()
    async def remove(self, ctx):
        """Remove highlighting in a certain channel"""
        async with self.config.channel(ctx.channel).highlight() as highlight:
            if str(ctx.author.id) in highlight:
                await ctx.send(
                    f"Highlighted word `{highlight[f'{ctx.author.id}']}` has been removed successfully."
                )
                del highlight[f"{ctx.author.id}"]

            else:
                await ctx.send(
                    "You currently do not have a highlighted word setup in this channel."
                )

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
    async def list(self, ctx):
        """Current highlight settings for the current channel."""
        async with self.config.channel(ctx.channel).highlight() as highlight:
            if str(ctx.author.id) in highlight:
                async with self.config.channel(ctx.channel).toggle() as toggle:
                    try:
                        embed = discord.Embed(
                            title=f"Current highlighted text for {ctx.author.display_name} in {ctx.message.channel}:",
                            description=f"**Word**: {highlight[f'{ctx.author.id}']}\n**Toggle**: {toggle[f'{ctx.author.id}']}",
                        )
                    except KeyError:
                        embed = discord.Embed(
                            title=f"Current highlighted text for {ctx.author.display_name} in {ctx.message.channel}:",
                            description=f"**Word**: {highlight[f'{ctx.author.id}']}\n**Toggle**: Use [p]highlight toggle",
                        )

                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    "You currently do not have any highlighted text set up in this channel."
                )
