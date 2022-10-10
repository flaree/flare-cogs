import asyncio
import functools
import logging
import random

import discord
from redbot.core import commands
from redbot.core.config import Config
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

log = logging.getLogger("red.flare.tips")

real_send = commands.Context.send


def task_done_callback(task: asyncio.Task):
    """Properly handle and log errors in the startup task."""
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as error:
        log.exception("Failed to initialize the cog.", exc_info=error)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


# from: https://docs.python.org/3/library/stdtypes.html#str.format_map
class Default(dict):
    """Used with str.format_map to avoid KeyErrors on bad tips."""

    def __missing__(self, key):
        # returns missing keys as '{key}'
        return f"{{{key}}}"


# Thanks Jack for smileysend
@functools.wraps(real_send)
async def send(self, content=None, **kwargs):
    content = str(content) if content is not None else None
    cog = self.bot.get_cog("Tips")
    if (cog).usercache.get(self.author.id, {}).get("toggle", True) and random.randint(
        1, cog.chance
    ) == 1:
        tips = cog.message_cache or ["No tips configured."]
        tip_msg = random.choice(tips).replace("{prefix}", self.clean_prefix)
        new_content = cog.tip_format.format_map(
            Default(
                content=content or "",
                tip_msg=tip_msg,
                prefix=self.clean_prefix,
            )
        )

        if len(new_content) <= 2000:
            content = new_content
    return await real_send(self, content, **kwargs)


class Tips(commands.Cog):
    """Tips - Credit to Jackenmen"""

    __version__ = "0.0.3"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 176070082584248320, force_registration=True)
        self.config.register_global(
            tips=["Add tips by using `{prefix}tips add-tip`."],
            chance=50,
            tip_format="{tip_msg}\nYou can turn these tips off by typing `{prefix}tips off`\n\n{content}",
        )
        self.config.register_user(toggle=True)

        setattr(commands.Context, "send", send)
        self.message_cache = []
        self.chance = 50
        self.tip_format = ""
        self.usercache = {}

        self.initialize_task = asyncio.create_task(self.initialize())
        self.initialize_task.add_done_callback(task_done_callback)

    async def initialize(self) -> None:
        await self.generate_cache()

    async def generate_cache(self):
        data = await self.config.all()
        self.message_cache = data["tips"]
        self.chance = data["chance"]
        self.tip_format = data["tip_format"]
        self.usercache = await self.config.all_users()

    def cog_unload(self) -> None:
        setattr(commands.Context, "send", real_send)

    @commands.group(invoke_without_command=True)
    async def tips(self, ctx: commands.Context, toggle: bool) -> None:
        """
        Toggle and setup tips.

        Run `[p]tips off` to disable tips.
        """
        await self.config.user(ctx.author).toggle.set(toggle)
        await ctx.tick()
        await self.generate_cache()

    @commands.is_owner()
    @tips.command()
    async def chance(self, ctx, chance: int):
        """
        Chance for a tip to show.

        Default is 50
        """
        if chance <= 1:
            return await ctx.send("Chance must be greater than 1")
        await self.config.chance.set(chance)
        await self.generate_cache()
        await ctx.tick()

    @commands.is_owner()
    @tips.command(name="add-tip", aliases=["add", "addtip", "create"])
    async def add_tip(self, ctx, *, tip: str):
        """
        Add a tip message.

        Append `{prefix}` to have it formatted with prefix on send.
        """
        async with self.config.tips() as replies:
            if tip in replies:
                return await ctx.send("That is already a response.")
            replies.append(tip)
            ind = replies.index(tip)
        await ctx.send(f"Your tip has been added and is tip ID #{ind}")
        await self.generate_cache()

    @commands.is_owner()
    @tips.command(name="del-tip", aliases=["del", "deltip", "delete"])
    async def del_tips(self, ctx, *, id: int):
        """Delete a custom tip."""
        async with self.config.tips() as replies:
            if not replies:
                return await ctx.send("No custom tips are configured.")
            if id > len(replies):
                return await ctx.send("Invalid ID.")
            replies.pop(id)
        await ctx.send("Your tip has been removed")
        await self.generate_cache()

    @commands.is_owner()
    @tips.command(name="list-tips", aliases=["list", "listtips"])
    async def list_tips(
        self,
        ctx,
    ):
        """List custom tips."""
        async with self.config.tips() as replies:
            if not replies:
                return await ctx.send("No tips have been configured.")
            a = chunks(replies, 10)
            embeds = []
            i = 0
            for item in a:
                items = []
                for strings in item:
                    items.append(f"**Reply {i}**: {strings}")
                    i += 1
                embed = discord.Embed(
                    colour=await self.bot.get_embed_colour(ctx.channel),
                    description="\n".join(items),
                )
                embeds.append(embed)
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.is_owner()
    @tips.command(name="format")
    async def format(
        self,
        ctx: commands.Context,
        *,
        formatting=None,
    ):
        """
        Set the format for tip messages.

        Variables:
        `tip_msg` - the tip
        `content` - the original message content
        `prefix` - the invocation prefix

        Default value:
        `{tip_msg}\\nYou can turn these tips off by typing `{prefix}tips off`\\n\\n{content}`
        """
        if formatting:
            await self.config.tip_format.set(formatting)
            await ctx.channel.send(
                f"The tip format has been set to:\n{formatting}"
            )  # intentionally uses ctx.channel to avoid tips being triggered
        else:
            await self.config.tip_format.clear()
            await ctx.channel.send("The tip format has been reset to the default.")
        await self.generate_cache()
        content = "This is example content of a message with a tip."
        tips = self.message_cache or ["No tips configured."]
        tip_msg = random.choice(tips).format(prefix=ctx.clean_prefix)
        await ctx.channel.send(
            self.tip_format.format(content=content, tip_msg=tip_msg, prefix=ctx.clean_prefix)
        )
