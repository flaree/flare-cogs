import json
import re
from io import BytesIO, StringIO
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

START_CODE_BLOCK_RE = re.compile(r"^((```json)(?=\s)|(```))")


class EmbedCreator(commands.Cog):
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

    __version__ = "0.0.4"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 95932766180343808, force_registration=True)
        self.config.register_guild(embeds={})

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]
        return content

    @commands.admin_or_permissions(manage_channels=True)
    @commands.group()
    async def embed(self, ctx):
        """Group command for embed creator."""

    @embed.command(name="from", aliases=["from_message", "from_msg"])
    async def from_message(
        self, ctx, message_id: int, channel: Optional[discord.TextChannel] = None
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
            file=discord.File(io, filename="embedcontents.json"),
        )

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

    async def build_embed(self, ctx, *, data, channel):
        if not isinstance(data, dict):
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                return await ctx.send(
                    "Unable to read JSON, ensure it is correctly formatted and validated."
                )
        if data.get("embed"):
            data = data["embed"]
        if data.get("embeds"):
            data = data["embeds"][0]
        if data.get("timestamp"):
            data["timestamp"] = data["timestamp"].strip("Z")
        try:
            embed = discord.Embed().from_dict(data)
        except Exception:
            return await ctx.send(
                "Oops. An error occured turning the input to an embed. Please validate the file and ensure it is using the correct keys."
            )
        if not isinstance(embed, discord.Embed):
            return await ctx.send("Embed could not be built from the json provided.")
        await channel.send(embed=embed)

    async def store_embed(self, ctx, *, name, data):
        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError:
            return await ctx.send(
                "Unable to read JSON, ensure it is correctly formatted and validated."
            )
        if data.get("embed"):
            data = data["embed"]
        if data.get("embeds"):
            data = data["embeds"][0]
        if data.get("timestamp"):
            data["timestamp"] = data["timestamp"].strip("Z")
        try:
            embed = discord.Embed().from_dict(data)
        except Exception:
            return await ctx.send(
                "Oops. An error occured turning the input to an embed. Please validate the file and ensure it is using the correct keys."
            )
        if not isinstance(embed, discord.Embed):
            return await ctx.send("Embed could not be built from the json provided.")
        await ctx.send("Here's how this will look.", embed=embed)
        async with self.config.guild(ctx.guild).embeds() as embeds:
            embeds[name] = {"data": data, "author": ctx.author.id}

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
        await self.store_embed(ctx, name=name, data=data)

    @store.command(name="json")
    @commands.bot_has_permissions(embed_links=True)
    async def store_json(self, ctx, name: str, *, raw_json):
        """Store an embed from raw json."""
        raw_json = self.cleanup_code(raw_json)
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name in embeds_stored:
            return await ctx.send("This embed already exists.")
        await self.store_embed(ctx, name=name, data=raw_json)

    @embed.command()
    @commands.bot_has_permissions(embed_links=True)
    async def send(self, ctx, channel: Optional[discord.TextChannel] = None, *, name: str):
        """Send a saved embed."""
        channel = channel or ctx.channel
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist.")
        data = embeds_stored[name]["data"]
        await self.build_embed(ctx, data=data, channel=channel)

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
