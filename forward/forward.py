from redbot.core import commands, checks, Config
import discord

from typing import Union


class Forward(commands.Cog):
    """Forward messages sent to the bot to the bot owner or in a specified channel."""

    __version__ = "1.2.3"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, 1398467138476, force_registration=True)
        default_global = {"toggles": {"botmessages": True}, "destination": None}
        self.config.register_global(**default_global)

    async def _destination(self, msg: str = None, embed: discord.Embed = None):
        await self.bot.wait_until_ready()
        channel = await self.config.destination()
        destination = (
            self.bot.get_channel(channel) if channel else self.bot.get_user(self.bot.owner_id)
        )
        await destination.send(msg, embed=embed)

    @staticmethod
    def _append_attachements(message: discord.Message, embeds: list):
        attachments_urls = []
        for attachment in message.attachments:
            if any(attachment.filename.endswith(imageext) for imageext in ["jpg", "png", "gif"]):
                if embeds[0].image:
                    embed = discord.Embed()
                    embed.set_image(url=attachment.url)
                    embeds.append(embed)
                else:
                    embeds[0].set_image(url=attachment.url)
            else:
                attachments_urls.append(f"[{attachment.filename}]({attachment.url})")
        if attachments_urls:
            embeds[0].add_field(name="Attachments", value="\n".join(attachments_urls))
        return embeds

    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        if message.guild is not None:
            return
        if message.channel.recipient.id == self.bot.owner_id:
            return
        if message.author == self.bot.user:
            async with self.config.toggles() as toggle:
                if not toggle["botmessages"]:
                    return
            msg = f"Sent PM to {message.channel.recipient} (`{message.channel.recipient.id}`)"
            if message.embeds:
                embed = discord.Embed.from_dict(
                    {**message.embeds[0].to_dict(), "timestamp": str(message.created_at)}
                )
            else:
                embed = discord.Embed(description=message.content, timestamp=message.created_at)
            await self._destination(msg, embed)
        else:
            embeds = []
            embeds.append(discord.Embed(description=message.content))
            embeds[0].set_author(
                name=f"{message.author} | {message.author.id}", icon_url=message.author.avatar_url
            )
            embeds = self._append_attachements(message, embeds)
            embeds[-1].timestamp = message.created_at
            for embed in embeds:
                await self._destination(msg=None, embed=embed)

    @checks.is_owner()
    @commands.group()
    async def forwardset(self, ctx):
        """Forwarding commands."""
        pass

    @forwardset.command(aliases=["botmessage"])
    async def botmsg(self, ctx, type: bool):
        """
        Set whether to send notifications when the bot sends a message.
        Type must be a valid bool.
        """
        async with self.config.toggles() as toggles:
            if type:
                toggles["botmessages"] = True
                await ctx.send("Bot message notifications have been enabled.")
            else:
                toggles["botmessages"] = False
                await ctx.send("Bot message notifications have been disabled.")

    @forwardset.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """
        Set if you want to receive notifications in a channel instead of your DMs.
        Leave blank if you want to set back to your DMs.
        """
        data = (
            {"msg": "Notifications will be sent in your DMs.", "config": None}
            if channel is None
            else {"msg": f"Notifications will be sent in {channel.mention}.", "config": channel.id}
        )
        await self.config.destination.set(data["config"])
        await ctx.send(data["msg"])

    @commands.command()
    @commands.guild_only()
    @checks.guildowner()
    async def pm(self, ctx, user: discord.Member, *, message: str):
        """
        PMs a person.
        Separate version of [p]dm but allows for guild owners.
        This only works for users in the guild.
        """
        em = discord.Embed(colour=discord.Colour.red(), description=message)

        if ctx.bot.user.avatar_url:
            em.set_author(
                name=f"Message from {ctx.author} | {ctx.author.id}",
                icon_url=ctx.bot.user.avatar_url,
            )
        else:
            em.set_author(name=f"Message from {ctx.author} | {ctx.author.id}")

        try:
            await user.send(embed=em)
        except discord.Forbidden:
            await ctx.send(
                "Oops. I couldn't deliver your message to {}. They most likely have me blocked or DMs closed!"
            )
        await ctx.send("Message delivered to {}".format(user))
