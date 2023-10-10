import asyncio
import contextlib
from copy import deepcopy

import discord
from redbot.core import Config, commands
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu
from redbot.core.utils.predicates import MessagePredicate

from .objects import TriggerObject


class Trigger(commands.Cog):
    __version__ = "0.2.0"
    __author__ = "flare(flare#0001)"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808)
        self.config.register_guild(triggers={})

        self.triggers = {}
        self.bg_config_loop = asyncio.create_task(self.init_loop())
        with contextlib.suppress(Exception):
            self.bot.add_dev_env_value("trigger", lambda x: self)

    async def init_loop(self):
        await self.bot.wait_until_ready()
        while True:
            await asyncio.sleep(60)
            await self.save_triggers()

    def cog_unload(self):
        self.bg_config_loop.cancel()
        asyncio.create_task(self.save_triggers())
        with contextlib.suppress(Exception):
            self.bot.remove_dev_env_value("trigger")

    async def save_triggers(self):
        for guild_id, triggers in self.triggers.items():
            guild_triggers = {}
            for trigger in triggers:
                guild_triggers[trigger] = deepcopy(triggers[trigger].__dict__)
                del guild_triggers[trigger]["timestamp"]
                del guild_triggers[trigger]["pattern"]
            await self.config.guild_from_id(guild_id).triggers.set(guild_triggers)

    async def init_loop(self):
        await self.bot.wait_until_ready()
        triggers = await self.config.all_guilds()
        for guild_id, guild_triggers in triggers.items():
            for trigger in guild_triggers["triggers"]:
                if guild_id not in self.triggers:
                    self.triggers[guild_id] = {}
                self.triggers[guild_id][trigger] = TriggerObject(
                    **guild_triggers["triggers"][trigger]
                )
        while True:
            await asyncio.sleep(60)
            await self.save_triggers()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        guild = message.guild
        for trigger in self.triggers.get(guild.id, {}):
            obj = self.triggers[guild.id][trigger]
            if obj.check(message):
                await obj.respond(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        if any(item in payload.data for item in ["content", "guild_id"]):
            return
        guild = self.bot.get_guild(int(payload.data["guild_id"]))
        if not guild:
            return
        channel = guild.get_channel(int(payload.data["channel_id"]))
        try:
            message = await channel.fetch_message(int(payload.data["id"]))
        except Exception:
            return
        if message.author.bot:
            return
        for trigger in self.triggers.get(guild.id, {}):
            obj = self.triggers[guild.id][trigger]
            if obj.embed_search and obj.check(message):
                await obj.respond(message)

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def trigger(self, ctx):
        """
        Group command for triggers.
        """

    @trigger.command()
    async def create(self, ctx, trigger_name: str, *, triggered_by: str):
        """
        Create a trigger.

        Variables can be used within the responses.
        user: The user that triggered the trigger.
        channel: The channel the trigger was triggered in.
        message: The message that triggered the trigger.
        guild: The guild the trigger was triggered in.
        uses: The number of times the trigger has been used.
        trigger: The name of the trigger that was triggered.

        Example: `{user} has triggered the trigger {trigger} in {channel} {uses} times.`
        """
        trigger_name = trigger_name.lower()
        triggers = await self.config.guild(ctx.guild).triggers()
        if trigger_name in triggers:
            await ctx.send("Trigger already exists.")
            return
        responses = []
        await ctx.send(
            "Every message you send will be counted as a response. To exit or finish adding responses, type `exit`."
        )
        while True:
            msg = await self.bot.wait_for("message", check=MessagePredicate.same_context(ctx))

            if msg.content.lower() == "exit":
                break
            elif len(msg.content) > 2000:
                await ctx.send(
                    "The text response you're trying to create has more than 2000 characters.\nI cannot send messages that are longer than 2000 characters, please try again."
                )
                continue
            await msg.add_reaction("✅")
            responses.append(msg.content)
        async with self.config.guild(ctx.guild).triggers() as triggers:
            triggers[trigger_name] = {
                "trigger": triggered_by,
                "responses": responses,
                "owner": ctx.author.id,
                "guild": ctx.guild.id,
                "cooldown": 0,
                "timestamp": None,
                "uses": 0,
                "toggle": True,
                "case_sensitive": False,
                "word_boundary": False,
                "embed_search": False,
            }
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])

        await ctx.send("Trigger created.")

    @trigger.command()
    async def delete(self, ctx, trigger_name: str):
        """
        Delete a trigger.
        """
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            del triggers[trigger_name]
        if trigger_name in self.triggers.get(ctx.guild.id, {}):
            del self.triggers[ctx.guild.id][trigger_name]
        await ctx.send("Trigger deleted.")

    @trigger.command(name="list")
    async def _list(self, ctx):
        """
        List all triggers.
        """
        await self.save_triggers()
        triggers = await self.config.guild(ctx.guild).triggers()
        if not triggers:
            await ctx.send("No triggers found.")
            return
        pages = []
        for trigger in triggers:
            responses = "\n".join(triggers[trigger]["responses"])
            msg = f"**Triggered By:** {triggers[trigger]['trigger']}\n**Uses:** {triggers[trigger]['uses']}\n**Cooldown:** {triggers[trigger]['cooldown']} seconds\n**Responses:**\n {responses}"
            if len(msg) > 2000:
                msg = f"**Triggered By:** {triggers[trigger]['trigger']}\n**Uses:** {triggers[trigger]['uses']}\n**Cooldown:** {triggers[trigger]['cooldown']} seconds\n**Responses:**\n *Responses Truncated*"
            embed = discord.Embed(title=trigger, description=msg, color=await ctx.embed_color())
            if user := ctx.guild.get_member(triggers[trigger]["owner"]):
                footer = f"Created by {user}"
            else:
                footer = f"Created by <Unknown User {triggers[trigger]['owner']}>"
            embed.set_footer(text=footer)
            pages.append(embed)
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @trigger.command()
    async def toggle(self, ctx, trigger_name):
        """
        Toggle a trigger.
        """
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            value = not triggers[trigger_name]["toggle"]
            triggers[trigger_name]["toggle"] = value
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])
        if value:
            await ctx.send("Trigger enabled.")
        else:
            await ctx.send("Trigger disabled.")

    @trigger.group()
    async def edit(self, ctx):
        """
        Edit a trigger.
        """

    @edit.command(name="trigger")
    async def _trigger(self, ctx, trigger_name: str, *, triggered_by: str):
        """
        Edit the trigger.
        """
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            triggers[trigger_name]["trigger"] = triggered_by
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])
        await ctx.tick()

    @edit.command()
    async def cooldown(self, ctx, trigger_name: str, seconds: int):
        """
        Set the cooldown for a trigger.
        """
        if seconds < 0:
            await ctx.send("Cooldown cannot be negative.")
            return
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            triggers[trigger_name]["cooldown"] = seconds
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])
        await ctx.tick()

    @edit.command(name="case", aliases=["casesensitive"])
    async def case_sensitive(self, ctx, trigger_name: str, case_sensitive: bool):
        """
        Toggle case sensitivity for a trigger.
        """
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            triggers[trigger_name]["case_sensitive"] = case_sensitive
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])
        await ctx.tick()

    @edit.command(name="boundary", aliases=["wordboundary"])
    async def word_boundary(self, ctx, trigger_name: str, toggle: bool):
        """
        Toggle word boundaries for a trigger.
        """
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            triggers[trigger_name]["word_boundary"] = toggle
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])
        await ctx.tick()

    @edit.command(name="embeds", aliases=["embedsearch"])
    async def embed_search(self, ctx, trigger_name: str, toggle: bool):
        """
        Toggle searching within embeds for the trigger.
        """
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            triggers[trigger_name]["embed_search"] = toggle
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])
        await ctx.tick()

    @edit.command()
    async def responses(self, ctx, trigger_name: str):
        """
        Edit the responses for a trigger.
        """
        trigger_name = trigger_name.lower()
        async with self.config.guild(ctx.guild).triggers() as triggers:
            if trigger_name not in triggers:
                await ctx.send("Trigger does not exist.")
                return
            responses = []
            await ctx.send(
                "Every message you send will be counted as a response. To exit or finish adding responses, type `exit`."
            )
            while True:
                msg = await self.bot.wait_for("message", check=MessagePredicate.same_context(ctx))

                if msg.content.lower() == "exit":
                    break
                elif len(msg.content) > 2000:
                    await ctx.send(
                        "The text response you're trying to create has more than 2000 characters.\nI cannot send messages that are longer than 2000 characters, please try again."
                    )
                    continue
                await msg.add_reaction("✅")
                responses.append(msg.content)
            triggers[trigger_name]["responses"] = responses
            await self.update_trigger(ctx.guild, trigger_name, triggers[trigger_name])
        await ctx.tick()

    async def update_trigger(self, guild, trigger_name, trigger_data):
        if guild.id not in self.triggers:
            self.triggers[guild.id] = {}
        self.triggers[guild.id][trigger_name] = TriggerObject(**trigger_data)
