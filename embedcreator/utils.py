import json
import traceback
from typing import Optional
from io import StringIO

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .embedmixin import embed


class EmbedUtils(MixinMeta):
    @embed.command(name="menu")
    async def embed_menu(self, ctx, *, embed_names: str):
        """Send a menu of multiple embeds.
        Must be split using spaces.

        Example Usage: [p]embed menu embed1 embed2 embed3
        Note: embeds must be saved."""
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        failed = []
        embeds = []
        for embedname in embed_names.split():
            if embedname not in embeds_stored:
                failed.append(embedname)
            else:
                embeds.append(embeds_stored[embedname]["data"])
        if failed:
            return await ctx.send(
                f"The following embed{'s' if len(failed) > 1 else ''} {'does' if len(failed) == 1 else 'do'} not exist in this guild: {humanize_list(failed)}"
            )
        await self.menu_embed(ctx, embeds=embeds)

    async def menu_embed(self, ctx, embeds):
        complete_embeds = []
        for data in embeds:
            embed = await self.validate_data(ctx, data=data)
            if not embed:
                return
            try:
                embed = discord.Embed().from_dict(data)
            except Exception:
                return await ctx.send(
                    "Oops. An error occured turning the input to an embed. Please validate the file and ensure it is using the correct keys."
                )
            if not isinstance(embed, discord.Embed):
                return await ctx.send("Embed could not be built from the json provided.")
            if len(embed) < 1 or len(embed) > 6000:
                if not any([embed.thumbnail, embed.image]):
                    return await ctx.send(
                        "The returned embed does not fit within discords size limitations. The total embed length must be greater then 0 and less than 6000."
                    )
            complete_embeds.append(embed)
        try:
            await menu(
                ctx,
                complete_embeds,
                DEFAULT_CONTROLS,
            )
        except discord.errors.HTTPException as error:
            err = "\n".join(traceback.format_exception_only(type(error), error))
            em = discord.Embed(
                title="Parsing Error",
                description=f"The following is an extract of the error:\n```py\n{err}``` \nValidate your input by using any available embed generator online.",
                colour=discord.Color.red(),
            )
            await ctx.send(embed=em)

    @embed.command(name="multi")
    async def embed_multi(self, ctx, *, embed_names: str):
        """Send multiple embeds.
        Must be split using spaces.

        Example Usage: [p]embed multi embed1 embed2 embed3
        Note: embeds must be saved."""
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        failed = []
        embeds = []
        for embedname in embed_names.split():
            if embedname not in embeds_stored:
                failed.append(embedname)
            else:
                embeds.append(embeds_stored[embedname]["data"])
        if failed:
            return await ctx.send(
                f"The following embed{'s' if len(failed) > 1 else ''} {'does' if len(failed) == 1 else 'do'} not exist in this guild: {humanize_list(failed)}"
            )
        for embed in embeds:
            embed = await self.validate_data(ctx, data=embed)
            if not embed:
                return
            await ctx.send(embed=embed)

    @embed.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def delete(self, ctx, *, name: str):
        """Delete a saved embed."""
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist.")
        async with self.config.guild(ctx.guild).embeds() as embeds:
            del embeds[name]
        await ctx.tick()

    @embed.command(name="list")
    @commands.admin_or_permissions(manage_guild=True)
    async def _list(self, ctx):
        """List saved embeds."""
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if not embeds_stored:
            return await ctx.send("There are no embeds stored in this server.")
        msg = ""
        for embed in embeds_stored:
            user = ctx.guild.get_member(embeds_stored[embed]["author"])
            msg += f"{embed} - Created by: {user if user is not None else '<removed user>'}\n"
        embeds = []
        for page in pagify(msg):
            embeds.append(
                discord.Embed(
                    title=f"Embeds in {ctx.guild}",
                    description=page,
                    color=await ctx.embed_colour(),
                )
            )
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
            return
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @embed.command(name="from", aliases=["from_message", "from_msg"])
    async def from_message(
        self,
        ctx,
        message_id: int,
        channel: Optional[discord.TextChannel] = None,
        name: Optional[str] = None,
    ):
        """Return the JSON in file format from an existing message."""
        channel = channel or ctx.channel
        try:
            message = await channel.fetch_message(message_id)
        except discord.HTTPException:
            return await ctx.send("No such message can be retrieved.")

        if not message.embeds:
            return await ctx.send("This message doesn't appear to have an embed.")
        data = message.embeds[0].to_dict()
        io = StringIO(json.dumps(data, indent=4))
        io.seek(0)
        await ctx.send(
            "Here is that embed contents as a json.",
            file=discord.File(io, filename=f"{name}.json" if name else "embedcontents.json"),
        )
