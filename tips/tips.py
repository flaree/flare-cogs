import functools
import random

import discord
from discord.abc import Messageable
from redbot.core import commands
from redbot.core.commands import Context
from redbot.core.config import Config
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

real_send = Messageable.send


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


# Thanks Jack for smileysend
@functools.wraps(real_send)
async def send(
    self,
    content=None,
    *,
    tts=False,
    embed=None,
    file=None,
    files=None,
    delete_after=None,
    nonce=None,
    allowed_mentions=None,
    reference=None,
    mention_author=None,
):
    if isinstance(self, Context):
        content = str(content) if content is not None else None
        cog = self.bot.get_cog("Tips")
        if (cog).usercache.get(self.author.id, {}).get("toggle", "False"):
            tips = cog.message_cache if cog.message_cache else ["No tips configured."]
            tip_msg = random.choice(tips).format(
                prefix=self.clean_prefix
            ) + "\nYou can turn these tips off by typing `{}tips off`\n".format(self.clean_prefix)
            if random.randint(1, cog.chance) == 1:
                if content:
                    if len(content) > 1995 - len(tip_msg):
                        await real_send(self, tip_msg)
                    else:
                        content = f"{tip_msg}\n{content}"
                else:
                    content = tip_msg
    return await send_with_msg_ref(
        self,
        content,
        tts=tts,
        embed=embed,
        file=file,
        files=files,
        delete_after=delete_after,
        nonce=nonce,
        allowed_mentions=allowed_mentions,
        reference=reference,
        mention_author=mention_author,
    )


async def send_with_msg_ref(
    messageable: Messageable,
    content=None,
    *,
    reference=None,
    **kwargs,
) -> discord.Message:
    try:
        return await real_send(messageable, content, reference=reference, **kwargs)
    except discord.HTTPException as e:
        if e.code == 50035 and "In message_reference: Unknown message" in str(e):
            return await send_with_msg_ref(
                messageable,
                content,
                **kwargs,
            )
        raise


class Tips(commands.Cog):
    """Tips - Credit to Jackenmen"""

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, 176070082584248320, force_registration=True)
        self.config.register_global(tips=["Add tips by using `{prefix}tips add-tip`"], chance=50)
        self.config.register_user(toggle=True)

    async def initialize(self) -> None:
        setattr(Messageable, "send", send)
        await self.generate_cache()

    async def generate_cache(self):
        self.usercache = await self.config.all_users()
        self.message_cache = await self.config.tips()
        self.chance = await self.config.chance()

    def cog_unload(self) -> None:
        setattr(Messageable, "send", real_send)

    @commands.group(invoke_without_command=True)
    async def tips(self, ctx: commands.Context, toggle: bool) -> None:
        await self.config.user(ctx.author).toggle.set(toggle)
        await ctx.tick()
        await self.generate_cache()

    @commands.is_owner()
    @tips.command()
    async def chance(self, ctx, chance: int):
        """Chance for a tip to show.
        Default is 50"""
        if chance <= 1:
            return await ctx.send("Chance must be greater than 1")
        await self.config.chance.set(chance)
        await self.generate_cache()

    @commands.is_owner()
    @tips.command(name="add-tip", aliases=["add", "addtip"])
    async def add_tip(self, ctx, *, tip: str):
        """Add a tip message.
        Append {prefix} to have it formatted with prefix on send.
        """
        async with self.config.tips() as replies:
            if tip in replies:
                return await ctx.send("That is already a response.")
            replies.append(tip)
            ind = replies.index(tip)
        await ctx.send("Your tip has been added and is tip ID #{}".format(ind))
        await self.generate_cache()

    @commands.is_owner()
    @tips.command(name="del-tip", aliases=["del", "deltip"])
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
            for item in a:
                items = []
                for i, strings in enumerate(item):
                    items.append(f"**Reply {i}**: {strings}")
                embed = discord.Embed(colour=discord.Color.red(), description="\n".join(items))
                embeds.append(embed)
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS)
