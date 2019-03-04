from redbot.core import commands
import discord


class Forward(commands.Cog):
    """Forward messages to the bot to the bot owner."""

    def __init__(self, bot):
        self.bot = bot

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
