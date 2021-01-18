from io import BytesIO
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .embedmixin import embed


class EmbedGlobal(MixinMeta):
    @commands.is_owner()
    @embed.command(name="convert")
    async def global_convert(self, ctx, *, name: str):
        """Convert a guild embed to global."""
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist.")
        data = embeds_stored[name]
        global_embeds = await self.config.embeds()
        if name in global_embeds:
            return await ctx.send("An embed with this name already exists globally.")
        async with self.config.embeds() as embeds:
            embeds[name] = data
        await ctx.tick()

    @commands.is_owner()
    @embed.group(name="global")
    async def global_embeds(self, ctx):
        """Global embed settings."""

    @global_embeds.command(name="list")
    async def global_list(self, ctx):
        """List global embeds."""
        embeds_stored = await self.config.embeds()
        if not embeds_stored:
            return await ctx.send("There are no embeds stored globally.")
        msg = ""
        for embed in embeds_stored:
            user = ctx.guild.get_member(embeds_stored[embed]["author"])
            msg += f"{embed} - Created by: {user if user is not None else '<unknown user>'}\n"
        embeds = []
        for page in pagify(msg):
            embeds.append(
                discord.Embed(
                    title=f"Global Embeds",
                    description=page,
                    color=await ctx.embed_colour(),
                )
            )
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
            return
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @global_embeds.command(name="file")
    @commands.bot_has_permissions(embed_links=True)
    async def store_file_global(self, ctx, *, name: str):
        """Store an embed globally from a json file."""
        embeds_stored = await self.config.embeds()
        if name in embeds_stored:
            return await ctx.send("This embed already exists.")

        if not ctx.message.attachments:
            return await ctx.send("You need to upload a file for this command to work")
        with BytesIO() as fp:
            await ctx.message.attachments[0].save(fp)
            data = fp.read().decode("utf-8")
        await self.store_embed(ctx, True, name=name, data=data)

    @global_embeds.command(name="json")
    @commands.bot_has_permissions(embed_links=True)
    async def store_json_global(self, ctx, name: str, *, raw_json):
        """Store an embed globally from raw json."""
        raw_json = self.cleanup_code(raw_json)
        embeds_stored = await self.config.embeds()
        if name in embeds_stored:
            return await ctx.send("This embed already exists.")
        await self.store_embed(ctx, True, name=name, data=raw_json)

    @global_embeds.command(name="from", aliases=["from_message", "from_msg"])
    async def from_message_store_global(
        self,
        ctx,
        name: str,
        message_id: int,
        channel: Optional[discord.TextChannel] = None,
    ):
        """Save an embed globally from an existing message."""
        embeds_stored = await self.config.embeds()
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
        await self.store_embed(ctx, True, name=name, data=data)

    @global_embeds.command(name="send")
    @commands.bot_has_permissions(embed_links=True)
    async def send_global(self, ctx, channel: Optional[discord.TextChannel] = None, *, name: str):
        """Send a globally saved embed."""
        channel = channel or ctx.channel
        embeds_stored = await self.config.embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist globally.")
        data = embeds_stored[name]["data"]
        await self.build_embed(ctx, data=data, channel=channel)

    @global_embeds.command(name="menu")
    async def embed_menu_global(self, ctx, *, embed_names: str):
        """Send a menu of multiple embeds.
        Must be split using spaces.

        Example Usage: [p]embed menu embed1 embed2 embed3
        Note: embeds must be saved."""
        embeds_stored = await self.config.embeds()
        failed = []
        embeds = []
        for embedname in embed_names.split():
            if embedname not in embeds_stored:
                failed.append(embedname)
            else:
                embeds.append(embeds_stored[embedname]["data"])
        if failed:
            return await ctx.send(
                f"The following embed{'s' if len(failed) > 1 else ''} {'does' if len(failed) == 1 else 'do'} not exist globally: {humanize_list(failed)}"
            )
        await self.menu_embed(ctx, embeds=embeds)

    @global_embeds.command(name="delete")
    @commands.admin_or_permissions(manage_guild=True)
    async def delete_global(self, ctx, *, name: str):
        """Delete a globally saved embed."""
        embeds_stored = await self.config.embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist globally.")
        async with self.config.embeds() as embeds:
            del embeds[name]
        await ctx.tick()
