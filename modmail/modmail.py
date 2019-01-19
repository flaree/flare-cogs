from redbot.core import commands, Config, checks
import discord


class Modmail(commands.Cog):
    """Forward messages to a set channel."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476)
        default_global = {"modmail": {}, "toggle": {"status": True}}
        self.config.register_global(**default_global)

    async def channelsend(self, embed2):
        async with self.config.toggle() as toggle:
            if not toggle['status']:
                return
        async with self.config.modmail() as modmail:
            for stats in modmail:
                channel = self.bot.get_channel(modmail[stats])
                await channel.send(embed=embed2)

    async def on_message(self, message):
        if message.guild is not None:
            return
        if message.channel.recipient.id == self.bot.owner_id:
            return
        if message.author == self.bot.user:
            return
        if message.content[0] not in await self.bot.get_prefix(message):
            embed = discord.Embed(description=message.content, timestamp=message.created_at)
            embed.set_author(name=message.author, icon_url=message.author.avatar_url)
            await self.channelsend(embed)

    @checks.is_owner()
    @commands.group(autohelp=True)
    async def modmail(self, ctx):
        """Modmail Commands"""
        pass

    @modmail.command()
    async def set(self, ctx, channel: discord.TextChannel):
        """Set the channel that the bot will post to - Mention the channel."""
        async with self.config.modmail() as modmail:
            key = str(ctx.message.guild.id)
            modmail[key] = channel.id
        await ctx.send("Channel added successfully.")

    @modmail.command()
    async def list(self, ctx):
        """List all current modmail channels."""
        async with self.config.modmail() as modmail:
            if len(modmail) == 0:
                await ctx.send("No channels are currently set.")
            for stats in modmail:
                await ctx.send(modmail[stats])

    @modmail.command()
    async def toggle(self, ctx, mode: bool):
        """Toggle modmail."""
        async with self.config.toggle() as toggle:
            if mode:
                toggle['status'] = True
                await ctx.send("ModMail is now enabled.")
            else:
                toggle['status'] = False
                await ctx.send("ModMail is now disabled.")
