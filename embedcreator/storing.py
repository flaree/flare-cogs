from io import BytesIO
from typing import Optional

import discord
from redbot.core import commands

from .abc import MixinMeta
from .embedmixin import embed


class EmbedStoring(MixinMeta):
    @embed.group()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True)
    async def store(self, ctx):
        """Embed storing commands"""

    @store.command(name="file")
    @commands.bot_has_permissions(embed_links=True)
    async def store_file(self, ctx, *, name: str):
        """Store an embed from a json file."""
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name in embeds_stored:
            return await ctx.send("This embed already exists.")

        if not ctx.message.attachments:
            return await ctx.send("You need to upload a file for this command to work")
        with BytesIO() as fp:
            await ctx.message.attachments[0].save(fp)
            data = fp.read().decode("utf-8")
        await self.store_embed(ctx, False, name=name, data=data)

    @store.command(name="json")
    @commands.bot_has_permissions(embed_links=True)
    async def store_json(self, ctx, name: str, *, raw_json):
        """Store an embed from raw json."""
        raw_json = self.cleanup_code(raw_json)
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name in embeds_stored:
            return await ctx.send("This embed already exists.")
        await self.store_embed(ctx, False, name=name, data=raw_json)

    @store.command(name="from", aliases=["from_message", "from_msg"])
    async def from_message_store(
        self,
        ctx,
        name: str,
        message_id: int,
        channel: Optional[discord.TextChannel] = None,
    ):
        """Save an embed from an existing message."""
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name in embeds_stored:
            return await ctx.send("This embed already exists.")
        channel = channel or ctx.channel
        try:
            message = await channel.fetch_message(message_id)
        except discord.HTTPException:
            return await ctx.send("No such message can be retrieved.")

        if not message.embeds:
            return await ctx.send("This message doesn't appear to have an embed.")
        data = message.embeds[0].to_dict()
        await self.store_embed(ctx, False, name=name, data=data)
