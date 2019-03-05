from redbot.core import commands, checks, Config
import discord


class Forward(commands.Cog):
    """Forward messages to the bot to the bot owner."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1398467138476)
        default_global = {"toggles": {"botmessages": True}}
        self.config.register_global(**default_global)

    async def sendowner(self, embed2):
        await self.bot.is_owner(discord.Object(id=None))
        owner = self.bot.get_user(self.bot.owner_id)
        await owner.send(embed=embed2)

    async def on_message(self, message):
        if message.guild is not None:
            return
        if message.channel.recipient.id == self.bot.owner_id:
            return
        if message.author == self.bot.user:
            async with self.config.toggles() as toggle:
                if not toggle['botmessages']:
                    return
            embed = discord.Embed(title=f"Sent PM to {message.channel.recipient}({message.channel.recipient.id}).",
                                  description=message.content,
                                  timestamp=message.created_at)
            await self.sendowner(embed)
        else:
            if message.attachments or not any(
                    message.content.startswith(prefix) for prefix in await self.bot.get_prefix(message)):
                embeds = []
                attachments_urls = []
                embeds.append(discord.Embed(description=message.content))
                embeds[0].set_author(name=f"{message.author} | {message.author.id}", icon_url=message.author.avatar_url)
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
                embeds[-1].timestamp = message.created_at
                for embed in embeds:
                    await self.sendowner(embed)

    @checks.is_owner()
    @commands.group(autohelp=True)
    async def forwardset(self, ctx):
        """Forwarding Commands"""
        pass

    @forwardset.command(aliases=["botmessage"])
    async def botmsg(self, ctx, type: bool):
        """Set whether to send notifications when the bot sends a message."""
        async with self.config.toggles() as toggles:
            if type:
                toggles['botmessages'] = True
                await ctx.send("Bot message notifications have been enabled.")
            else:
                toggles['botmessages'] = False
                await ctx.send("Bot message notifications have been disabled.")

    @commands.command()
    @checks.guildowner()
    async def pm(self, ctx, user_id: int, *, message: str):
        """PMs a person.
           Separate version of [p]dm but allows for guild owners."""
        user = discord.utils.get(ctx.bot.get_all_members(), id=user_id)
        e = discord.Embed(colour=discord.Colour.red(), description=message)

        if ctx.bot.user.avatar_url:
            e.set_author(name=f"Message from {ctx.author} | {ctx.author.id}", icon_url=ctx.bot.user.avatar_url)
        else:
            e.set_author(name=f"Message from {ctx.author} | {ctx.author.id}")

        try:
            await user.send(embed=e)
        except discord.HTTPException:
            await ctx.send("Sorry, I couldn't deliver your message to {}".format(user))
        else:
            await ctx.send("Message delivered to {}".format(user))
