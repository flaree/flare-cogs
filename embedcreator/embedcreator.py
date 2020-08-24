import json
from io import BytesIO, StringIO
from typing import Optional

import discord
from redbot.core import commands


class EmbedCreator(commands.Cog):

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.group()
    async def embed(self, ctx):
        """Group command for embed creator."""

    @embed.command()
    async def from_message(
        self, ctx, message_id: int, channel: Optional[discord.TextChannel] = None
    ):
        """Return the JSON in file format from an existing message."""
        channel = channel or ctx.channel
        try:
            message = await channel.fetch_message(message_id)
        except discord.HTTPException:
            return await ctx.maybe_send_embed("No such message")

        if not message.embeds:
            return await ctx.send("This message doesn't appear to have an embed.")
        data = message.embeds[0].to_dict()
        io = StringIO(json.dumps(data))
        io.seek(0)
        await ctx.send(
            "Here is that embed contents as a json.",
            file=discord.File(io, filename="embedcontents.json"),
        )

    @embed.command(name="file")
    async def embed_file(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Send an embed from a json file."""
        channel = channel or ctx.channel
        if not channel.permissions_for(ctx.me).send_messages:
            return await ctx.send(f"I do not have permission to send messages in {channel}.")
        if not channel.permissions_for(ctx.author).send_messages:
            return await ctx.send(f"You do not have permission to send messages in {channel}.")

        if not ctx.message.attachments:
            return await ctx.send("You need to upload a file for this command to work")
        with BytesIO() as fp:
            await ctx.message.attachments[0].save(fp)
            data = fp.read().decode("utf-8")
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError:
            return await ctx.send(
                "Unable to read JSON, ensure it is correctly formatted and validated."
            )
        try:
            embed = discord.Embed().from_dict(data)
        except Exception as e:
            return await ctx.send(
                "Oops. An error occured turning the input to an embed. Please validate the file and ensure it is using the correct keys."
            )
        await ctx.send(embed=embed)

    @embed.command(name="json")
    async def embed_json(self, ctx, *, raw_json: str):
        """Send an embed from directly pasting json."""
        channel = ctx.channel
        if not channel.permissions_for(ctx.me).send_messages:
            return await ctx.send(f"I do not have permission to send messages in {channel}.")
        if not channel.permissions_for(ctx.author).send_messages:
            return await ctx.send(f"You do not have permission to send messages in {channel}.")
        try:
            data = json.loads(raw_json)
        except json.decoder.JSONDecodeError:
            return await ctx.send(
                "Unable to read JSON, ensure it is correctly formatted and validated."
            )
        try:
            embed = discord.Embed().from_dict(data)
        except Exception as e:
            return await ctx.send(
                "Oops. An error occured turning the input to an embed. Please validate the file and ensure it is using the correct keys."
            )
        await ctx.send(embed=embed)
