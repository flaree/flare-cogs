import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import humanize_list


class Forward(commands.Cog):
    """Forward messages sent to the bot to the bot owner or in a specified channel."""

    __version__ = "1.2.9"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot

        self.config = Config.get_conf(self, 1398467138476, force_registration=True)
        default_global = {"toggles": {"botmessages": False}, "destination": None, "blacklist": []}
        self.config.register_global(**default_global)

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    async def _destination(self, msg: str = None, embed: discord.Embed = None):
        await self.bot.wait_until_ready()
        channel = await self.config.destination()
        channel = self.bot.get_channel(channel)
        if channel is None:
            await self.bot.send_to_owners(msg, embed=embed)
        else:
            await channel.send(msg, embed=embed)

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
        recipient = message.channel.recipient
        if recipient is None:
            chan = self.bot.get_channel(message.channel.id)
            if chan is None:
                chan = await self.bot.fetch_channel(message.channel.id)
            if not isinstance(chan, discord.DMChannel):
                return
            recipient = chan.recipient
        if recipient.id in self.bot.owner_ids:
            return
        if not await self.bot.allowed_by_whitelist_blacklist(message.author):
            return
        if message.author.id in await self.config.blacklist():
            return
        msg = ""
        if message.author == self.bot.user:
            async with self.config.toggles() as toggle:
                if not toggle["botmessages"]:
                    return
            msg = f"Sent PM to {recipient} (`{recipient.id}`)"
            if message.embeds:
                msg += f"\n**Message Content**: {message.content}"
                embeds = [
                    discord.Embed.from_dict(
                        {**message.embeds[0].to_dict(), "timestamp": str(message.created_at)}
                    )
                ]
            else:
                embeds = [discord.Embed(description=message.content)]
                embeds[0].set_author(
                    name=f"{message.author} | {message.author.id}",
                    icon_url=message.author.display_avatar,
                )
                embeds = self._append_attachements(message, embeds)
                embeds[-1].timestamp = message.created_at
        else:
            embeds = [discord.Embed(description=message.content)]
            embeds[0].set_author(
                name=f"{message.author} | {message.author.id}",
                icon_url=message.author.display_avatar.url,
            )
            embeds = self._append_attachements(message, embeds)
            embeds[-1].timestamp = message.created_at
        for embed in embeds:
            await self._destination(msg=msg, embed=embed)

    @checks.is_owner()
    @commands.group()
    async def forwardset(self, ctx):
        """Forwarding commands."""

    @forwardset.command(aliases=["botmessage"])
    async def botmsg(self, ctx, type: bool = None):
        """Set whether to send notifications when the bot sends a message.

        Type must be a valid bool.
        """
        async with self.config.toggles() as toggles:
            if type is None:
                type = not toggles.get("botmessages")
            if type:
                toggles["botmessages"] = True
                await ctx.send("Bot message notifications have been enabled.")
            else:
                toggles["botmessages"] = False
                await ctx.send("Bot message notifications have been disabled.")

    @forwardset.command()
    async def channel(self, ctx, channel: discord.TextChannel = None):
        """Set if you want to receive notifications in a channel instead of your DMs.

        Leave blank if you want to set back to your DMs.
        """
        data = (
            {"msg": "Notifications will be sent in your DMs.", "config": None}
            if channel is None
            else {"msg": f"Notifications will be sent in {channel.mention}.", "config": channel.id}
        )
        await self.config.destination.set(data["config"])
        await ctx.send(data["msg"])

    @forwardset.command(aliases=["bl"])
    async def blacklist(self, ctx: commands.Context, user_id: int = None):
        """Blacklist receiving messages from a user."""
        if not user_id:
            e = discord.Embed(
                color=await ctx.embed_color(),
                title="Forward Blacklist",
                description=humanize_list(await self.config.blacklist()),
            )
            await ctx.send(embed=e)
        else:
            if user_id in await self.config.blacklist():
                await ctx.send("This user is already blacklisted.")
                return
            async with self.config.blacklist() as b:
                b.append(user_id)
            await ctx.tick()

    @forwardset.command(aliases=["unbl"])
    async def unblacklist(self, ctx: commands.Context, user_id: int):
        """Remove a user from the blacklist."""
        if user_id not in await self.config.blacklist():
            await ctx.send("This user is not in the blacklist.")
            return
        async with self.config.blacklist() as b:
            index = b.index(user_id)
            b.pop(index)
        await ctx.tick()

    @commands.command()
    @commands.guild_only()
    @checks.guildowner()
    async def pm(self, ctx, user: discord.Member, *, message: str):
        """PMs a person.

        Separate version of [p]dm but allows for guild owners. This only works for users in the
        guild.
        """
        em = discord.Embed(colour=discord.Colour.red(), description=message)

        if ctx.bot.user.display_avatar:
            em.set_author(
                name=f"Message from {ctx.author} | {ctx.author.id}",
                icon_url=ctx.bot.user.display_avatar,
            )
        else:
            em.set_author(name=f"Message from {ctx.author} | {ctx.author.id}")

        try:
            await user.send(embed=em)
        except discord.Forbidden:
            await ctx.send(
                "Oops. I couldn't deliver your message to {}. They most likely have me blocked or DMs closed!"
            )
        await ctx.send(f"Message delivered to {user}")
