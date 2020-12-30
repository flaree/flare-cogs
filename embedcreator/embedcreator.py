import json
import re
import traceback
from abc import ABC
from typing import Optional

import discord
from redbot.core import Config, commands

from .embedmixin import EmbedMixin
from .globalembeds import EmbedGlobal
from .sending import EmbedSending
from .storing import EmbedStoring
from .update import EmbedUpdate
from .utils import EmbedUtils

START_CODE_BLOCK_RE = re.compile(r"^((```json)(?=\s)|(```))")


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """This allows the metaclass used for proper type detection to coexist with discord.py's
    metaclass."""


class EmbedCreator(
    EmbedMixin,
    EmbedUtils,
    EmbedGlobal,
    EmbedSending,
    EmbedStoring,
    EmbedUpdate,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """EmbedCreator"""

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        all_guilds = await self.config.all_guilds()
        matches = []
        for guild_id, guildconf in all_guilds.items():
            for embed in guildconf["embeds"]:
                if guildconf["embeds"][embed]["author"] == user_id:
                    matches.append((guild_id, embed))
        for match in matches:
            async with self.config.guild_from_id(match[0]).embeds() as embeds:
                embeds[match[1]]["author"] = 00000000
        all_embeds = await self.config.all()
        all_matches = []
        for embed in all_embeds["embeds"]:
            if all_embeds["embeds"][embed]["author"] == user_id:
                all_matches.append(embed)

        async with self.config.embeds() as embeds:
            for match in all_matches:
                embeds[match]["author"] = 00000000

    __version__ = "0.2.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 95932766180343808, force_registration=True)
        self.config.register_guild(embeds={})
        self.config.register_global(embeds={})

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]
        return content

    async def build_embed(self, ctx, *, data, channel):
        embed = await self.validate_data(ctx, data=data)
        if not embed:
            return
        try:
            await channel.send(embed=embed)
        except discord.errors.HTTPException as error:
            err = "\n".join(traceback.format_exception_only(type(error), error))
            em = discord.Embed(
                title="Parsing Error",
                description=f"The following is an extract of the error:\n```py\n{err}``` \nValidate your input by using any available embed generator online.",
                colour=discord.Color.red(),
            )
            await ctx.send(embed=em)

    async def store_embed(self, ctx, is_global, *, name, data):
        embed = await self.validate_data(ctx, data=data)
        if not embed:
            return
        try:
            await ctx.send("Here's how this will look.", embed=embed)
        except discord.errors.HTTPException as error:
            err = "\n".join(traceback.format_exception_only(type(error), error))
            em = discord.Embed(
                title="Parsing Error",
                description=f"The following is an extract of the error:\n```py\n{err}``` \nValidate your input by using any available embed generator online.",
                colour=discord.Color.red(),
            )
            await ctx.send(embed=em)
            return
        if not is_global:
            async with self.config.guild(ctx.guild).embeds() as embeds:
                embeds[name] = {"data": data, "author": ctx.author.id}
        else:
            async with self.config.embeds() as embeds:
                embeds[name] = {"data": data, "author": ctx.author.id}

    async def validate_data(self, ctx, *, data) -> Optional[discord.Embed]:
        if not isinstance(data, dict):
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                return await ctx.send(
                    "Unable to read JSON, ensure it is correctly formatted and validated."
                )
        if not isinstance(data, dict):
            await ctx.send("The JSON provided is not in a dictionary format.")
            return False
        if data.get("embed"):
            data = data["embed"]
        if data.get("embeds"):
            data = data["embeds"][0]
        if data.get("timestamp"):
            data["timestamp"] = data["timestamp"].strip("Z")
        try:
            embed = discord.Embed().from_dict(data)
        except Exception:
            await ctx.send(
                "Oops. An error occured turning the input to an embed. Please validate the file and ensure it is using the correct keys."
            )
            return False
        else:
            if not isinstance(embed, discord.Embed):
                await ctx.send("Embed could not be built from the json provided.")
                return False
            if len(embed) < 1 or len(embed) > 6000:
                if not any([embed.thumbnail, embed.image]):
                    await ctx.send(
                        "The returned embed does not fit within discords size limitations. The total embed length must be greater then 0 and less than 6000."
                    )
                    return False
            return embed
