import traceback
from io import BytesIO
from typing import Optional

import discord
from redbot.core import commands

from .abc import MixinMeta
from .embedmixin import embed


class EmbedSending(MixinMeta):
    @embed.command(name="file")
    @commands.bot_has_permissions(embed_links=True)
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
        await self.build_embed(ctx, data=data, channel=channel)

    @embed.command(name="json")
    @commands.bot_has_permissions(embed_links=True)
    async def embed_json(self, ctx, *, raw_json: str):
        """Send an embed from directly pasting json."""
        channel = ctx.channel
        raw_json = self.cleanup_code(raw_json)
        if not channel.permissions_for(ctx.me).send_messages:
            return await ctx.send(f"I do not have permission to send messages in {channel}.")
        if not channel.permissions_for(ctx.author).send_messages:
            return await ctx.send(f"You do not have permission to send messages in {channel}.")
        await self.build_embed(ctx, data=raw_json, channel=channel)

    @embed.command()
    @commands.bot_has_permissions(embed_links=True)
    async def send(self, ctx, channel: Optional[discord.TextChannel] = None, *, name: str):
        """Send a saved embed."""
        channel = channel or ctx.channel
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist in this guild.")
        data = embeds_stored[name]["data"]
        await self.build_embed(ctx, data=data, channel=channel)

    @embed.command()
    @commands.bot_has_permissions(embed_links=True)
    async def edit(self, ctx, message: discord.Message, *, name: str):
        """Edit a bot sent message with a new embed.

        Message format is in messageID format.
        Messages in other channels must follow ChannelID-MessageID format."""
        if message.guild != ctx.guild:
            return await ctx.send("I can only edit messages in this server.")
        if message.author != ctx.guild.me:
            return await ctx.send("I cannot edit messages that are not sent by me.")
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist.")
        data = embeds_stored[name]["data"]
        embed = await self.validate_data(ctx, data=data)
        if not embed:
            return
        try:
            await message.edit(content="", embed=embed)
            await ctx.tick()
        except discord.errors.HTTPException as error:
            err = "\n".join(traceback.format_exception_only(type(error), error))
            em = discord.Embed(
                title="Parsing Error",
                description=f"The following is an extract of the error:\n```py\n{err}``` \nValidate your input by using any available embed generator online.",
                colour=discord.Color.red(),
            )
            await ctx.send(embed=em)

    @embed.command(name="editjson", aliases=["edit-json", "editraw"])
    @commands.bot_has_permissions(embed_links=True)
    async def edit_json(self, ctx, message: discord.Message, *, raw_json: str):
        """Edit a bot sent message with a new embed from JSON.

        Message format is in messageID format.
        Messages in other channels must follow ChannelID-MessageID format."""
        if message.guild != ctx.guild:
            return await ctx.send("I can only edit messages in this server.")
        if message.author != ctx.guild.me:
            return await ctx.send("I cannot edit messages that are not sent by me.")
        data = self.cleanup_code(raw_json)
        embed = await self.validate_data(ctx, data=data)
        if not embed:
            return
        try:
            await message.edit(content="", embed=embed)
            await ctx.tick()
        except discord.errors.HTTPException as error:
            err = "\n".join(traceback.format_exception_only(type(error), error))
            em = discord.Embed(
                title="Parsing Error",
                description=f"The following is an extract of the error:\n```py\n{err}``` \nValidate your input by using any available embed generator online.",
                colour=discord.Color.red(),
            )
            await ctx.send(embed=em)
