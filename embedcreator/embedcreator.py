import json
import re
import traceback
from io import BytesIO, StringIO
from typing import Optional

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import humanize_list, pagify
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
        all_embeds = await self.config.all()
        all_matches = []
        for embed in all_embeds["embeds"]:
            if all_embeds["embeds"][embed]["author"] == user_id:
                all_matches.append(embed)

        async with self.config.embeds() as embeds:
            for match in all_matches:
                embeds[match]["author"] = 00000000

    __version__ = "0.1.0"

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

    @commands.admin_or_permissions(manage_channels=True)
    @commands.group()
    async def embed(self, ctx):
        """Group command for embed creator."""

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
            if not isinstance(data, dict):
                return await ctx.send("The JSON provided is not in a dictionary format.")
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
        if len(embed) < 1 or len(embed) > 6000:
            return await ctx.send(
                "The returned embed does not fit within discords size limitations. The total embed length must be greater then 0 and less than 6000."
            )
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
        if not isinstance(data, dict):
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                return await ctx.send(
                    "Unable to read JSON, ensure it is correctly formatted and validated."
                )
        if not isinstance(data, dict):
            return await ctx.send("The JSON provided is not in a dictionary format.")
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
        if len(embed) < 1 or len(embed) > 6000:
            return await ctx.send(
                "The returned embed does not fit within discords size limitations. The total embed length must be greater then 0 and less than 6000."
            )
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
        if not is_global:
            async with self.config.guild(ctx.guild).embeds() as embeds:
                embeds[name] = {"data": data, "author": ctx.author.id}
        else:
            async with self.config.embeds() as embeds:
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
        """Edit a bot sent message with a new embed. Message format is in messageID format."""
        if message.guild != ctx.guild:
            return await ctx.send("I can only edit messages in this server.")
        if message.author != ctx.guild.me:
            return await ctx.send("I cannot edit messages that are not sent by me.")
        embeds_stored = await self.config.guild(ctx.guild).embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist.")
        data = embeds_stored[name]["data"]
        if not isinstance(data, dict):
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                return await ctx.send(
                    "Unable to read JSON, ensure it is correctly formatted and validated."
                )
            if not isinstance(data, dict):
                return await ctx.send("The JSON provided is not in a dictionary format.")
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
        if len(embed) < 1 or len(embed) > 6000:
            return await ctx.send(
                "The returned embed does not fit within discords size limitations. The total embed length must be greater then 0 and less than 6000."
            )
        try:
            await message.edit(embed=embed)
        except discord.errors.HTTPException as error:
            err = "\n".join(traceback.format_exception_only(type(error), error))
            em = discord.Embed(
                title="Parsing Error",
                description=f"The following is an extract of the error:\n```py\n{err}``` \nValidate your input by using any available embed generator online.",
                colour=discord.Color.red(),
            )
            await ctx.send(embed=em)

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
            if not isinstance(data, dict):
                try:
                    data = json.loads(data)
                except json.decoder.JSONDecodeError:
                    return await ctx.send(
                        "Unable to read JSON, ensure it is correctly formatted and validated."
                    )
                if not isinstance(data, dict):
                    return await ctx.send("The JSON provided is not in a dictionary format.")
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
            if len(embed) < 1 or len(embed) > 6000:
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
    async def embed_menu(self, ctx, *, embed_names: str):
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

    @global_embeds.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def delete(self, ctx, *, name: str):
        """Delete a globally saved embed."""
        embeds_stored = await self.config.embeds()
        if name not in embeds_stored:
            return await ctx.send("This embed doesn't exist globally.")
        async with self.config.embeds() as embeds:
            del embeds[name]
        await ctx.tick()
